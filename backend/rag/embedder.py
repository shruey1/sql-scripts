import time
import logging
from openai import APIError, RateLimitError
from config import openai_client, AZURE_OPENAI_EMBEDDING_DEPLOYMENT

logger = logging.getLogger(__name__)

# ————————
# SINGLE EMBEDDING
# ————————
def generate_embedding(
    text: str,
    max_retries: int = 4,
    base_delay: float = 1.0,
) -> list[float]:
    """
    Generates an embedding vector for the given text.
    Retries on rate-limit or transient API errors with exponential backoff.
    """
    for attempt in range(1, max_retries + 1):
        try:
            response = openai_client.embeddings.create(
                model=AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
                input=text,
            )
            return response.data[0].embedding

        except RateLimitError as e:
            wait = base_delay * (2 ** (attempt - 1))
            logger.warning(
                f"Rate limited (attempt {attempt}/{max_retries}). "
                f"Retrying in {wait:.1f}s... [{e}]"
            )
            time.sleep(wait)

        except APIError as e:
            if attempt == max_retries:
                logger.error(f"API error after {max_retries} attempts: {e}")
                raise

            wait = base_delay * (2 ** (attempt - 1))
            logger.warning(
                f"API error (attempt {attempt}/{max_retries}). "
                f"Retrying in {wait:.1f}s... [{e}]"
            )
            time.sleep(wait)

    raise RuntimeError(f"Failed to generate embedding after {max_retries} retries.")


# ————————
# BATCHED EMBEDDINGS
# ————————
def generate_embeddings_batch(
    chunks: list[str],
    batch_size: int = 16,
) -> list[list[float]]:
    """
    Generates embeddings for a list of chunks in batches to reduce API round-trips.
    Returns a list of embedding vectors in the same order as the input chunks.
    """
    all_embeddings: list[list[float]] = []

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i: i + batch_size]
        logger.info(f"  Embedding batch {i // batch_size + 1} ({len(batch)} chunks)...")

        for attempt in range(1, 5):
            try:
                response = openai_client.embeddings.create(
                    model=AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
                    input=batch,
                )

                # API returns items with .index attribute; sort to preserve order
                sorted_data = sorted(response.data, key=lambda x: x.index)
                all_embeddings.extend([item.embedding for item in sorted_data])
                break

            except RateLimitError as e:
                wait = 1.0 * (2 ** (attempt - 1))
                logger.warning(
                    f"Rate limited on batch (attempt {attempt}/4). "
                    f"Retrying in {wait:.1f}s... [{e}]"
                )
                time.sleep(wait)

            except APIError as e:
                if attempt == 4:
                    logger.error(f"Batch embedding failed after 4 attempts: {e}")
                    raise

                wait = 1.0 * (2 ** (attempt - 1))
                logger.warning(
                    f"API error on batch (attempt {attempt}/4). "
                    f"Retrying in {wait:.1f}s... [{e}]"
                )
                time.sleep(wait)

    return all_embeddings