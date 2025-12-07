"""
Database connection and utilities
"""
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable, Awaitable
from contextlib import asynccontextmanager

import psycopg
from psycopg_pool import AsyncConnectionPool

from app.config import get_settings
from app.logger import logger


class DatabaseManager:
    """Gestiona las conexiones a la base de datos con reintentos"""
    
    def __init__(self, database_url: str, auto_setup: bool = False):
        self.database_url = database_url
        self.auto_setup = auto_setup
        self.pool: Optional[AsyncConnectionPool] = None
        self.schema_initialized: bool = False
        self._pool_lock = asyncio.Lock()
        self._pool_kwargs = {
            "conninfo": self.database_url,
            "min_size": 2,
            "max_size": 10,
            "timeout": 30.0
        }
        self._max_retries = 2
        self._retry_delay = 2
    
    async def initialize(self):
        """Inicializa (o reinicializa) el pool de conexiones"""
        try:
            await self._ensure_pool(force=True)
            logger.info("✅ Pool de conexiones de BD inicializado")
            await self.ensure_schema()
        except Exception as e:
            logger.error(f"❌ Error al conectar a la BD: {e}")
            raise
    
    async def _ensure_pool(self, force: bool = False):
        """Garantiza que exista un pool abierto"""
        async with self._pool_lock:
            if self.pool and not force and not self.pool.closed:
                return
            if self.pool and (force or self.pool.closed):
                try:
                    await self.pool.close()
                except Exception:
                    pass
            self.pool = AsyncConnectionPool(**self._pool_kwargs)
            await self.pool.open()
    
    async def _reset_pool(self, reason: str):
        logger.warning(f"♻️  Reiniciando pool de BD por: {reason}")
        await self._ensure_pool(force=True)
    
    async def _execute_with_retry(self, operation: Callable[[], Awaitable[Any]]):
        """Ejecuta una operación con reintentos ante errores de conexión"""
        last_error: Optional[Exception] = None
        for attempt in range(1, self._max_retries + 2):  # retries + intento inicial
            try:
                return await operation()
            except (psycopg.OperationalError, psycopg.InterfaceError) as exc:
                last_error = exc
                logger.error(
                    f"⚠️  Error de conexión a BD (intento {attempt}): {exc}"
                )
                if attempt > self._max_retries:
                    break
                await self._reset_pool(str(exc))
                await asyncio.sleep(min(self._retry_delay * attempt, 5))
            except Exception as exc:
                last_error = exc
                break
        if last_error:
            raise last_error
        raise RuntimeError("Database operation failed without exception")

    async def ensure_schema(self):
        """Garantiza que las tablas requeridas existan"""
        if self.schema_initialized:
            return
        if not self.auto_setup:
            logger.info("ℹ️ Auto-setup de base de datos deshabilitado (DATABASE_AUTO_SETUP=false)")
            self.schema_initialized = True
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
        await self._ensure_pool()
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
        async def _operation():
            async with self.get_connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(query, params)
                    columns = [desc[0] for desc in cur.description] if cur.description else []
                    rows = await cur.fetchall()
                    return [dict(zip(columns, row)) for row in rows]
        
        return await self._execute_with_retry(_operation)
    
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
    
    async def execute_non_query(
        self,
        query: str,
        params: Optional[tuple] = None
    ) -> int:
        """
        Ejecuta una sentencia INSERT/UPDATE/DELETE y confirma la transacción.
        Retorna la cantidad de filas afectadas.
        """
        async def _operation():
            async with self.get_connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(query, params)
                    await conn.commit()
                    return cur.rowcount
        
        return await self._execute_with_retry(_operation)


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """Get or create database manager instance"""
    global _db_manager
    if _db_manager is None:
        settings = get_settings()
        _db_manager = DatabaseManager(
            database_url=settings.database_url,
            auto_setup=settings.database_auto_setup
        )
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

