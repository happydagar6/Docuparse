from supabase import create_client, Client
from qdrant_client import QdrantClient
from qdrant_client.http import models
from dotenv import load_dotenv
import os
load_dotenv()

# We use the Service Role Key for Supabase to bypass Row Level Security internally.
# The user's JWT validates authorization at the API route level before reaching here.
supabase: Client = create_client(os.getenv("SUPABASE_URL", ""), os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""))

# We connect to Qdrant Cloud for our Vector Database.
qdrant = QdrantClient(
    os.getenv("QDRANT_URL"), 
    api_key=os.getenv("QDRANT_API_KEY"),
    timeout=120,  # 2 minutes timeout for large uploads
    check_compatibility=False  # Suppress version mismatch warning (client works fine with newer server)
)

# Create Qdrant collection if it doesn't exist
try:
    # Check if collection exists
    if not qdrant.collection_exists("litwise_collection"):
        print("✅ Creating new Qdrant collection for OpenAI multimodal embeddings...")
        # OpenAI text-embedding-3-small uses 1536-dimensional vectors
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
        
        print("✅ Collection created with OpenAI embeddings support (1536 dimensions)")
    else:
        # Collection exists - verify it's the right size
        try:
            collection_info = qdrant.get_collection("litwise_collection")
            vectors_config = collection_info.config.params.vectors
            
            if hasattr(vectors_config, "size"):
                vector_size = vectors_config.size
            elif isinstance(vectors_config, dict) and "size" in vectors_config:
                vector_size = vectors_config["size"]
            else:
                vector_size = 0
            
            if vector_size == 1536:
                print(f"✅ Collection exists with correct vector size: {vector_size} (OpenAI text-embedding-3-small compatible)")
            elif vector_size == 3072:
                print(f"❌ CRITICAL: Collection has OLD vector size {vector_size}, but code uses text-embedding-3-small (1536)")
                print(f"    You MUST recreate the collection! Run: python -c \"from workflow.db import qdrant; qdrant.delete_collection('litwise_collection')\"")
                print(f"    Then restart the server to auto-create with 1536 dimensions")
            else:
                print(f"⚠️  Collection vector size is {vector_size}, expected 1536 for text-embedding-3-small")
                print(f"    Using current collection as-is for compatibility")
        except Exception as e:
            print(f"⚠️  Could not verify collection size: {e}")
        
        # Try to create indexes if they don't exist
        try:
            qdrant.create_payload_index(
                collection_name="litwise_collection",
                field_name="paper_id",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
        except Exception as e:
            print(f"📌 Index for 'paper_id' may already exist")
        
        try:
            qdrant.create_payload_index(
                collection_name="litwise_collection",
                field_name="page",
                field_schema=models.PayloadSchemaType.INTEGER
            )
        except Exception as e:
            print(f"📌 Index for 'page' may already exist")
except Exception as e:
    print(f"❌ Error setting up Qdrant collection: {e}")
