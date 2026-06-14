"""
Configuration Manager - Read and write app configuration
Manages settings from config.ini file
"""
import configparser
import os
from pathlib import Path
from typing import Any, Optional


class ConfigManager:
    """Manages application configuration from config.ini."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize the config manager and load or create the config file."""
        if config_path is None:
            # Default: config.ini in app root directory
            app_dir = Path(__file__).parent.parent
            config_path = app_dir / "config.ini"

        self.config_path = str(config_path)
        self.config = configparser.ConfigParser()
        self._load()

    def _load(self):
        """Load configuration from file, creating defaults if the file does not exist."""
        if os.path.exists(self.config_path):
            self.config.read(self.config_path)
        else:
            self._create_default()

    def _create_default(self):
        """Write a default config.ini with sensible fallback values."""
        self.config['Backend'] = {
            'url': 'http://localhost:8000',
            'timeout': '10',
            'retry_attempts': '3',
            'retry_backoff': '2.0'
        }

        self.config['Sync'] = {
            'enabled': 'true',
            'interval': '30',
            'batch_size': '50',
            'max_queue_size': '1000'
        }

        self.config['App'] = {
            'auto_sync': 'true',
            'show_notifications': 'true',
            'log_level': 'INFO'
        }

        self.save()

    def save(self):
        """Persist the current in-memory configuration to disk."""
        with open(self.config_path, 'w') as f:
            self.config.write(f)

    def get(self, section: str, key: str, fallback: Any = None) -> Any:
        """Return a string value from the config, or fallback if the key is missing."""
        try:
            return self.config.get(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return fallback

    def get_int(self, section: str, key: str, fallback: int = 0) -> int:
        """Return an integer value from the config, or fallback on missing or invalid key."""
        try:
            return self.config.getint(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback

    def get_float(self, section: str, key: str, fallback: float = 0.0) -> float:
        """Return a float value from the config, or fallback on missing or invalid key."""
        try:
            return self.config.getfloat(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback

    def get_bool(self, section: str, key: str, fallback: bool = False) -> bool:
        """Return a boolean value from the config, or fallback on missing or invalid key."""
        try:
            return self.config.getboolean(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback

    def set(self, section: str, key: str, value: Any):
        """Set a config value, creating the section if it does not exist."""
        if not self.config.has_section(section):
            self.config.add_section(section)

        self.config.set(section, key, str(value))

    # Convenience methods for common settings

    def get_backend_url(self) -> str:
        """Return the configured backend base URL."""
        return self.get('Backend', 'url', 'http://localhost:8000')

    def get_backend_timeout(self) -> int:
        """Return the configured backend request timeout in seconds."""
        return self.get_int('Backend', 'timeout', 10)

    def get_sync_interval(self) -> int:
        """Return the sync interval in seconds."""
        return self.get_int('Sync', 'interval', 30)

    def get_sync_batch_size(self) -> int:
        """Return the maximum number of records per sync batch."""
        return self.get_int('Sync', 'batch_size', 50)

    def is_sync_enabled(self) -> bool:
        """Return True if background sync to the backend is enabled."""
        return self.get_bool('Sync', 'enabled', True)

    def is_auto_sync(self) -> bool:
        """Return True if sync should start automatically on app launch."""
        return self.get_bool('App', 'auto_sync', True)

    def get_log_level(self) -> str:
        """Return the configured logging level string (e.g. 'INFO')."""
        return self.get('App', 'log_level', 'INFO')


# Global config instance
_config_instance: Optional[ConfigManager] = None


def get_config() -> ConfigManager:
    """Return the singleton ConfigManager instance, creating it on first call."""
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigManager()
    return _config_instance


# Example usage
if __name__ == "__main__":
    config = ConfigManager()

    print(f"Backend URL: {config.get_backend_url()}")
    print(f"Sync interval: {config.get_sync_interval()}s")
    print(f"Sync enabled: {config.is_sync_enabled()}")
    print(f"Log level: {config.get_log_level()}")
