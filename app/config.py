"""
Configuration management
"""
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
import yaml


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
    config_path = Path(config_file)
    
    if not config_path.exists():
        return {}
    
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

