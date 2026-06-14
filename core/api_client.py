"""
Backend API Client - HTTP client for communicating with FastAPI backend
Handles scan result uploads and history retrieval
"""
import requests
from typing import Dict, List, Optional
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class BackendClient:
    """HTTP client for backend API communication."""

    def __init__(self, base_url: str = "http://localhost:8000", timeout: int = 10):
        """Initialize the client with a base URL and configure automatic retries."""
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

        # Create session with connection pooling
        self.session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,  # 1s, 2s, 4s
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def is_online(self) -> bool:
        """Perform a quick health-check GET and return True if the backend responds 200."""
        try:
            response = self.session.get(
                f"{self.base_url}/health",
                timeout=3  # Quick timeout for health check
            )
            return response.status_code == 200
        except Exception:
            return False

    def check_health(self) -> Optional[Dict]:
        """Return the backend health JSON payload, or None if the request fails."""
        try:
            response = self.session.get(
                f"{self.base_url}/health",
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Health check failed: {e}")
            return None

    def save_scan_result(self, filename: str, label: str, file_hash: str) -> Optional[Dict]:
        """POST a scan result to the backend and return the response dict, or None on failure."""
        try:
            payload = {
                "filename": filename,
                "label": label,
                "file_hash": file_hash
            }

            response = self.session.post(
                f"{self.base_url}/scanning-file",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"Failed to save scan result: {e}")
            return None

    def get_scan_history(self, limit: int = 10, offset: int = 0) -> Optional[List[Dict]]:
        """Fetch paginated scan history from the backend; returns a list or None on failure."""
        try:
            params = {
                "limit": min(limit, 100),  # Max 100
                "offset": max(offset, 0)   # Min 0
            }

            response = self.session.get(
                f"{self.base_url}/history-scan",
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"Failed to get scan history: {e}")
            return None

    def batch_upload(self, scan_results: List[Dict]) -> Dict[str, int]:
        """Upload a list of scan results one by one and return success/failure counts."""
        success_count = 0
        failure_count = 0

        for result in scan_results:
            response = self.save_scan_result(
                filename=result.get("filename"),
                label=result.get("label"),
                file_hash=result.get("file_hash")
            )

            if response:
                success_count += 1
            else:
                failure_count += 1

            # Small delay to avoid overwhelming server
            time.sleep(0.1)

        return {
            "success": success_count,
            "failed": failure_count
        }

    def close(self):
        """Close the underlying requests session and free connection resources."""
        self.session.close()

    def __enter__(self):
        """Support usage as a context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close the session when exiting a context manager block."""
        self.close()


# Example usage
if __name__ == "__main__":
    # Test connection
    client = BackendClient()

    # Check health
    health = client.check_health()
    print(f"Backend health: {health}")

    # Check if online
    online = client.is_online()
    print(f"Backend online: {online}")

    if online:
        # Save a test scan result
        result = client.save_scan_result(
            filename="test.exe",
            label="Malware",
            file_hash="test_hash_123"
        )
        print(f"Save result: {result}")

        # Get history
        history = client.get_scan_history(limit=5)
        print(f"History: {history}")

    client.close()
