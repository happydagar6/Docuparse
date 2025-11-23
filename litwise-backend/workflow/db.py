from supabase import create_client, Client
from qdrant_client import QdrantClient
from dotenv import load_dotenv
import os
load_dotenv()

supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
qdrant = QdrantClient(os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"))

# Create Qdrant collection if it doesn't exist
qdrant.recreate_collection(
    collection_name="litwise_collection",
    vectors_config={"size": 1536, "distance": "Cosine"},
)
