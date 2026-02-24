# Each-Way Tracker

Real-time odds monitoring web application for UK bookmakers including Betfair, Bet365, William Hill, and more.

## Features

- Real-time odds monitoring from multiple bookmakers
- Live WebSocket updates without page refresh
- Historical price charts
- Filter and search capabilities
- Bookmaker comparison view
- Designed for easy migration from scraping to Betfair API

## Architecture

```
React Frontend (Browser)
    ↓ WebSocket + REST API
FastAPI Backend Server
    ↓
PostgreSQL (history) + Redis (live cache)
    ↑
Scraper Orchestrator
    ↓
Multiple Bookmaker Scrapers
    ↓
Bookmaker Websites
```

## Tech Stack

- **Frontend**: React 18 + TypeScript, Material-UI, Recharts, Vite
- **Backend**: Python FastAPI (async), WebSocket support
- **Storage**: PostgreSQL 15 with TimescaleDB extension, Redis 7
- **Scraping**: Selenium 4.x with undetected-chromedriver
- **Deployment**: Docker + Docker Compose
- **Scheduling**: APScheduler

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for local frontend development)
- Python 3.11+ (for local backend development)

### Setup

1. Clone the repository:
   ```bash
   cd /Users/bsslbj/Desktop/FirstUse/betting-monitor
   ```

2. Create `.env` file from template:
   ```bash
   cp .env.example .env
   ```

3. Edit `.env` and add your credentials:
   - `PROFIT_MAXIMISER_EMAIL` and `PROFIT_MAXIMISER_PASSWORD`
   - Update database passwords

4. Start all services:
   ```bash
   docker-compose up -d
   ```

5. Access the application:
   - Frontend: http://localhost:3000
   - API docs: http://localhost:8000/docs
   - Health check: http://localhost:8000/health

## Development

### Backend Development

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

## Project Structure

```
each-way-tracker/
├── backend/
│   ├── api/
│   │   └── routes/
│   ├── services/
│   │   └── scrapers/
│   ├── models/
│   ├── db/
│   └── main.py
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── services/
│   │   └── stores/
│   └── package.json
├── config/
│   ├── scrapers.yaml
│   └── selectors/
├── db/
│   └── init.sql
├── docker-compose.yml
└── README.md
```

## Deployment

### Local Server (Recommended)
Run on a home server or spare laptop with Docker installed.

### Cloud VPS
Deploy to DigitalOcean, Hetzner, or similar (~$12/month).

## Migration to Betfair API

The application is designed to easily migrate from web scraping to the official Betfair API:

1. Sign up for Betfair API access
2. Add API credentials to `.env`
3. Change `BETFAIR_MODE=api` in config
4. Restart services

## License

Private use only.
