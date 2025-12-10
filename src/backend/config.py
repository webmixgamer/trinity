"""
Configuration constants for the Trinity backend.
"""
import os

# Development Mode
# Set DEV_MODE_ENABLED=true to enable local username/password login
# When false (default), only Auth0 OAuth is allowed
DEV_MODE_ENABLED = os.getenv("DEV_MODE_ENABLED", "false").lower() == "true"

# JWT Settings
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Service URLs
AUDIT_URL = os.getenv("AUDIT_URL", "http://audit-logger:8001")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Auth0 Configuration
# Set these environment variables to enable Auth0 authentication
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN", "")  # e.g., "your-tenant.us.auth0.com"
AUTH0_ALLOWED_DOMAIN = os.getenv("AUTH0_ALLOWED_DOMAIN", "")  # e.g., "your-company.com" (leave empty to allow all)

# OAuth Provider Configs
OAUTH_CONFIGS = {
    "google": {
        "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
    },
    "slack": {
        "client_id": os.getenv("SLACK_CLIENT_ID", ""),
        "client_secret": os.getenv("SLACK_CLIENT_SECRET", ""),
    },
    "github": {
        "client_id": os.getenv("GITHUB_CLIENT_ID", ""),
        "client_secret": os.getenv("GITHUB_CLIENT_SECRET", ""),
    },
    "notion": {
        "client_id": os.getenv("NOTION_CLIENT_ID", ""),
        "client_secret": os.getenv("NOTION_CLIENT_SECRET", ""),
    }
}

# CORS Origins
# Add your production domains to EXTRA_CORS_ORIGINS environment variable (comma-separated)
_extra_origins = os.getenv("EXTRA_CORS_ORIGINS", "").split(",")
_extra_origins = [o.strip() for o in _extra_origins if o.strip()]

CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8080",
] + _extra_origins

# GitHub Templates
# Configure your own GitHub agent templates here or via a config file.
# Format: github:owner/repo - requires GITHUB_PAT credential for private repos
# See docs/AGENT_TEMPLATE_SPEC.md for template structure
GITHUB_TEMPLATES = []

# Example template configuration (uncomment and customize):
# GITHUB_TEMPLATES = [
#     {
#         "id": "github:your-org/your-agent",
#         "display_name": "Your Agent Name",
#         "description": "Description of what your agent does",
#         "github_repo": "your-org/your-agent",
#         "github_credential_id": "your-github-pat-credential-id",  # From Trinity credentials
#         "source": "github",
#         "resources": {"cpu": "2", "memory": "4g"},
#         "mcp_servers": [],
#         "required_credentials": []
#     }
# ]

# Combined templates list
ALL_GITHUB_TEMPLATES = GITHUB_TEMPLATES
