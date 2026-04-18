#!/usr/bin/env python3
"""
Test Azure Search connectivity and basic operations
"""
import os
import logging
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents import SearchClient

# Load environment
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

def test_azure_search():
    """Test basic Azure Search connectivity"""

    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    admin_key = os.getenv("AZURE_SEARCH_ADMIN_KEY")

    if not endpoint or not admin_key:
        log.error("❌ Missing AZURE_SEARCH_ENDPOINT or AZURE_SEARCH_ADMIN_KEY")
        return False

    log.info(f"🔍 Testing Azure Search at: {endpoint}")

    try:
        # Test credentials
        credential = AzureKeyCredential(admin_key)
        index_client = SearchIndexClient(endpoint=endpoint, credential=credential)

        # List existing indexes
        indexes = list(index_client.list_indexes())
        log.info(f"📋 Found {len(indexes)} existing indexes:")
        for idx in indexes:
            log.info(f"  - {idx.name}")

        # Test creating a simple index
        test_index_name = "test-connection-index"

        # Delete if exists
        try:
            index_client.delete_index(test_index_name)
            log.info(f"🗑️ Deleted existing test index: {test_index_name}")
        except:
            pass

        # Create simple test index
        from azure.search.documents.indexes.models import (
            SearchIndex, SimpleField, SearchFieldDataType
        )

        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SimpleField(name="test_field", type=SearchFieldDataType.String, searchable=True)
        ]

        index = SearchIndex(name=test_index_name, fields=fields)
        index_client.create_index(index)
        log.info(f"✅ Created test index: {test_index_name}")

        # Test search client
        search_client = SearchClient(
            endpoint=endpoint,
            index_name=test_index_name,
            credential=credential
        )

        # Upload test document
        test_doc = {"id": "test-1", "test_field": "Hello Azure Search!"}
        result = search_client.upload_documents([test_doc])
        log.info(f"📤 Uploaded test document: {result[0].succeeded}")

        # Search for it
        results = list(search_client.search("Hello"))
        log.info(f"🔎 Found {len(results)} results for 'Hello'")

        # Clean up
        index_client.delete_index(test_index_name)
        log.info(f"🧹 Cleaned up test index: {test_index_name}")

        log.info("✅ Azure Search connectivity test PASSED")
        return True

    except HttpResponseError as e:
        log.error(f"❌ HTTP Error: {e.status_code} - {e.message}")
        if e.status_code == 403:
            log.error("🔐 Check your admin key permissions")
        elif e.status_code == 404:
            log.error("🌐 Check your endpoint URL")
        return False
    except Exception as e:
        log.error(f"❌ Unexpected error: {type(e).__name__}: {e}")
        return False

if __name__ == "__main__":
    success = test_azure_search()
    exit(0 if success else 1)