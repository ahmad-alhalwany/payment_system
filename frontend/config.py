import os
# http://localhost:8000
# https://payment-system-y2x3.onrender.com
# Default configuration
DEFAULT_CONFIG = {
    "API_URL": "http://localhost:8000",
}

def setup_environment():
    """Set up environment variables if they don't exist."""
    for key, default_value in DEFAULT_CONFIG.items():
        if key not in os.environ:
            os.environ[key] = default_value

def get_api_url():
    """Get the API URL from environment variables."""
    return os.environ.get("API_URL", DEFAULT_CONFIG["API_URL"]) 