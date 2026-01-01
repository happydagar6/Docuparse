"use client";

export function RateLimitError({ error, onRetry, waitTime = 60 }) {
  const [countdown, setCountdown] = React.useState(waitTime);

  React.useEffect(() => {
    if (countdown <= 0) return; // Stop countdown at 0

    const timer = setInterval(() => {
      setCountdown((prev) => Math.max(0, prev - 1));
    }, 1000);

    return () => clearInterval(timer); // Cleanup on unmount
  }, [countdown]);

  return (
    <div className="fixed top-4 right-4 bg-red-500 text-white p-4 rounded-lg shadow-lg max-w-sm">
      <h3 className="font-bold mb-2">Too Many Requests</h3>
      <p className="text-sm mb-3">
        {error?.detail || "You are making requests too quickly."}
      </p>
      <div className="flex items-center justify-between">
        <span className="text-sm">
          Retry in: <strong>{countdown}s</strong>
        </span>
        {countdown === 0 && (
          <button
            onClick={onRetry}
            className="bg-white text-red-500 px-3 py-1 rounded text-sm font-semibold hover:bg-gray-100"
          >
            Retry Now
          </button>
        )}
      </div>
    </div>
  );
}
