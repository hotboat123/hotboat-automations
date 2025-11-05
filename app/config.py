"""
Configuration management
"""
from copy import deepcopy
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
import yaml


DEFAULT_CONFIG = {
    "monitors": {
        "appointments": {
            "enabled": True,
            "name": "Monitor de Reservas",
            "check_interval": 60,
            "notifications": {
                "new_appointment": True,
                "cancelled_appointment": True,
                "modified_appointment": True,
                "upcoming_reminder": True,
                "reminder_hours_before": 24,
            },
        },
        "stock": {
            "enabled": True,
            "name": "Monitor de Stock",
            "check_interval": 300,
            "thresholds": {
                "low_stock": 5,
                "critical_stock": 2,
                "out_of_stock": 0,
            },
            "notifications": {
                "low_stock": True,
                "critical_stock": True,
                "out_of_stock": True,
                "stock_restored": True,
            },
        },
    },
    "notifications": {
        "telegram": {
            "enabled": False,
            "priority_levels": {
                "critical": True,
                "high": True,
                "medium": True,
                "low": False,
            },
        },
        "email": {
            "enabled": True,
            "send_summary": True,
            "summary_interval": "daily",
            "summary_time": "08:00",
            "priority_levels": {
                "critical": True,
                "high": True,
                "medium": False,
                "low": False,
            },
        },
        "whatsapp": {
            "enabled": True,
            "priority_levels": {
                "critical": True,
                "high": True,
                "medium": True,
                "low": False,
            },
        },
    },
    "database": {
        "pool_size": 5,
        "max_overflow": 10,
        "pool_timeout": 30,
        "echo": False,
    },
    "logging": {
        "level": "INFO",
        "format": "colored",
        "rotation": "daily",
        "retention_days": 30,
        "max_file_size": "10MB",
    },
    "general": {
        "timezone": "America/Santiago",
        "startup_notification": True,
        "error_notification": True,
        "health_check_interval": 3600,
    },
}


class Settings(BaseSettings):
    """Application settings from environment variables"""
    
    # Database
    database_url: str
    
    # Telegram
    telegram_bot_token: Optional[str] = None
    telegram_chat_ids: str = ""  # Comma-separated
    
    # Email (SMTP)
    email_enabled: bool = False
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    email_from: Optional[str] = None
    email_to: str = ""  # Comma-separated
    
    # SendGrid
    sendgrid_api_key: Optional[str] = None
    sendgrid_from_email: Optional[str] = None
    
    # WhatsApp
    whatsapp_enabled: bool = False
    whatsapp_api_token: Optional[str] = None
    whatsapp_phone_number_id: Optional[str] = None
    whatsapp_business_account_id: Optional[str] = None
    whatsapp_verify_token: Optional[str] = None
    whatsapp_recipients: str = ""  # Comma-separated
    
    # Monitor Configuration
    check_interval_appointments: int = 60
    check_interval_stock: int = 300
    low_stock_threshold: int = 5
    critical_stock_threshold: int = 2
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/automation.log"
    
    # Environment
    environment: str = "development"
    port: int = 8080  # Puerto para Railway
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    @property
    def telegram_chat_ids_list(self) -> List[int]:
        """Parse Telegram chat IDs from comma-separated string"""
        if not self.telegram_chat_ids:
            return []
        return [int(id.strip()) for id in self.telegram_chat_ids.split(",") if id.strip()]
    
    @property
    def email_to_list(self) -> List[str]:
        """Parse email recipients from comma-separated string"""
        if not self.email_to:
            return []
        return [email.strip() for email in self.email_to.split(",") if email.strip()]
    
    @property
    def whatsapp_recipients_list(self) -> List[str]:
        """Parse WhatsApp recipients from comma-separated string"""
        if not self.whatsapp_recipients:
            return []
        return [phone.strip() for phone in self.whatsapp_recipients.split(",") if phone.strip()]


def get_settings() -> Settings:
    """Get settings instance"""
    return Settings()


def load_yaml_config(config_file: str = "config.yaml") -> dict:
    """Load YAML configuration file"""
    config = deepcopy(DEFAULT_CONFIG)
    config_path = Path(config_file)
    
    if not config_path.exists():
        return config
    
    with open(config_path, "r", encoding="utf-8") as f:
        file_config = yaml.safe_load(f) or {}
        if isinstance(file_config, dict):
            config = _deep_merge(config, file_config)
    
    return config


def _deep_merge(base: dict, overrides: dict) -> dict:
    """Deep merge dictionaries without mutating inputs"""
    result = deepcopy(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result.get(key, {}), value)
        else:
            result[key] = value
    return result

