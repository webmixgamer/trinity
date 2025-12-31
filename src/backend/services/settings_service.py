"""
Settings service for retrieving configuration values.

Provides centralized access to:
- Database-stored settings
- Environment variable fallbacks
- Typed conversions

This service breaks the circular dependency where services were importing
from routers.settings. Now all settings retrieval logic lives here, and
routers.settings re-exports these functions for backward compatibility.
"""
import os
from typing import Optional
from database import db


# ============================================================================
# Ops Settings Configuration - moved from routers/settings.py
# ============================================================================

# Default values for ops settings (as specified in requirements)
OPS_SETTINGS_DEFAULTS = {
    "ops_context_warning_threshold": "75",  # Context % to trigger warning
    "ops_context_critical_threshold": "90",  # Context % to trigger reset/action
    "ops_idle_timeout_minutes": "30",  # Minutes before stuck detection
    "ops_cost_limit_daily_usd": "50.0",  # Daily cost limit (0 = unlimited)
    "ops_max_execution_minutes": "10",  # Max chat execution time
    "ops_alert_suppression_minutes": "15",  # Suppress duplicate alerts
    "ops_log_retention_days": "7",  # Days to keep container logs
    "ops_health_check_interval": "60",  # Seconds between health checks
}

# Descriptions for each ops setting
OPS_SETTINGS_DESCRIPTIONS = {
    "ops_context_warning_threshold": "Context usage percentage to trigger a warning (default: 75)",
    "ops_context_critical_threshold": "Context usage percentage to trigger critical alert or action (default: 90)",
    "ops_idle_timeout_minutes": "Minutes of inactivity before an agent is considered stuck (default: 30)",
    "ops_cost_limit_daily_usd": "Maximum daily cost limit in USD per agent (0 = unlimited) (default: 50.0)",
    "ops_max_execution_minutes": "Maximum allowed execution time for a single chat in minutes (default: 10)",
    "ops_alert_suppression_minutes": "Minutes to suppress duplicate alerts for same agent+type (default: 15)",
    "ops_log_retention_days": "Number of days to retain container logs (default: 7)",
    "ops_health_check_interval": "Seconds between automated health checks (default: 60)",
}


class SettingsService:
    """
    Centralized service for retrieving settings.

    Hierarchy:
    1. Database setting (if exists)
    2. Environment variable (fallback)
    3. Default value (if provided)
    """

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a setting from database with optional default."""
        value = db.get_setting_value(key, None)
        return value if value is not None else default

    def get_anthropic_api_key(self) -> str:
        """Get Anthropic API key from settings, fallback to env var."""
        key = self.get_setting('anthropic_api_key')
        if key:
            return key
        return os.getenv('ANTHROPIC_API_KEY', '')

    def get_github_pat(self) -> str:
        """Get GitHub PAT from settings, fallback to env var."""
        key = self.get_setting('github_pat')
        if key:
            return key
        return os.getenv('GITHUB_PAT', '')

    def get_google_api_key(self) -> str:
        """Get Google API key from settings, fallback to env var."""
        key = self.get_setting('google_api_key')
        if key:
            return key
        return os.getenv('GOOGLE_API_KEY', '')

    def get_ops_setting(self, key: str, as_type: type = str):
        """
        Get an ops setting with type conversion.

        Uses defaults from OPS_SETTINGS_DEFAULTS if not set.
        """
        default = OPS_SETTINGS_DEFAULTS.get(key, "")
        value = self.get_setting(key, default)

        if as_type == int:
            return int(value)
        elif as_type == float:
            return float(value)
        elif as_type == bool:
            return str(value).lower() in ("true", "1", "yes")
        return value


# Singleton instance
settings_service = SettingsService()


# Convenience functions for backward compatibility
def get_anthropic_api_key() -> str:
    """Get Anthropic API key from settings, fallback to env var."""
    return settings_service.get_anthropic_api_key()


def get_github_pat() -> str:
    """Get GitHub PAT from settings, fallback to env var."""
    return settings_service.get_github_pat()


def get_google_api_key() -> str:
    """Get Google API key from settings, fallback to env var."""
    return settings_service.get_google_api_key()


def get_ops_setting(key: str, as_type: type = str):
    """Get an ops setting with type conversion."""
    return settings_service.get_ops_setting(key, as_type)
