import uvicorn
if __name__ == "__main__":
    uvicorn.run(
        "app:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        limit_max_requests=1000,
        timeout_keep_alive=120,
        # Allow up to 40MB requests (slightly more than 35MB to account for multipart overhead)
        limit_concurrency=100
    )