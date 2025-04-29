# api/client.py
import requests
import os

class APIClient:
    def __init__(self, token=None):
        self.token = token
        self.api_url = os.environ["API_URL"]
    
    def _get_headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}
    
    def get_branches(self):
        return requests.get(
            f"{self.api_url}/branches/",
            headers=self._get_headers()
        )
    
    # Add more API methods as needed...