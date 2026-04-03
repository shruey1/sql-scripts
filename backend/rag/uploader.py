import os
import re
import logging
import argparse
from azure.search.documents import SearchClient
from config import (
    AZURE_SEARCH_ENDPOINT,
    SQL_INDEX,
    BP_INDEX,
    credential,
)
from chunker import chunk_text_section_aware
from embedder import generate_embeddings_batch

logger = logging.getLogger(__name__)


# ————————
# HELPERS
# ————————
def to_pascal_case_from_filename(filename: str) -> str:
    """
    Convert a filename like 'datatype_rules.txt' -> 'DatatypeRules'
    """
    name, _ = os.path.splitext(filename)
    name = name.replace("_", " ").replace("-", " ").strip()
    return "".join(part for part in name.title().split())


def parent_folder_name(file_path: str) -> str:
    """
    Returns the immediate parent folder’s name in PascalCase.
    Example: '/…/bigquery/datatype_rules.txt' -> 'Bigquery'
    """
    parent = os.path.basename(os.path.dirname(file_path))
    parent = parent.replace("_", " ").replace("-", " ").strip()
    return "".join(part for part in parent.title().split())


def make_doc_id(folder: str, filename: str, chunk_index: int) -> str:
    """
    Collision-safe document ID using folder + filename + chunk index.
    Sanitizes special characters for Azure Search compatibility.
    """
    raw = f"{folder}__{filename}__{chunk_index}"
    return re.sub(r"[^a-zA-Z0-9_-]", "_", raw)


# ————————
# FILE DISCOVERY
# ————————
def discover_txt_files(root_path: str) -> list[str]:
    """
    Recursively discovers all .txt files under root_path.
    Logs a notice when subdirectories are found and processed.
    """
    txt_files: list[str] = []

    for dirpath, dirnames, filenames in os.walk(root_path):
        if dirnames and dirpath == root_path:
            logger.info(
                f"Found subdirectories in '{root_path}': "
                f"{dirnames} — processing recursively."
            )
        for filename in filenames:
            if filename.lower().endswith(".txt"):
                txt_files.append(os.path.join(dirpath, filename))

    return txt_files


# ————————
# UPLOAD
# ————————
def upload_directory(
    directory_path: str,
    index_name: str,
    metadata_value: str | None = None,
    chunk_size: int = 500,
    overlap: int = 50,
    dry_run: bool = False,
) -> None:
    """
    Uploads all .txt files (recursively) in directory_path to index_name.
    Uses section-aware chunking and batched embedding generation.
    """

    if not os.path.isdir(directory_path):
        logger.error(f"Directory not found: '{directory_path}'")
        return

    search_client = (
        SearchClient(
            endpoint=AZURE_SEARCH_ENDPOINT,
            index_name=index_name,
            credential=credential,
        )
        if not dry_run
        else None
    )

    txt_files = discover_txt_files(directory_path)
    if not txt_files:
        logger.warning(f"No .txt files found under: '{directory_path}'")
        return

    logger.info(
        f"Found {len(txt_files)} .txt file(s) under '{directory_path}' → index '{index_name}'"
    )

    for file_path in txt_files:
        filename = os.path.basename(file_path)
        folder_name = parent_folder_name(file_path)
        section_name = to_pascal_case_from_filename(filename)

        logger.info(f"Processing: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except OSError as e:
            logger.error(f"Could not read '{file_path}': {e}")
            continue

        chunks = chunk_text_section_aware(content, chunk_size=chunk_size, overlap=overlap)
        logger.info(f"  → {len(chunks)} chunk(s) after section-aware split.")

        if dry_run:
            logger.info(f"[DRY RUN] Would upload {len(chunks)} chunks for '{filename}'.")
            for i, chunk in enumerate(chunks[:3]):
                logger.info(f"  Chunk {i}: {chunk[:120]}...")
            continue

        # Batch-embed all chunks
        try:
            embeddings = generate_embeddings_batch(chunks)
        except Exception as e:
            logger.error(f"Embedding failed for '{filename}': {e}. Skipping file.")
            continue

        documents = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            doc_id = make_doc_id(folder_name, filename, i)

            doc = {
                "id": doc_id,
                "content": chunk,
                "contentvector": embedding,
            }

            if index_name == SQL_INDEX:
                doc["database_type"] = folder_name
                doc["doc_section"] = section_name
            else:
                doc["category"] = metadata_value if metadata_value else folder_name

            documents.append(doc)

        try:
            results = search_client.upload_documents(documents)
            failed = [
                r for r in results
                if not (
                    getattr(r, "succeeded", False)
                    or getattr(r, "status_code", 200) in (200, 201)
                )
            ]

            if failed:
                logger.warning(
                    f"⚠️  {len(failed)} chunk(s) failed to upload for '{filename}': {failed}"
                )
            else:
                logger.info(
                    f"✅ Uploaded {len(documents)} chunk(s) from '{filename}' to '{index_name}'."
                )

        except Exception as e:
            logger.error(f"Upload failed for '{filename}': {e}")


# ————————
# MAIN
# ————————
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload documents to Azure AI Search.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview chunks without uploading to Azure Search.",
    )
    args = parser.parse_args()

    sql_docs_path = "backend/rag/documents/bigquery"
    best_practices_path = "backend/rag/documents/best_practices"

    logger.info("=== Starting document upload pipeline ===")

    upload_directory(
        directory_path=sql_docs_path,
        index_name=SQL_INDEX,
        dry_run=args.dry_run,
    )

    upload_directory(
        directory_path=best_practices_path,
        index_name=BP_INDEX,
        metadata_value="BestPractice",
        dry_run=args.dry_run,
    )

    logger.info("=== Upload pipeline completed. ===")