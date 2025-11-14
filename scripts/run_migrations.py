"""
Script para ejecutar migraciones SQL automáticamente
Se ejecuta al iniciar la app en Railway
"""
import os
import sys
from pathlib import Path

# Añadir el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
from app.logger import logger
import psycopg


def run_migration(cursor, migration_file: Path):
    """Ejecuta un archivo de migración SQL"""
    try:
        logger.info(f"📝 Ejecutando migración: {migration_file.name}")
        
        with open(migration_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Ejecutar el SQL
        cursor.execute(sql_content)
        
        logger.info(f"✅ Migración completada: {migration_file.name}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en migración {migration_file.name}: {e}")
        return False


def run_all_migrations():
    """Ejecuta todas las migraciones pendientes"""
    settings = get_settings()
    
    # Conectar a la base de datos
    try:
        conn = psycopg.connect(
            conninfo=settings.database_url,
            autocommit=False
        )
        cursor = conn.cursor()
        
        logger.info("🔄 Iniciando migraciones...")
        
        # Lista de migraciones a ejecutar (en orden)
        migrations_dir = Path(__file__).parent
        migrations = [
            migrations_dir / "fix_trigger_cast.sql",
        ]
        
        success_count = 0
        
        for migration_file in migrations:
            if not migration_file.exists():
                logger.warning(f"⚠️  Archivo de migración no encontrado: {migration_file.name}")
                continue
            
            if run_migration(cursor, migration_file):
                success_count += 1
                conn.commit()
            else:
                conn.rollback()
                logger.error(f"❌ Falló la migración: {migration_file.name}")
                # Continuar con las siguientes migraciones
        
        logger.info(f"✅ Migraciones completadas: {success_count}/{len(migrations)}")
        
        cursor.close()
        conn.close()
        
        return success_count == len(migrations)
        
    except Exception as e:
        logger.error(f"❌ Error conectando a la base de datos: {e}")
        return False


if __name__ == "__main__":
    success = run_all_migrations()
    sys.exit(0 if success else 1)

