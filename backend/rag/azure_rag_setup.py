import os
import json
import time
import uuid
import logging
from pathlib import Path
from typing import Optional, List
from dotenv import load_dotenv
from tqdm import tqdm
 
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import ResourceExistsError, HttpResponseError
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    SemanticConfiguration,
    SemanticPrioritizedFields,
    SemanticField,
    SemanticSearch,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
)
from azure.search.documents.models import QueryType
 
# Optional: Azure OpenAI for embeddings
try:
    from openai import AzureOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
 
# ───────── Logging ─────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)
 
load_dotenv()
 
# ───────── Configuration ─────────
AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_ADMIN_KEY = os.getenv("AZURE_SEARCH_ADMIN_KEY")
INDEX_NAME = os.getenv("INDEX_NAME", "commerce-schema-index")
 
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_API_VER = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
EMBEDDING_DEPLOYMENT = os.getenv("EMBEDDING_DEPLOYMENT", "text-embedding-ada-002")
EMBEDDING_DIMENSIONS = 1536
 
USE_VECTOR_SEARCH = bool(AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_KEY and OPENAI_AVAILABLE)
 
KNOWLEDGE_BASE_FILE = Path("commerce_knowledge_base.json")
KNOWLEDGE_BASE_DIR = Path("knowledge_base")
 
 
# ════════════════════════════════════════════════════════════════
# LOAD KNOWLEDGE BASE
# ════════════════════════════════════════════════════════════════
 
def load_knowledge_base() -> List[dict]:
    if not KNOWLEDGE_BASE_FILE.exists():
        raise FileNotFoundError(
            f"✗ Knowledge base file not found: {KNOWLEDGE_BASE_FILE}\n"
            "Make sure commerce_knowledge_base.json is in the same folder."
        )
 
    with open(KNOWLEDGE_BASE_FILE, encoding="utf-8") as f:
        data = json.load(f)
 
    entries = data.get("entries", [])
    meta = data.get("metadata", {})
 
    log.info("Loaded %d entries from %s  [version: %s]",
             len(entries), KNOWLEDGE_BASE_FILE.name, meta.get("version", "unknown"))
 
    return entries
 
 
def load_extra_documents(directory: Path) -> List[dict]:
    docs = []
    if not directory.exists():
        return docs
 
    for file in directory.iterdir():
        if file.suffix == ".json":
            try:
                with open(file, encoding="utf-8") as f:
                    raw = json.load(f)
                items = raw if isinstance(raw, list) else raw.get("entries", [])
                docs.extend(items)
                log.info("Extra: loaded %d entries from %s", len(items), file.name)
            except Exception as exc:
                log.warning("Skipping %s: %s", file.name, exc)
 
        elif file.suffix == ".txt":
            with open(file, encoding="utf-8") as f:
                paragraphs = [p.strip() for p in f.read().split("\n\n") if p.strip()]
            for i, para in enumerate(paragraphs):
                docs.append({
                    "field_name": f"{file.stem}_entry_{i}",
                    "domain": "commerce",
                    "sub_domain": "general",
                    "data_type": "",
                    "constraints": "",
                    "professional_description": para,
                    "examples": "",
                    "related_fields": "",
                    "compliance_notes": "",
                })
            log.info("Extra: loaded %d paragraphs from %s", len(paragraphs), file.name)
 
    return docs
 
 
# ════════════════════════════════════════════════════════════════
# ENV VALIDATION
# ════════════════════════════════════════════════════════════════
 
def _validate_env() -> None:
    missing = [v for v in ("AZURE_SEARCH_ENDPOINT", "AZURE_SEARCH_ADMIN_KEY") if not os.getenv(v)]
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            "Copy .env.example to .env and fill in credentials."
        )
 
 
def _get_embedding(text: str, client: AzureOpenAI) -> List[float]:
    response = client.embeddings.create(input=text, model=EMBEDDING_DEPLOYMENT)
    return response.data[0].embedding
 
 
# ════════════════════════════════════════════════════════════════
# SEARCH CLIENT (USED BY RUNTIME)
# ════════════════════════════════════════════════════════════════
 
