# Setup Guide

## Prerequisites

- Docker and Docker Compose installed
- Node.js 18+ (for local development)
- Python 3.11+ (for local development)

## Quick Start

### 1. Create Environment File

Copy the example environment file and fill in your credentials:

```bash
cd /Users/bsslbj/Desktop/FirstUse/betting-monitor
cp .env.example .env
```

Edit `.env` and update:
```bash
# Required: Your ProfitMaximiser credentials
PROFIT_MAXIMISER_EMAIL=your_email@example.com
PROFIT_MAXIMISER_PASSWORD=your_password

# Optional: Change database password (recommended)
DB_PASSWORD=your_secure_password_here
```

### 2. Start Services with Docker

```bash
docker-compose up -d
```

This will start:
- PostgreSQL database with TimescaleDB (port 5432)
- Redis cache (port 6379)
- Backend API (port 8000)
- Scraper service (runs in background)
- Frontend dev server (port 3000)

### 3. View Logs

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f scraper
docker-compose logs -f frontend
```

### 4. Access Application

- **Frontend**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs
- **API Health Check**: http://localhost:8000/status/health

## Local Development (Without Docker)

### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start PostgreSQL and Redis (via Docker)
docker-compose up -d postgres redis

# Run database migrations (if using Alembic)
# alembic upgrade head

# Start API server
uvicorn main:app --reload --port 8000

# In another terminal, start scraper
python -m services.orchestrator
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will be available at http://localhost:3000

## Configuration

### Scraper Configuration

Edit `config/scrapers.yaml` to:
- Enable/disable specific scrapers
- Adjust scraping intervals
- Configure Betfair mode (scraper vs API)

### Database

The database schema is automatically created when PostgreSQL starts via `db/init.sql`.

To access the database:
```bash
docker-compose exec postgres psql -U betting_user -d betting_monitor
```

Useful queries:
```sql
-- View all events
SELECT * FROM events ORDER BY scheduled_time;

-- View latest odds
SELECT * FROM latest_odds;

-- View scraper status
SELECT * FROM scraper_status;

-- View best odds
SELECT * FROM best_odds;
```

## Troubleshooting

### Scraper not starting

1. Check credentials in `.env`
2. View scraper logs: `docker-compose logs -f scraper`
3. Check if Chrome/Selenium is working: look for errors in logs

### No data appearing

1. Check scraper status: http://localhost:8000/status/scrapers
2. ProfitMaximiser site might not have any horses matching filters (Rating >= 97, EPV >= 102, Odds >= 2)
3. View scraper logs for errors

### Database connection errors

1. Ensure PostgreSQL is running: `docker-compose ps postgres`
2. Check database credentials in `.env`
3. Try restarting: `docker-compose restart postgres`

### Frontend not loading

1. Check if backend is running: http://localhost:8000/status/health
2. Clear browser cache
3. Check frontend logs: `docker-compose logs -f frontend`

## Stopping Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: deletes all data)
docker-compose down -v
```

## Next Steps

After basic setup is working:

1. **Phase 2**: Add WebSocket for real-time updates
2. **Phase 3**: Implement additional bookmaker scrapers
3. **Phase 4**: Add Betfair API integration
4. **Phase 5**: Add charts, filters, and advanced features

See the main plan document for full implementation roadmap.
