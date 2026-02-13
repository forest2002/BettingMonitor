from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal

class BookmakerSchema(BaseModel):
    id: int
    name: str
    display_name: str
    enabled: bool

    model_config = ConfigDict(from_attributes=True)

class EventTypeSchema(BaseModel):
    id: int
    name: str
    display_name: str

    model_config = ConfigDict(from_attributes=True)

class SelectionSchema(BaseModel):
    id: int
    event_id: int
    name: str
    metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)

class EventSchema(BaseModel):
    id: int
    event_type_id: int
    name: str
    venue: Optional[str] = None
    scheduled_time: datetime
    status: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class EventWithSelectionsSchema(EventSchema):
    event_type_name: Optional[str] = None
    selections: List[SelectionSchema] = []

class OddsSchema(BaseModel):
    id: int
    selection_id: int
    bookmaker_id: int
    odds_decimal: Decimal
    place_odds: Optional[Decimal] = None
    place_terms: Optional[str] = None
    scraped_at: datetime
    metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)

class OddsWithDetailsSchema(OddsSchema):
    selection_name: str
    bookmaker_name: str
    event_name: str
    event_id: int
    scheduled_time: datetime
    venue: Optional[str] = None

class OddsUpdateMessage(BaseModel):
    """WebSocket message for odds updates"""
    type: str = "odds_update"
    selection_id: int
    bookmaker_id: int
    odds_decimal: float
    place_odds: Optional[float] = None
    place_terms: Optional[str] = None
    scraped_at: datetime
    event_id: int

class ScraperStatusSchema(BaseModel):
    bookmaker_id: int
    bookmaker_name: str
    last_scrape_at: Optional[datetime] = None
    last_success_at: Optional[datetime] = None
    last_error: Optional[str] = None
    total_scrapes: int
    total_errors: int
    is_healthy: bool

    model_config = ConfigDict(from_attributes=True)

# Data classes for scrapers
class OddsData(BaseModel):
    """Standardized format for scraped odds data"""
    event_name: str
    venue: str
    scheduled_time: datetime
    selection_name: str
    odds_decimal: Decimal
    place_odds: Optional[Decimal] = None
    place_terms: Optional[str] = None
    bookmaker_name: str
    event_type: str = "horse_racing"
    metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)
