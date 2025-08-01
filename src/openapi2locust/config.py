"""Configuration management for openapi2locust."""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union, Tuple
import yaml


class ConfigError(Exception):
    """Base exception for configuration errors."""
    pass


class ConfigurationManager:
    """Manage configuration settings for openapi2locust."""
    
    DEFAULT_CONFIG = {
        "output_dir": ".",
        "min_wait": 1,
        "max_wait": 3,
        "default_weight": {
            "GET": 10,
            "POST": 3,
            "PUT": 2,
            "PATCH": 2,
            "DELETE": 1,
            "HEAD": 1,
            "OPTIONS": 1
        },
        "include_security_headers": True,
        "security_headers": {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Cache-Control": "no-cache, no-store, must-revalidate"
        },
        "data_faker": {
            "locale": "en_US"
        },
        "template": {
            "add_response_validation": True,
            "include_test_data_helpers": True
        }
    }
    
    def __init__(self, config_path: Optional[Union[str, Path]] = None) -> None:
        self.logger = logging.getLogger(__name__)
        self.config: Dict[str, Any] = self.DEFAULT_CONFIG.copy()
        
        if config_path:
            self.load_config(config_path)
    
    def load_config(self, config_path: Union[str, Path]) -> None:
        """Load configuration from file."""
        config_path = Path(config_path)
        
        if not config_path.exists():
            raise ConfigError(f"Configuration file not found: {config_path}")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                if config_path.suffix.lower() in ['.yaml', '.yml']:
                    user_config = yaml.safe_load(f)
                elif config_path.suffix.lower() == '.json':
                    user_config = json.load(f)
                else:
                    raise ConfigError(f"Unsupported configuration file format: {config_path.suffix}")
            
            if not isinstance(user_config, dict):
                raise ConfigError("Configuration must be a dictionary/object")
            
            # Merge user config with defaults
            self._merge_config(user_config)
            self.logger.info(f"Loaded configuration from {config_path}")
            
        except (yaml.YAMLError, json.JSONDecodeError) as e:
            raise ConfigError(f"Invalid configuration file format: {e}") from e
        except Exception as e:
            raise ConfigError(f"Failed to load configuration: {e}") from e
    
    def _merge_config(self, user_config: Dict[str, Any]) -> None:
        """Merge user configuration with defaults."""
        def merge_dicts(default: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
            result = default.copy()
            for key, value in user.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = merge_dicts(result[key], value)
                else:
                    result[key] = value
            return result
        
        self.config = merge_dicts(self.config, user_config)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key (supports dot notation)."""
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value by key (supports dot notation)."""
        keys = key.split('.')
        config = self.config
        
        # Navigate to the parent dictionary
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # Set the final value
        config[keys[-1]] = value
    
    def get_output_dir(self) -> str:
        """Get output directory setting."""
        return self.get('output_dir', '.')
    
    def get_wait_time(self) -> Tuple[int, int]:
        """Get wait time settings as (min_wait, max_wait)."""
        return (self.get('min_wait', 1), self.get('max_wait', 3))
    
    def get_task_weight(self, method: str) -> int:
        """Get task weight for HTTP method."""
        weights = self.get('default_weight', {})
        return weights.get(method.upper(), 5)
    
    def should_include_security_headers(self) -> bool:
        """Check if security headers should be included."""
        return self.get('include_security_headers', True)
    
    def get_security_headers(self) -> Dict[str, str]:
        """Get security headers configuration."""
        return self.get('security_headers', {})
    
    def get_data_faker_locale(self) -> str:
        """Get data faker locale setting."""
        return self.get('data_faker.locale', 'en_US')
    
    def should_add_response_validation(self) -> bool:
        """Check if response validation should be added."""
        return self.get('template.add_response_validation', True)
    
    def should_include_test_data_helpers(self) -> bool:
        """Check if test data helpers should be included."""
        return self.get('template.include_test_data_helpers', True)
    
    def save_config(self, config_path: Union[str, Path]) -> None:
        """Save current configuration to file."""
        config_path = Path(config_path)
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                if config_path.suffix.lower() in ['.yaml', '.yml']:
                    yaml.dump(self.config, f, default_flow_style=False, indent=2)
                elif config_path.suffix.lower() == '.json':
                    json.dump(self.config, f, indent=2)
                else:
                    raise ConfigError(f"Unsupported configuration file format: {config_path.suffix}")
            
            self.logger.info(f"Configuration saved to {config_path}")
            
        except Exception as e:
            raise ConfigError(f"Failed to save configuration: {e}") from e
    
    def validate_config(self) -> None:
        """Validate current configuration."""
        errors = []
        
        # Validate wait times
        min_wait = self.get('min_wait')
        max_wait = self.get('max_wait')
        if not isinstance(min_wait, int) or min_wait < 0:
            errors.append("min_wait must be a non-negative integer")
        if not isinstance(max_wait, int) or max_wait < 0:
            errors.append("max_wait must be a non-negative integer")
        if isinstance(min_wait, int) and isinstance(max_wait, int) and min_wait > max_wait:
            errors.append("min_wait cannot be greater than max_wait")
        
        # Validate output directory
        output_dir = self.get('output_dir')
        if not isinstance(output_dir, str):
            errors.append("output_dir must be a string")
        
        # Validate weights
        weights = self.get('default_weight', {})
        if not isinstance(weights, dict):
            errors.append("default_weight must be a dictionary")
        else:
            for method, weight in weights.items():
                if not isinstance(weight, int) or weight < 0:
                    errors.append(f"Weight for {method} must be a non-negative integer")
        
        if errors:
            raise ConfigError("Configuration validation failed: " + "; ".join(errors))
    
    def get_sample_config(self) -> str:
        """Get a sample configuration file content."""
        sample_config = """# openapi2locust configuration file
# This file can be in YAML or JSON format

# Output directory for generated files
output_dir: "./output"

# Wait time between requests (in seconds)
min_wait: 1
max_wait: 5

# Task weights for different HTTP methods
default_weight:
  GET: 10
  POST: 3
  PUT: 2
  PATCH: 2
  DELETE: 1
  HEAD: 1
  OPTIONS: 1

# Security headers to include in requests
include_security_headers: true
security_headers:
  X-Content-Type-Options: "nosniff"
  X-Frame-Options: "DENY"
  X-XSS-Protection: "1; mode=block"
  Referrer-Policy: "strict-origin-when-cross-origin"
  Cache-Control: "no-cache, no-store, must-revalidate"

# Data faker settings
data_faker:
  locale: "en_US"

# Template generation settings
template:
  add_response_validation: true
  include_test_data_helpers: true
"""
        return sample_config.strip()


# Default configuration manager instance
default_config = ConfigurationManager()