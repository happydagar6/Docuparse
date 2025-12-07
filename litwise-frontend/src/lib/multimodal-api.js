/**
 * Multi-Modal API Functions
 * Handles fetching images and tables from backend
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Fetch multi-modal content (images + tables) for a paper
 *
 * @param {string} paperId - Paper UUID
 * @returns {Promise<{images: Array, tables: Array, total_images: number, total_tables: number}>}
 */

export async function getMultiModalContent(paperId) {
  if (!paperId) {
    throw new Error("Paper ID is required to fetch multi-modal content.");
  }

  try {
    const response = await fetch(
      `${API_BASE_URL}/api/papers/${paperId}/multimodal`,
      {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
        },
        // Add timeout
        signal: AbortSignal.timeout(20000), // 20 seconds timeout
      }
    );

    if (!response.ok) {
      const error = await response
        .json()
        .catch(() => ({ message: "Unknown error" }));
      throw new Error(
        error.message ||
          `Error fetching multi-modal content: ${response.statusText}`
      );
    }

    const data = await response.json();

    // Validate response structure
    if (!data || typeof data !== "object") {
      throw new Error("Invalid response format from multi-modal content API.");
    }

    return {
      paper_id: data.paper_id,
      images: Array.isArray(data.images) ? data.images : [],
      tables: Array.isArray(data.tables) ? data.tables : [],
      total_images: data.total_images || 0,
      total_tables: data.total_tables || 0,
    };
  } catch (error) {
    console.error("[Multi-Modal API] Error fetching content:", error);
    throw error;
  }
}


/**
 * Get full image base64 data (if truncated in initial response)
 * This is a placeholder - implement if backend provides separate endpoint
 */

export async function getFullImageData(paperId, imageHash){
    // TODO: Implement if backend provides endpoint for full image retrieval
    throw new Error("getFullImageData not implemented.");
}