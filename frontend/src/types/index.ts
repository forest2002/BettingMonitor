export interface Event {
  id: number
  event_type_id: number
  event_type_name?: string
  name: string
  venue: string | null
  scheduled_time: string
  status: string
  metadata: Record<string, any> | null
  created_at: string
  updated_at: string
  selections: Selection[]
}

export interface Selection {
  id: number
  event_id: number
  name: string
  metadata: Record<string, any> | null
}

export interface Odds {
  id: number
  selection_id: number
  bookmaker_id: number
  odds_decimal: number
  place_odds: number | null
  place_terms: string | null
  scraped_at: string
  metadata: Record<string, any> | null
  selection_name: string
  bookmaker_name: string
  event_name: string
  event_id: number
  scheduled_time: string
  venue: string | null
}

export interface CurrentOrder {
  betId: string
  marketId: string
  selectionId: number
  side: 'BACK' | 'LAY'
  price: number
  size: number
  sizeMatched: number
  sizeRemaining: number
  status: string
  placedDate: string
  matchedDate: string
  eventName: string
  marketName: string
  runnerName: string
  scheduledTime: string
  isEachWay: boolean
}

export interface ClearedOrder {
  betId: string
  marketId: string
  selectionId: number
  side: 'BACK' | 'LAY'
  priceMatched: number
  sizeSettled: number
  profit: number
  placedDate: string
  settledDate: string
  eventName: string
  marketName: string
  runnerName: string
  isEachWay: boolean
}

export interface ScraperStatus {
  bookmaker_id: number
  bookmaker_name: string
  last_scrape_at: string | null
  last_success_at: string | null
  last_error: string | null
  total_scrapes: number
  total_errors: number
  is_healthy: boolean
}
