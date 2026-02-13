-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Bookmakers table
CREATE TABLE bookmakers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Event types (horse_racing, football, etc.)
CREATE TABLE event_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Events (races, matches)
CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    event_type_id INTEGER NOT NULL REFERENCES event_types(id),
    name VARCHAR(255) NOT NULL,
    venue VARCHAR(100),
    scheduled_time TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(20) DEFAULT 'upcoming',
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_events_scheduled_time ON events(scheduled_time);
CREATE INDEX idx_events_status ON events(status);
CREATE INDEX idx_events_event_type ON events(event_type_id);

-- Selections (horses, teams, players)
CREATE TABLE selections (
    id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(event_id, name)
);

CREATE INDEX idx_selections_event_id ON selections(event_id);

-- Odds history (TimescaleDB hypertable for time-series optimization)
CREATE TABLE odds_history (
    id BIGSERIAL,
    selection_id INTEGER NOT NULL REFERENCES selections(id) ON DELETE CASCADE,
    bookmaker_id INTEGER NOT NULL REFERENCES bookmakers(id),
    odds_decimal NUMERIC(10, 2) NOT NULL,
    place_odds NUMERIC(10, 2),
    place_terms VARCHAR(20),
    scraped_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB,
    CHECK (odds_decimal >= 1.01 AND odds_decimal <= 1000.0)
);

-- Convert to hypertable for time-series optimization
SELECT create_hypertable('odds_history', 'scraped_at', chunk_time_interval => INTERVAL '1 day');

-- Indexes for odds_history
CREATE INDEX idx_odds_selection_time ON odds_history(selection_id, scraped_at DESC);
CREATE INDEX idx_odds_bookmaker_time ON odds_history(bookmaker_id, scraped_at DESC);
CREATE INDEX idx_odds_scraped_at ON odds_history(scraped_at DESC);

-- Scraper status tracking
CREATE TABLE scraper_status (
    bookmaker_id INTEGER PRIMARY KEY REFERENCES bookmakers(id),
    last_scrape_at TIMESTAMP WITH TIME ZONE,
    last_success_at TIMESTAMP WITH TIME ZONE,
    last_error TEXT,
    total_scrapes INTEGER DEFAULT 0,
    total_errors INTEGER DEFAULT 0,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Seed data: Bookmakers
INSERT INTO bookmakers (name, display_name, enabled) VALUES
    ('profit_maximiser', 'Profit Maximiser', true),
    ('betfair', 'Betfair Exchange', false),
    ('bet365', 'Bet365', false),
    ('william_hill', 'William Hill', false),
    ('ladbrokes', 'Ladbrokes', false),
    ('coral', 'Coral', false),
    ('paddy_power', 'Paddy Power', false);

-- Seed data: Event types
INSERT INTO event_types (name, display_name) VALUES
    ('horse_racing', 'Horse Racing'),
    ('football', 'Football'),
    ('tennis', 'Tennis'),
    ('greyhounds', 'Greyhounds');

-- Initialize scraper status
INSERT INTO scraper_status (bookmaker_id, total_scrapes, total_errors)
SELECT id, 0, 0 FROM bookmakers;

-- View for latest odds per selection
CREATE VIEW latest_odds AS
SELECT DISTINCT ON (oh.selection_id, oh.bookmaker_id)
    oh.id,
    oh.selection_id,
    oh.bookmaker_id,
    b.display_name as bookmaker_name,
    oh.odds_decimal,
    oh.place_odds,
    oh.place_terms,
    oh.scraped_at,
    s.name as selection_name,
    e.name as event_name,
    e.scheduled_time,
    e.venue
FROM odds_history oh
JOIN selections s ON oh.selection_id = s.id
JOIN events e ON s.event_id = e.id
JOIN bookmakers b ON oh.bookmaker_id = b.id
WHERE e.scheduled_time > NOW()
ORDER BY oh.selection_id, oh.bookmaker_id, oh.scraped_at DESC;

-- View for best odds per selection
CREATE VIEW best_odds AS
SELECT
    s.id as selection_id,
    s.name as selection_name,
    e.id as event_id,
    e.name as event_name,
    e.scheduled_time,
    e.venue,
    MAX(oh.odds_decimal) as best_odds,
    (
        SELECT b.display_name
        FROM odds_history oh2
        JOIN bookmakers b ON oh2.bookmaker_id = b.id
        WHERE oh2.selection_id = s.id
        AND oh2.scraped_at > NOW() - INTERVAL '5 minutes'
        ORDER BY oh2.odds_decimal DESC
        LIMIT 1
    ) as best_bookmaker
FROM selections s
JOIN events e ON s.event_id = e.id
LEFT JOIN odds_history oh ON s.id = oh.selection_id
WHERE e.scheduled_time > NOW()
AND oh.scraped_at > NOW() - INTERVAL '5 minutes'
GROUP BY s.id, s.name, e.id, e.name, e.scheduled_time, e.venue;

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for events table
CREATE TRIGGER update_events_updated_at BEFORE UPDATE ON events
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Trigger for scraper_status table
CREATE TRIGGER update_scraper_status_updated_at BEFORE UPDATE ON scraper_status
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add compression policy for old data (compress data older than 7 days)
-- Disabled for MVP - requires columnstore to be enabled first
-- SELECT add_compression_policy('odds_history', INTERVAL '7 days');

-- Add retention policy to drop data older than 90 days
-- Disabled for MVP
-- SELECT add_retention_policy('odds_history', INTERVAL '90 days');
