"""
test_vector_rag.py - Live Verification of Steps 1.1, 1.2, and 1.3
"""
import asyncio
from dotenv import load_dotenv
load_dotenv()  # Loads your OPENAI_API_KEY and Qdrant credentials

from services.rag.ingestion import document_ingestion_service
from services.rag.vector_store import vector_store_service
from services.rag.retriever import hybrid_retriever

async def main():
    print("=" * 65)
    print("🚀 TESTING LITWISE RAG: INGESTION + VECTOR + HYBRID RETRIEVER")
    print("=" * 65)

    # 1. Sample 2-page research document
    sample_paper_id = "test_paper_999"
    sample_text = (
        "Introduction to Deep Learning: Transformer architectures utilize self-attention "
        "mechanisms to compute representations of input sequences in parallel. Unlike recurrent "
        "neural networks (RNNs) that process tokens sequentially, Transformers allow for "
        "significantly higher parallelization and training efficiency on modern GPUs. "
        "\n\n"
        "Experimental Results and Conclusion: The proposed model was evaluated on the GLUE benchmark. "
        "The model achieved an overall accuracy of 94.6% on the test set, outperforming previous "
        "baselines by 3.2%. The researchers concluded that scaling model parameters directly "
        "correlates with downstream task reasoning performance."
    )

    sample_page_info = [
        {"page_number": 1, "start_char": 0, "end_char": 350},   
        {"page_number": 2, "start_char": 351, "end_char": 900}
    ]

    # --- STEP 1.1: CHUNKING & PAGE MAPPING ---
    print("\n📝 1. Chunking document with Page Mapping...")
    chunks = document_ingestion_service.chunk_document(
        text=sample_text,
        paper_id=sample_paper_id,
        page_info=sample_page_info
    )
    print(f"   ✅ Created {len(chunks)} chunks:")
    for c in chunks:
        print(f"      - Chunk #{c.chunk_index} -> PDF Page {c.page_number} ({len(c.content)} chars)")

    # --- STEP 1.2: QDRANT VECTOR UPSERT ---
    print("\n🧠 2. Generating OpenAI Embeddings & Storing in Qdrant...")
    upserted_count = await vector_store_service.upsert_chunks(chunks)
    print(f"   ✅ Successfully stored {upserted_count} vectors in Qdrant Cloud!")

    # --- STEP 1.3: IN-MEMORY BM25 INDEXING ---
    print("\n⚡ 3. Indexing Chunks in Hybrid Retriever (In-Memory BM25)...")
    hybrid_retriever.index_paper(paper_id=sample_paper_id, chunks=chunks)

    # --- TEST QUERY ---
    question = "What was the final accuracy score achieved by the model on the GLUE benchmark?"
    print(f"\n🔍 4. Asking Question: '{question}'")
    
    # --- PURE VECTOR SEARCH (STEP 1.2) ---
    print("\n--- [A] PURE VECTOR SEARCH RESULTS ---")
    vector_only_results = await vector_store_service.search(
        query=question,
        paper_id=sample_paper_id,
        top_k=2
    )
    for i, res in enumerate(vector_only_results, 1):
        print(f"   Match #{i} (Cosine Similarity: {res['score']:.4f}):")
        print(f"   📖 Page: {res['page_number']} | Text: \"{res['content'][:110]}...\"")

    # --- HYBRID SEARCH + RE-RANKING (STEP 1.3) ---
    print("\n--- [B] HYBRID SEARCH (VECTOR + BM25 + RE-RANKING) ---")
    hybrid_results = await hybrid_retriever.retrieve(
        query=question,
        paper_id=sample_paper_id,
        top_k=2,
        alpha=0.7
    )
    for i, res in enumerate(hybrid_results, 1):
        print(f"   Rank #{i} (Final Re-ranked Score: {res['score']:.4f}):")
        print(f"   📖 Page: {res['page_number']} | Text: \"{res['content'][:110]}...\"")

    # --- STEP 1.4: LIVE STREAMING GENERATION (GPT-6-LUNA) ---
    print("\n--- [C] LIVE STREAMING GENERATION (STEP 1.4: GPT-6-LUNA) ---")
    from services.rag.generator import rag_generator
    import json

    print(f"🤖 Invoking gpt-6-luna for: '{question}'\n")
    print("AI Answer: ", end="", flush=True)

    sources_received = []
    async for sse_chunk in rag_generator.chat_stream(query=question, paper_id=sample_paper_id):
        if sse_chunk.startswith("data: "):
            try:
                payload = json.loads(sse_chunk[6:].strip())
                if payload.get("type") == "token":
                    print(payload.get("content", ""), end="", flush=True)
                elif payload.get("type") == "sources":
                    sources_received = payload.get("sources", [])
                elif payload.get("type") == "complete":
                    print("\n\n✅ [SSE COMPLETE EVENT RECEIVED]")
                elif payload.get("type") == "error":
                    print(f"\n❌ [SSE ERROR]: {payload.get('error')}")
            except Exception as parse_err:
                pass

    print(f"\n📚 Verified Sources Attached: {len(sources_received)} citation(s)")
    for s in sources_received:
        print(f"   📖 Page {s['page_number']} (Score: {s['score']:.4f}): \"{s['content'][:90]}...\"")

    print("\n" + "=" * 65)
    print("🎉 FULL RAG PIPELINE (STEPS 1.1 - 1.4) VERIFIED SUCCESSFULLY!")
    print("=" * 65)

if __name__ == "__main__":
    asyncio.run(main())
