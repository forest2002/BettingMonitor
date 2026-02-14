import { create } from 'zustand'
import { Event, Odds } from '../types'
import { eventsApi, oddsApi } from '../services/api'

interface OddsStore {
  events: Event[]
  oddsMap: Map<number, Odds[]> // eventId -> Odds[]
  isLoading: boolean
  error: string | null
  fetchEvents: () => Promise<void>
  fetchEventOdds: (eventId: number) => Promise<void>
  fetchAllEventOdds: () => Promise<void>
}

export const useOddsStore = create<OddsStore>((set, get) => ({
  events: [],
  oddsMap: new Map(),
  isLoading: false,
  error: null,

  fetchEvents: async () => {
    set({ isLoading: true, error: null })
    try {
      // Calculate hours until end of today (midnight)
      const now = new Date()
      const endOfDay = new Date(now)
      endOfDay.setHours(23, 59, 59, 999)
      const hoursUntilMidnight = Math.max(1, Math.ceil((endOfDay.getTime() - now.getTime()) / (1000 * 60 * 60)))

      const events = await eventsApi.getEvents({
        hours_ahead: hoursUntilMidnight,
        status: 'upcoming',
      })
      set({ events, isLoading: false })

      // Automatically fetch odds for all events
      get().fetchAllEventOdds()
    } catch (error: any) {
      set({
        error: error.message || 'Failed to fetch events',
        isLoading: false,
      })
    }
  },

  fetchEventOdds: async (eventId: number) => {
    try {
      const rawOdds = await oddsApi.getEventOdds(eventId)
      // Backend returns Decimal fields as strings — convert to numbers
      const odds = rawOdds.map((o) => ({
        ...o,
        odds_decimal: Number(o.odds_decimal),
        place_odds: o.place_odds != null ? Number(o.place_odds) : null,
      }))
      const oddsMap = new Map(get().oddsMap)
      oddsMap.set(eventId, odds)
      set({ oddsMap })
    } catch (error: any) {
      console.error(`Failed to fetch odds for event ${eventId}:`, error)
    }
  },

  fetchAllEventOdds: async () => {
    const { events } = get()
    await Promise.all(events.map((event) => get().fetchEventOdds(event.id)))
  },
}))
