"""
Utility helper functions for the Trinity backend.
"""
import re
from typing import List, Tuple


def parse_env_content(content: str) -> List[Tuple[str, str]]:
    """
    Parse .env-style content into list of (key, value) tuples.

    Handles:
    - KEY=VALUE
    - KEY="VALUE WITH SPACES"
    - KEY='VALUE WITH SPACES'
    - # comments
    - Empty lines
    """
    results = []

    for line in content.split('\n'):
        line = line.strip()

        if not line or line.startswith('#'):
            continue

        if '=' not in line:
            continue

        key, _, value = line.partition('=')
        key = key.strip()
        value = value.strip()

        # Remove surrounding quotes if present
        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]

        # Validate key format (must be uppercase with underscores)
        if not key or not re.match(r'^[A-Z][A-Z0-9_]*$', key):
            continue

        if key and value:
            results.append((key, value))

    return results


def infer_service_from_key(key: str) -> str:
    """
    Infer service name from environment variable name.

    Examples:
    - HEYGEN_API_KEY -> heygen
    - TWITTER_API_SECRET -> twitter
    - OPENAI_API_KEY -> openai
    - CLOUDINARY_CLOUD_NAME -> cloudinary
    """
    service_patterns = [
        ('HEYGEN_', 'heygen'),
        ('TWITTER_', 'twitter'),
        ('OPENAI_', 'openai'),
        ('ANTHROPIC_', 'anthropic'),
        ('CLOUDINARY_', 'cloudinary'),
        ('GEMINI_', 'gemini'),
        ('GOOGLE_', 'google'),
        ('GITHUB_', 'github'),
        ('SLACK_', 'slack'),
        ('NOTION_', 'notion'),
        ('GIPHY_', 'giphy'),
        ('METRICOOL_', 'metricool'),
        ('BLOTATO_', 'blotato'),
        ('GOFILE_', 'gofile'),
        ('KLAP_', 'klap'),
        ('AWS_', 'aws'),
        ('AZURE_', 'azure'),
        ('STRIPE_', 'stripe'),
        ('SENDGRID_', 'sendgrid'),
        ('TWILIO_', 'twilio'),
        ('DISCORD_', 'discord'),
        ('LINKEDIN_', 'linkedin'),
        ('INSTAGRAM_', 'instagram'),
        ('TIKTOK_', 'tiktok'),
        ('YOUTUBE_', 'youtube'),
    ]

    key_upper = key.upper()
    for prefix, service in service_patterns:
        if key_upper.startswith(prefix):
            return service

    parts = key.split('_')
    if len(parts) > 1:
        return parts[0].lower()

    return 'custom'


def infer_type_from_key(key: str) -> str:
    """Infer credential type from environment variable name."""
    key_upper = key.upper()

    if '_API_KEY' in key_upper or key_upper.endswith('_KEY'):
        return 'api_key'
    elif '_TOKEN' in key_upper:
        return 'token'
    elif '_SECRET' in key_upper:
        return 'api_key'
    elif '_PASSWORD' in key_upper:
        return 'basic_auth'
    else:
        return 'api_key'


def sanitize_agent_name(name: str) -> str:
    """
    Sanitize agent name for Docker container naming rules.

    Docker container names must match: [a-zA-Z0-9][a-zA-Z0-9_.-]
    """
    # Replace spaces and invalid chars with hyphens
    sanitized = re.sub(r'[^a-zA-Z0-9_.-]', '-', name)
    # Remove leading non-alphanumeric chars
    sanitized = re.sub(r'^[^a-zA-Z0-9]+', '', sanitized)
    # Collapse multiple hyphens
    sanitized = re.sub(r'-+', '-', sanitized)
    # Remove trailing hyphens
    sanitized = sanitized.rstrip('-')
    return sanitized.lower()
