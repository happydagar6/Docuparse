"""
Async wrapper for LangGraph pipeline to enable non-blocking processing
"""

import asyncio
from typing import Dict, Any
from concurrent.futures import ThreadPoolExecutor
import logging

# Configure logging for async operations
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AsyncPipelineWrapper:
    """
    Async wrapper for the LangGraph pipeline to prevent blocking operations
    """
    
    def __init__(self, pipeline_app):
        """
        Initialize with the LangGraph application
        
        Args:
            pipeline_app: The LangGraph application instance
        """
        self.pipeline_app = pipeline_app
        self.executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="pipeline_worker")
    
    async def process_async(self, text: str, background: bool = False) -> Dict[str, Any]:
        """
        Process text through LangGraph pipeline asynchronously
        
        Args:
            text: Input text to process
            background: If True, returns immediately with a task ID for status checking
            
        Returns:
            Processing result or task information
        """
        try:
            if background:
                # Start background processing and return task info
                task = asyncio.create_task(self._run_pipeline_async(text))
                return {
                    "status": "processing",
                    "task_id": id(task),
                    "message": "Processing started in background"
                }
            else:
                # Run and wait for completion
                result = await self._run_pipeline_async(text)
                return {
                    "status": "completed",
                    "result": result,
                    "message": "Processing completed successfully"
                }
                
        except Exception as e:
            logger.error(f"Async pipeline processing failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": "Processing failed"
            }
    
    async def _run_pipeline_async(self, text: str) -> Dict[str, Any]:
        """
        Internal method to run pipeline in thread pool
        """
        loop = asyncio.get_running_loop()
        
        # Run the blocking pipeline operation in a thread pool
        result = await loop.run_in_executor(
            self.executor,
            self._invoke_pipeline,
            text
        )
        
        return result
    
    def _invoke_pipeline(self, text: str) -> Dict[str, Any]:
        """
        Synchronous pipeline invocation (runs in thread pool)
        """
        try:
            logger.info(f"Starting LangGraph pipeline processing for {len(text)} characters")
            result = self.pipeline_app.invoke({"text": text, "summary": {}})
            logger.info("LangGraph pipeline processing completed successfully")
            return result
        except Exception as e:
            logger.error(f"LangGraph pipeline processing failed: {e}")
            raise e
    
    async def process_with_timeout(self, text: str, timeout_seconds: int = 300) -> Dict[str, Any]:
        """
        Process with timeout to prevent indefinite hanging
        
        Args:
            text: Input text to process
            timeout_seconds: Maximum processing time (default 5 minutes)
            
        Returns:
            Processing result or timeout error
        """
        try:
            result = await asyncio.wait_for(
                self._run_pipeline_async(text),
                timeout=timeout_seconds
            )
            return {
                "status": "completed",
                "result": result,
                "processing_time": f"< {timeout_seconds}s"
            }
        except asyncio.TimeoutError:
            logger.error(f"Pipeline processing timed out after {timeout_seconds} seconds")
            return {
                "status": "timeout",
                "error": f"Processing timed out after {timeout_seconds} seconds",
                "message": "Consider using background processing for large documents"
            }
        except Exception as e:
            logger.error(f"Pipeline processing failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": "Processing failed"
            }
    
    def cleanup(self):
        """
        Cleanup resources
        """
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)

# Global instance (will be initialized in app.py)
async_pipeline_wrapper = None

def get_async_pipeline(pipeline_app):
    """
    Get or create async pipeline wrapper instance
    """
    global async_pipeline_wrapper
    if async_pipeline_wrapper is None:
        async_pipeline_wrapper = AsyncPipelineWrapper(pipeline_app)
    return async_pipeline_wrapper