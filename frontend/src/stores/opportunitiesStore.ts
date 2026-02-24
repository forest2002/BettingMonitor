import { create } from 'zustand'
import { persist } from 'zustand/middleware'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export interface Opportunity {
  selection_name: string
  event_name: string
  venue: string | null
  scheduled_time: string | null
  bookmaker: string
  bookmaker_win_odds: number
  bookmaker_place_odds: number
  betfair_win_lay_odds: number
  betfair_place_lay_odds: number
  win_edge: number
  place_edge: number
  total_edge: number
  rating: number
  win_lay_stake: number
  place_lay_stake: number
  profit_if_wins: number
  profit_if_places: number
  profit_if_loses: number
  num_places: number
  is_fair_odds: boolean
}

export interface BookmakerEntry {
  bookmaker: string
  bookmaker_win_odds: number
  bookmaker_place_odds: number
  betfair_win_lay_odds: number
  betfair_place_lay_odds: number
  win_edge: number
  place_edge: number
  total_edge: number
  rating: number
  win_lay_stake: number
  place_lay_stake: number
  profit_if_wins: number
  profit_if_places: number
  profit_if_loses: number
  num_places: number
  is_fair_odds: boolean
}

export interface HistoricalOpportunity {
  selection_name: string
  event_name: string
  venue: string | null
  scheduled_time: string | null
  firstSeen: string   // ISO timestamp
  lastSeen: string    // ISO timestamp
  bestRating: number
  bookmakers: BookmakerEntry[]
}

function historyKey(opp: { selection_name: string; event_name: string }): string {
  return `${opp.selection_name}::${opp.event_name}`
}

function oppToBookmakerEntry(opp: Opportunity): BookmakerEntry {
  return {
    bookmaker: opp.bookmaker,
    bookmaker_win_odds: opp.bookmaker_win_odds,
    bookmaker_place_odds: opp.bookmaker_place_odds,
    betfair_win_lay_odds: opp.betfair_win_lay_odds,
    betfair_place_lay_odds: opp.betfair_place_lay_odds,
    win_edge: opp.win_edge,
    place_edge: opp.place_edge,
    total_edge: opp.total_edge,
    rating: opp.rating,
    win_lay_stake: opp.win_lay_stake,
    place_lay_stake: opp.place_lay_stake,
    profit_if_wins: opp.profit_if_wins,
    profit_if_places: opp.profit_if_places,
    profit_if_loses: opp.profit_if_loses,
    num_places: opp.num_places,
    is_fair_odds: opp.is_fair_odds,
  }
}

interface OpportunitiesState {
  opportunities: Opportunity[]
  history: HistoricalOpportunity[]
  isLoading: boolean
  error: string | null
  lastFetch: Date | null
  fetchOpportunities: (minRating?: number) => Promise<void>
  clearHistory: () => void
}

export const useOpportunitiesStore = create<OpportunitiesState>()(
  persist(
    (set, get) => ({
  opportunities: [],
  history: [],
  isLoading: false,
  error: null,
  lastFetch: null,

  fetchOpportunities: async (minRating = 0) => {
    set({ isLoading: true, error: null })
    try {
      const response = await fetch(
        `${API_BASE_URL}/opportunities/each-way?min_rating=${minRating}`
      )
      if (!response.ok) {
        throw new Error('Failed to fetch opportunities')
      }
      const data = await response.json()
      const incoming: Opportunity[] = data.opportunities
      const now = new Date().toISOString()

      const { history } = get()

      // Build lookup of existing history by selection+event key
      const historyMap = new Map<string, HistoricalOpportunity>()
      for (const h of history) {
        historyMap.set(historyKey(h), h)
      }

      // Group incoming opportunities by selection+event
      const incomingByKey = new Map<string, Opportunity[]>()
      for (const opp of incoming) {
        const key = historyKey(opp)
        const group = incomingByKey.get(key) || []
        group.push(opp)
        incomingByKey.set(key, group)
      }

      // Update history: one entry per selection+event, all bookmakers grouped
      for (const [key, opps] of incomingByKey) {
        const bestOpp = opps.reduce((a, b) => (b.rating > a.rating ? b : a))
        const bookmakerEntries = opps
          .map(oppToBookmakerEntry)
          .sort((a, b) => b.rating - a.rating)

        const existing = historyMap.get(key)
        if (existing) {
          // Merge bookmakers: keep any previously-seen bookmakers not in current batch, update those that are
          const currentBookmakers = new Set(bookmakerEntries.map(b => b.bookmaker))
          const previousOnly = existing.bookmakers.filter(b => !currentBookmakers.has(b.bookmaker))
          historyMap.set(key, {
            selection_name: bestOpp.selection_name,
            event_name: bestOpp.event_name,
            venue: bestOpp.venue,
            scheduled_time: bestOpp.scheduled_time,
            firstSeen: existing.firstSeen,
            lastSeen: now,
            bestRating: Math.max(existing.bestRating, bestOpp.rating),
            bookmakers: [...bookmakerEntries, ...previousOnly],
          })
        } else {
          historyMap.set(key, {
            selection_name: bestOpp.selection_name,
            event_name: bestOpp.event_name,
            venue: bestOpp.venue,
            scheduled_time: bestOpp.scheduled_time,
            firstSeen: now,
            lastSeen: now,
            bestRating: bestOpp.rating,
            bookmakers: bookmakerEntries,
          })
        }
      }

      // Sort history: most recently seen first
      const updatedHistory = Array.from(historyMap.values()).sort(
        (a, b) => new Date(b.lastSeen).getTime() - new Date(a.lastSeen).getTime()
      )

      set({
        opportunities: incoming,
        history: updatedHistory,
        isLoading: false,
        lastFetch: new Date(),
      })
    } catch (error: any) {
      set({
        error: error.message || 'Failed to fetch opportunities',
        isLoading: false,
      })
    }
  },

  clearHistory: () => set({ history: [] }),
}),
    {
      name: 'opportunities-history',
      partialize: (state) => ({ history: state.history }),
    }
  )
)