def get_search_client(index_name: str = None) -> Optional[SearchClient]:
    """
    Get a SearchClient instance for the specified or default index.
    Returns None if credentials are not configured.
    """
    if not AZURE_SEARCH_ENDPOINT or not AZURE_SEARCH_ADMIN_KEY:
        log.warning("Azure Search credentials not configured")
        return None
 
    try:
        credential = AzureKeyCredential(AZURE_SEARCH_ADMIN_KEY)
        target_index = index_name or INDEX_NAME
        search_client = SearchClient(
            endpoint=AZURE_SEARCH_ENDPOINT,
            index_name=target_index,
            credential=credential
        )
        log.info("SearchClient initialized for index '%s'", target_index)
        return search_client
    except Exception as e:
        log.error("Failed to initialize SearchClient: %s", e)
        return None
 
 
def upload_custom_kb(custom_kb: dict, index_name: str = "custom-kb-index") -> Optional[SearchClient]:
    """
    Upload custom knowledge base to Azure Search.
    Creates index if needed, uploads documents, returns search client.
    """
    log.info("━━ Custom KB Upload Process Started ━━")
 
    if not custom_kb:
        log.error("✗ Custom KB is None or empty")
        return None
 
    if not AZURE_SEARCH_ENDPOINT or not AZURE_SEARCH_ADMIN_KEY:
        log.error("✗ Azure Search credentials not configured: endpoint=%s, key=%s",
                 bool(AZURE_SEARCH_ENDPOINT), bool(AZURE_SEARCH_ADMIN_KEY))
        return None
 
    entries = custom_kb.get("entries", [])
    if not entries:
        log.error("✗ Custom KB has no 'entries' array or it's empty")
        return None
 
    log.info("📦 Uploading custom KB with %d entries to index '%s'", len(entries), index_name)
 
    try:
        credential = AzureKeyCredential(AZURE_SEARCH_ADMIN_KEY)
        index_client = SearchIndexClient(endpoint=AZURE_SEARCH_ENDPOINT, credential=credential)
        log.info("✓ Azure Search client initialized (endpoint: %s)", AZURE_SEARCH_ENDPOINT)
    except Exception as e:
        log.error("✗ Failed to initialize Azure Search client: %s", e, exc_info=True)
        return None
 
    # Create index
    try:
        log.info("📋 Creating index '%s'...", index_name)
        create_index_for_custom_kb(index_client, index_name)
        log.info("✓ Index '%s' created successfully", index_name)
    except ResourceExistsError:
        log.info("ℹ Index '%s' already exists, will update", index_name)
    except Exception as e:
        log.error("✗ Failed to create index '%s': %s", index_name, e, exc_info=True)
        return None
 
    # Prepare documents
    try:
        log.info("📄 Preparing %d documents...", len(entries))
        documents = prepare_documents(entries, None)  # No embeddings for custom KB
        log.info("✓ Prepared %d documents for upload", len(documents))
    except Exception as e:
        log.error("✗ Failed to prepare documents: %s", e, exc_info=True)
        return None
 
    # Upload
    try:
        log.info("📤 Uploading documents to index '%s'...", index_name)
        search_client = SearchClient(endpoint=AZURE_SEARCH_ENDPOINT, index_name=index_name, credential=credential)
        upload_documents(search_client, documents, batch_size=10)
        log.info("✓ Custom KB uploaded successfully to '%s'", index_name)
        return search_client
    except Exception as e:
        log.error("✗ Failed to upload custom KB: %s", e, exc_info=True)
        return None
 
 
