"""
Database connection and utilities
"""
from pathlib import Path
import psycopg
from psycopg_pool import AsyncConnectionPool
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from app.config import get_settings
from app.logger import logger


class DatabaseManager:
    """Gestiona las conexiones a la base de datos"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool: Optional[AsyncConnectionPool] = None
        self.schema_initialized: bool = False
    
    async def initialize(self):
        """Inicializa el pool de conexiones"""
        try:
            self.pool = AsyncConnectionPool(
                conninfo=self.database_url,
                min_size=2,
                max_size=10,
                timeout=30.0
            )
            logger.info("✅ Pool de conexiones de BD inicializado")
            await self.ensure_schema()
        except Exception as e:
            logger.error(f"❌ Error al conectar a la BD: {e}")
            raise

    async def ensure_schema(self):
        """Garantiza que las tablas requeridas existan"""
        if self.schema_initialized:
            return
        script_path = Path("setup_database.sql")
        if not script_path.exists():
            logger.warning("⚠️ Script setup_database.sql no encontrado, omitiendo creación de esquema")
            self.schema_initialized = True
            return
        try:
            sql_script = script_path.read_text(encoding="utf-8")
            async with self.get_connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(sql_script)
                await conn.commit()
            logger.info("🛠️ Esquema de base de datos verificado")
            self.schema_initialized = True
        except Exception as e:
            logger.error(f"❌ Error al asegurar el esquema de BD: {e}")
            raise
    
    async def close(self):
        """Cierra el pool de conexiones"""
        if self.pool:
            await self.pool.close()
            logger.info("🔌 Pool de conexiones cerrado")
    
    @asynccontextmanager
    async def get_connection(self):
        """Context manager para obtener una conexión"""
        async with self.pool.connection() as conn:
            yield conn
    
    async def execute_query(
        self,
        query: str,
        params: Optional[tuple] = None
    ) -> List[Dict[str, Any]]:
        """
        Ejecuta una query SELECT y devuelve los resultados
        """
        async with self.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params)
                
                # Get column names
                columns = [desc[0] for desc in cur.description] if cur.description else []
                
                # Fetch all results
                rows = await cur.fetchall()
                
                # Convert to list of dicts
                return [dict(zip(columns, row)) for row in rows]
    
    async def execute_single(
        self,
        query: str,
        params: Optional[tuple] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Ejecuta una query y devuelve un único resultado
        """
        results = await self.execute_query(query, params)
        return results[0] if results else None


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """Get or create database manager instance"""
    global _db_manager
    if _db_manager is None:
        settings = get_settings()
        _db_manager = DatabaseManager(settings.database_url)
    return _db_manager


async def init_database():
    """Initialize database connection"""
    db = get_db_manager()
    await db.initialize()
    return db


async def close_database():
    """Close database connection"""
    global _db_manager
    if _db_manager:
        await _db_manager.close()
        _db_manager = None

