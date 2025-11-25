from supabase import create_client, Client
from qdrant_client import QdrantClient
from qdrant_client.http import models
from dotenv import load_dotenv
import os
load_dotenv()

supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
qdrant = QdrantClient(os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"))

# Create Qdrant collection if it doesn't exist
try:
    # Check if collection exists
    if not qdrant.collection_exists("litwise_collection"):
        print("Creating new collection with proper indexing...")
        qdrant.create_collection(
            collection_name="litwise_collection",
            vectors_config=models.VectorParams(size=1536, distance=models.Distance.COSINE),
        )
        
        # Create payload index for the 'paper_id' field
        qdrant.create_payload_index(
            collection_name="litwise_collection",
            field_name="paper_id",
            field_schema=models.PayloadSchemaType.KEYWORD
        )
        
        # Create index for other commonly used fields
        qdrant.create_payload_index(
            collection_name="litwise_collection",
            field_name="page",
            field_schema=models.PayloadSchemaType.INTEGER
        )
        
        print("Collection created with proper indexing")
    else:
        print("Collection already exists, checking indexes...")
        # Try to create indexes if they don't exist (will fail silently if they exist)
        try:
            qdrant.create_payload_index(
                collection_name="litwise_collection",
                field_name="paper_id",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
        except Exception as e:
            print(f"Index for 'paper_id' may already exist: {e}")
        
        try:
            qdrant.create_payload_index(
                collection_name="litwise_collection",
                field_name="page",
                field_schema=models.PayloadSchemaType.INTEGER
            )
        except Exception as e:
            print(f"Index for 'page' may already exist: {e}")
except Exception as e:
    print(f"Error setting up Qdrant collection: {e}")