def create_index_for_custom_kb(index_client: SearchIndexClient, index_name: str):
    """Create index for custom KB with semantic search enabled."""
    log.info("🔧 Configuring index schema with semantic search...")
   
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
        SearchableField(name="field_name", type=SearchFieldDataType.String, filterable=True, sortable=True),
        SimpleField(name="domain", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SimpleField(name="sub_domain", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SearchableField(name="professional_description", type=SearchFieldDataType.String, analyzer_name="en.microsoft"),
        SimpleField(name="data_type", type=SearchFieldDataType.String, filterable=True),
        SearchableField(name="constraints", type=SearchFieldDataType.String),
        SearchableField(name="examples", type=SearchFieldDataType.String),
        SearchableField(name="related_fields", type=SearchFieldDataType.String),
        SearchableField(name="compliance_notes", type=SearchFieldDataType.String),
    ]
 
    # Create semantic configuration for enhanced search
    semantic_config = SemanticConfiguration(
        name="custom-semantic",
        prioritized_fields=SemanticPrioritizedFields(
            title_field=SemanticField(field_name="field_name"),
            content_fields=[SemanticField(field_name="professional_description")],
            keywords_fields=[
                SemanticField(field_name="domain"),
                SemanticField(field_name="sub_domain"),
                SemanticField(field_name="constraints"),
            ],
        ),
    )
 
    index = SearchIndex(
        name=index_name,
        fields=fields,
        semantic_search=SemanticSearch(configurations=[semantic_config]),
    )
    log.info("✓ Index schema created with semantic search enabled")
 
    try:
        log.info("🚀 Submitting index to Azure Search Service...")
        index_client.create_index(index)
        log.info("✓ Index '%s' created successfully in Azure Search", index_name)
    except Exception as e:
        log.error("✗ Index creation failed: %s", e, exc_info=True)
        raise
 
 
# ════════════════════════════════════════════════════════════════
# RAG CONTEXT BUILDER
# ════════════════════════════════════════════════════════════════
 
def build_rag_context_block(tables: List[dict], search_client: SearchClient, top_k: int = 3, semantic_config_name: str = "commerce-semantic") -> str:
    if not tables or not search_client:
        return ""
 
    seen_queries = set()
    all_parts = []
 
    for table in tables:
        table_name = table.get("name", "")
        columns = table.get("columns", [])
 
        queries = (
            [f"{col.get('name', '')} {table_name}" for col in columns if col.get("name")]
            if columns else [table_name]
        )
 
        for query in queries:
            query = query.strip()
            if not query or query in seen_queries:
                continue
 
            seen_queries.add(query)
 
            try:
                # Try semantic search first
                results = list(search_client.search(
                    search_text=query,
                    query_type=QueryType.SEMANTIC,
                    semantic_configuration_name=semantic_config_name,
                    top=top_k,
                    select=[
                        "field_name",
                        "professional_description",
                        "constraints",
                        "related_fields",
                        "compliance_notes",
                        "sub_domain",
                    ],
                ))
            except Exception as semantic_exc:
                log.warning("Semantic search failed for '%s', trying regular search: %s", query, semantic_exc)
                try:
                    # Fall back to regular search
                    results = list(search_client.search(
                        search_text=query,
                        top=top_k,
                        select=[
                            "field_name",
                            "professional_description",
                            "constraints",
                            "related_fields",
                            "compliance_notes",
                            "sub_domain",
                        ],
                    ))
                except Exception as regular_exc:
                    log.warning("Regular search also failed for '%s': %s", query, regular_exc)
                    continue
 
            for r in results:
                part = (
                    f"Reference Field : {r['field_name']} [{r.get('sub_domain', '')}]\n"
                    f"Description     : {r['professional_description']}\n"
                    f"Constraints     : {r.get('constraints', '')}\n"
                    f"Related Fields  : {r.get('related_fields', '')}"
                )
                if r.get("compliance_notes"):
                    part += f"\nCompliance      : {r['compliance_notes']}"
                all_parts.append(part)
 
    if not all_parts:
        return ""
 
    separator = "\n\n---\n\n"
    return (
        "=== RAG KNOWLEDGE BASE CONTEXT ===\n"
        "Use these professional field descriptions.\n\n"
        + separator.join(all_parts)
        + "\n=== END RAG CONTEXT ==="
    )
 
 
# ════════════════════════════════════════════════════════════════
# STEP 1 — CREATE INDEX
# ════════════════════════════════════════════════════════════════
 
def create_index(index_client: SearchIndexClient) -> None:
    log.info("━━ Step 1: Creating index '%s' ━━", INDEX_NAME)
 
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
        SearchableField(name="field_name", type=SearchFieldDataType.String, filterable=True, sortable=True),
        SimpleField(name="domain", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SimpleField(name="sub_domain", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SearchableField(name="professional_description", type=SearchFieldDataType.String, analyzer_name="en.microsoft"),
        SimpleField(name="data_type", type=SearchFieldDataType.String, filterable=True),
        SearchableField(name="constraints", type=SearchFieldDataType.String),
        SearchableField(name="examples", type=SearchFieldDataType.String),
        SearchableField(name="related_fields", type=SearchFieldDataType.String),
        SearchableField(name="compliance_notes", type=SearchFieldDataType.String),
    ]
 
    vector_search = None
 
    if USE_VECTOR_SEARCH:
        fields.append(
            SearchField(
                name="description_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=EMBEDDING_DIMENSIONS,
                vector_search_profile_name="hnsw-profile",
            )
        )
        vector_search = VectorSearch(
            algorithms=[HnswAlgorithmConfiguration(name="hnsw-algo")],
            profiles=[VectorSearchProfile(name="hnsw-profile", algorithm_configuration_name="hnsw-algo")],
        )
        log.info("Vector search enabled (dimensions=%d)", EMBEDDING_DIMENSIONS)
 
    semantic_config = SemanticConfiguration(
        name="commerce-semantic",
        prioritized_fields=SemanticPrioritizedFields(
            title_field=SemanticField(field_name="field_name"),
            content_fields=[SemanticField(field_name="professional_description")],
            keywords_fields=[
                SemanticField(field_name="domain"),
                SemanticField(field_name="sub_domain"),
                SemanticField(field_name="constraints"),
            ],
        ),
    )
 
    index = SearchIndex(
        name=INDEX_NAME,
        fields=fields,
        semantic_search=SemanticSearch(configurations=[semantic_config]),
        vector_search=vector_search,
    )
 
    try:
        index_client.create_index(index)
        log.info("✓ Index created successfully")
 
    except (ResourceExistsError, HttpResponseError) as exc:
        log.warning("Index already exists — deleting and recreating")
        index_client.delete_index(INDEX_NAME)
        time.sleep(2)
        index_client.create_index(index)
        log.info("✓ Index recreated successfully")
 
 
# ════════════════════════════════════════════════════════════════
# STEP 2 — PREPARE DOCUMENTS
# ════════════════════════════════════════════════════════════════
 
def prepare_documents(raw_docs: List[dict], openai_client: Optional[AzureOpenAI] = None) -> List[dict]:
    log.info("━━ Step 2: Preparing %d documents ━━", len(raw_docs))
 
    prepared = []
 
    for doc in tqdm(raw_docs, desc="Preparing", unit="doc"):
        entry = {
            "id": str(uuid.uuid4()),
            "field_name": doc.get("field_name", ""),
            "domain": doc.get("domain", "commerce"),
            "sub_domain": doc.get("sub_domain", "general"),
            "professional_description": doc.get("professional_description", ""),
            "data_type": doc.get("data_type", ""),
            "constraints": doc.get("constraints", ""),
            "examples": doc.get("examples", ""),
            "related_fields": doc.get("related_fields", ""),
            "compliance_notes": doc.get("compliance_notes", ""),
        }
 
        # Print extracted field information to terminal
        log.info("  📝 Field: %s | Domain: %s | Type: %s",
                 entry["field_name"], entry["domain"], entry["data_type"])
 
        if USE_VECTOR_SEARCH and openai_client:
            embed_text = (
                f"{entry['field_name']} {entry['professional_description']} "
                f"{entry['constraints']} {entry['related_fields']}"
            )
            try:
                entry["description_vector"] = _get_embedding(embed_text, openai_client)
                log.debug("  🔢 Vector embedding created for: %s", entry["field_name"])
            except Exception as exc:
                log.warning("Embedding failed for '%s': %s", entry["field_name"], exc)
 
        prepared.append(entry)
 
    return prepared
 
 
# ════════════════════════════════════════════════════════════════
# STEP 3 — UPLOAD DOCUMENTS
# ════════════════════════════════════════════════════════════════
 
def upload_documents(search_client: SearchClient, documents: List[dict], batch_size: int = 5) -> None:
    log.info("━━ Step 3: Uploading %d documents (batch_size=%d) ━━", len(documents), batch_size)
 
    total_uploaded = 0
    total_batches = (len(documents) + batch_size - 1) // batch_size
 
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i + batch_size]
        batch_num = i // batch_size + 1
        attempt = 0
 
        while attempt < 3:
            try:
                log.info("  📦 Batch %d/%d: uploading %d documents...", batch_num, total_batches, len(batch))
                result = search_client.upload_documents(documents=batch)
                failed = [r for r in result if not r.succeeded]
 
                if failed:
                    log.warning("  ⚠ %d docs failed in batch %d/%d", len(failed), batch_num, total_batches)
                    for f in failed:
                        log.warning("    key=%s  error=%s", f.key, f.error_message)
 
                total_uploaded += len(batch) - len(failed)
                log.info("  ✓ Batch %d/%d done (%d docs uploaded)", batch_num, total_batches, len(batch) - len(failed))
                break
 
            except Exception as exc:
                attempt += 1
                wait = 2 ** attempt
                log.warning(
                    "  ⚠ Batch %d/%d failed (attempt %d/3), retrying in %ds: %s",
                    batch_num, total_batches, attempt, wait, exc,
                )
                time.sleep(wait)
 
        if attempt >= 3:
            log.error("  ✗ Batch %d/%d failed after 3 attempts", batch_num, total_batches)
 
        time.sleep(0.5)
 
    log.info("━━ Upload Complete: %d / %d documents uploaded ━━", total_uploaded, len(documents))
 
 
# ════════════════════════════════════════════════════════════════
# STEP 4 — VERIFY INDEX
# ════════════════════════════════════════════════════════════════
 
def verify_index(search_client: SearchClient) -> None:
    log.info("━━ Step 4: Verifying index ━━")
 
    test_queries = [
        "customer email unique identifier",
        "order total payment amount",
        "stock quantity inventory warehouse",
    ]
 
    for query_text in test_queries:
        try:
            results = list(search_client.search(
                search_text=query_text,
                query_type=QueryType.SEMANTIC,
                semantic_configuration_name="commerce-semantic",
                top=1,
                select=["field_name", "domain", "professional_description"],
            ))
 
            if results:
                top = results[0]
                snippet = top["professional_description"][:80] + "..."
                log.info("  ✓ %-40s → %-25s %s",
                         f"'{query_text}'",
                         f"{top['field_name']} [{top['domain']}]",
                         snippet)
            else:
                log.warning("No results for: '%s'", query_text)
 
        except Exception as exc:
            log.warning("Verification query failed: %s", exc)
 
    log.info("Verification complete")
 
 
# ════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════
 
def main() -> None:
    print("\n" + "═" * 60)
    print("  Azure AI Search — Commerce RAG Index Setup")
    print("═" * 60 + "\n")
 
    _validate_env()
 
    credential = AzureKeyCredential(AZURE_SEARCH_ADMIN_KEY)
    index_client = SearchIndexClient(endpoint=AZURE_SEARCH_ENDPOINT, credential=credential)
    search_client = SearchClient(endpoint=AZURE_SEARCH_ENDPOINT, index_name=INDEX_NAME, credential=credential)
 
    openai_client = None
    if USE_VECTOR_SEARCH:
        openai_client = AzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_KEY,
            api_version=AZURE_OPENAI_API_VER,
        )
        log.info("Azure OpenAI client initialised for embeddings")
 
    kb_entries = load_knowledge_base()
    extra_docs = load_extra_documents(KNOWLEDGE_BASE_DIR)
    all_docs = kb_entries + extra_docs
 
    log.info("Total entries: %d  (%d base + %d extra)", len(all_docs), len(kb_entries), len(extra_docs))
 
    create_index(index_client)
    time.sleep(2)
 
    documents = prepare_documents(all_docs, openai_client)
    upload_documents(search_client, documents)
 
    time.sleep(3)
 
    verify_index(search_client)
 
    print("\n" + "═" * 60)
    print("  ✅ Setup complete!")
    print(f"  Index  : {INDEX_NAME}")
    print(f"  Docs   : {len(documents)}")
    print(f"  Vector : {'enabled' if USE_VECTOR_SEARCH else 'disabled'}")
    print("═" * 60 + "\n")
 
 
if __name__ == "__main__":
    main()
 