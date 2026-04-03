import os
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from openai import AzureOpenAI
load_dotenv()
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_EMBEDDING_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_API_KEY = os.getenv("AZURE_SEARCH_API_KEY")
SQL_INDEX = "sql-docs-index"
BP_INDEX = "schema-best-practices-index"
openai_client = AzureOpenAI(
   api_key=AZURE_OPENAI_API_KEY,
   api_version="2024-02-15-preview",
   azure_endpoint=AZURE_OPENAI_ENDPOINT
)
credential = AzureKeyCredential(AZURE_SEARCH_API_KEY)

def generate_embedding(text):
   response = openai_client.embeddings.create(
       model=AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
       input=text
   )
   return response.data[0].embedding

def search_index(query, index_name):
   search_client = SearchClient(
       endpoint=AZURE_SEARCH_ENDPOINT,
       index_name=index_name,
       credential=credential
   )
   embedding = generate_embedding(query)
   vector_query = VectorizedQuery(
       vector=embedding,
       k_nearest_neighbors=5,
       fields="content_vector"
   )
   results = search_client.search(
       search_text=None,
       vector_queries=[vector_query]
   )
   for r in results:
       print(r["content"])
       print("------")

if __name__ == "__main__":
   query = input("Enter query: ")
   if "best practice" in query.lower():
       search_index(query, BP_INDEX)
   else:
       search_index(query, SQL_INDEX)