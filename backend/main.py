from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os
from dotenv import load_dotenv

# Import database connections
from db.database import db
from db.redis_client import redis_client

# Import routes
from api.routes import events, odds, status

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("Starting Betting Monitor API...")
    try:
        await db.connect()
        await redis_client.connect()
        logger.info("All connections established successfully")
    except Exception as e:
        logger.error(f"Failed to establish connections: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Betting Monitor API...")
    await db.disconnect()
    await redis_client.disconnect()
    logger.info("All connections closed")

# Create FastAPI app
app = FastAPI(
    title="Betting Monitor API",
    description="Real-time odds monitoring API for UK bookmakers",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
origins = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(events.router)
app.include_router(odds.router)
app.include_router(status.router)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Betting Monitor API",
        "version": "1.0.0",
        "status": "running"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.getenv('API_HOST', '0.0.0.0'),
        port=int(os.getenv('API_PORT', 8000)),
        reload=True
    )
