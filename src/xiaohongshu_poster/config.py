"""
Configuration management for Xiaohongshu Poster
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv


class Config:
    """Configuration manager for the Xiaohongshu bot."""

    DEFAULT_CONFIG = {
        "adb": {
            "connection_type": "usb",
            "device_ip": "192.168.1.100",
            "device_port": 5555,
            "adb_host": "127.0.0.1",
            "adb_port": 5037,
        },
        "xiaohongshu": {
            "package_name": "com.xingin.xhs",
            "main_activity": "com.xingin.xhs.index.v2.IndexActivityV2",
        },
        "timing": {
            "app_launch_wait": 3,
            "action_wait": 1.5,
            "upload_wait": 10,
            "post_complete_wait": 5,
        },
        "coordinates": {
            "screen_width": 1080,
            "screen_height": 2400,
            "post_button": {"x": 540, "y": 2280},
            "image_option": {"x": 270, "y": 1800},
            "video_option": {"x": 810, "y": 1800},
            "next_button": {"x": 980, "y": 150},
            "title_input": {"x": 540, "y": 400},
            "content_input": {"x": 540, "y": 700},
            "publish_button": {"x": 980, "y": 150},
        },
        "post": {
            "default_hashtags": [],
            "add_location": False,
        },
    }

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration.

        Args:
            config_path: Path to YAML config file. If None, uses default config.
        """
        load_dotenv()
        self._config = self.DEFAULT_CONFIG.copy()

        if config_path:
            self._load_from_file(config_path)

        self._apply_env_overrides()

    def _load_from_file(self, config_path: str) -> None:
        """Load configuration from YAML file."""
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(path, "r", encoding="utf-8") as f:
            file_config = yaml.safe_load(f) or {}

        self._deep_merge(self._config, file_config)

    def _deep_merge(self, base: Dict, override: Dict) -> None:
        """Deep merge override dict into base dict."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides."""
        env_mappings = {
            "XHS_ADB_HOST": ("adb", "adb_host"),
            "XHS_ADB_PORT": ("adb", "adb_port"),
            "XHS_DEVICE_IP": ("adb", "device_ip"),
            "XHS_DEVICE_PORT": ("adb", "device_port"),
            "XHS_CONNECTION_TYPE": ("adb", "connection_type"),
        }

        for env_var, path in env_mappings.items():
            value = os.getenv(env_var)
            if value:
                section, key = path
                if key.endswith("_port"):
                    value = int(value)
                self._config[section][key] = value

    def get(self, *keys: str, default: Any = None) -> Any:
        """
        Get a configuration value by nested keys.

        Args:
            *keys: Nested keys to traverse
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        value = self._config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    @property
    def adb(self) -> Dict[str, Any]:
        """Get ADB configuration section."""
        return self._config["adb"]

    @property
    def xiaohongshu(self) -> Dict[str, Any]:
        """Get Xiaohongshu app configuration section."""
        return self._config["xiaohongshu"]

    @property
    def timing(self) -> Dict[str, Any]:
        """Get timing configuration section."""
        return self._config["timing"]

    @property
    def coordinates(self) -> Dict[str, Any]:
        """Get screen coordinates configuration section."""
        return self._config["coordinates"]

    @property
    def post(self) -> Dict[str, Any]:
        """Get post settings configuration section."""
        return self._config["post"]

    def scale_coordinates(self, actual_width: int, actual_height: int) -> Dict[str, Any]:
        """
        Scale coordinates from config resolution to actual device resolution.

        Args:
            actual_width: Actual device screen width
            actual_height: Actual device screen height

        Returns:
            Scaled coordinates dictionary
        """
        config_width = self.coordinates["screen_width"]
        config_height = self.coordinates["screen_height"]

        scale_x = actual_width / config_width
        scale_y = actual_height / config_height

        scaled = {}
        for key, value in self.coordinates.items():
            if isinstance(value, dict) and "x" in value and "y" in value:
                scaled[key] = {
                    "x": int(value["x"] * scale_x),
                    "y": int(value["y"] * scale_y),
                }
            else:
                scaled[key] = value

        scaled["screen_width"] = actual_width
        scaled["screen_height"] = actual_height

        return scaled
