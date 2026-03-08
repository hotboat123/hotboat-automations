"""
Script para verificar configuración de email
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings, load_yaml_config

settings = get_settings()
config = load_yaml_config()

print("="*80)
print("CONFIGURACIÓN DE EMAIL")
print("="*80)

# Email settings
email_config = config.get("email", {})
print(f"\nEmail destino: {email_config.get('to', 'NO CONFIGURADO')}")
print(f"Email remitente: {email_config.get('from', 'NO CONFIGURADO')}")
print(f"SMTP Host: {email_config.get('smtp', {}).get('host', 'NO CONFIGURADO')}")
print(f"SMTP Port: {email_config.get('smtp', {}).get('port', 'NO CONFIGURADO')}")
print(f"SMTP User: {email_config.get('smtp', {}).get('username', 'NO CONFIGURADO')}")
print(f"SMTP Password: {'***' if email_config.get('smtp', {}).get('password') else 'NO CONFIGURADO'}")

print("\n" + "="*80)
print("NOTIFICACIONES HABILITADAS")
print("="*80)

notifications = config.get("notifications", {})
for channel, channel_config in notifications.items():
    enabled = channel_config.get("enabled", False)
    print(f"{channel}: {'✓ HABILITADO' if enabled else '✗ DESHABILITADO'}")
