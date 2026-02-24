import asyncpg
import os
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Create database connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                host=os.getenv('DB_HOST', 'localhost'),
                port=int(os.getenv('DB_PORT', 5432)),
                database=os.getenv('DB_NAME', 'each_way_tracker'),
                user=os.getenv('DB_USER', 'betting_user'),
                password=os.getenv('DB_PASSWORD', ''),
                min_size=2,
                max_size=10,
                command_timeout=60
            )
            logger.info("Database connection pool created successfully")
        except Exception as e:
            logger.error(f"Failed to create database pool: {e}")
            raise

    async def disconnect(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")

    async def fetch_one(self, query: str, *args):
        """Execute query and return one row"""
        async with self.pool.acquire() as connection:
            return await connection.fetchrow(query, *args)

    async def fetch_all(self, query: str, *args):
        """Execute query and return all rows"""
        async with self.pool.acquire() as connection:
            return await connection.fetch(query, *args)

    async def execute(self, query: str, *args):
        """Execute query without returning results"""
        async with self.pool.acquire() as connection:
            return await connection.execute(query, *args)

    async def execute_many(self, query: str, args_list):
        """Execute query multiple times with different arguments"""
        async with self.pool.acquire() as connection:
            return await connection.executemany(query, args_list)

# Global database instance
db = Database()
