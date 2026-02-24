import { create } from 'zustand'
import { Event, Odds } from '../types'
import { eventsApi, oddsApi } from '../services/api'

interface OddsStore {
  events: Event[]
  oddsMap: Record<number, Odds[]> // eventId -> Odds[]
  lastUpdate: number // Timestamp to force re-renders
  isLoading: boolean
  error: string | null
  fetchEvents: () => Promise<void>
  fetchEventOdds: (eventId: number) => Promise<void>
  fetchAllEventOdds: () => Promise<void>
}

export const useOddsStore = create<OddsStore>((set, get) => ({
  events: [],
  oddsMap: {},
  lastUpdate: Date.now(),
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
      console.log(`[OddsStore] Fetched ${rawOdds.length} odds for event ${eventId}`)

      // Backend returns Decimal fields as strings — convert to numbers
      const odds = rawOdds.map((o) => ({
        ...o,
        odds_decimal: Number(o.odds_decimal),
        place_odds: o.place_odds != null ? Number(o.place_odds) : null,
      }))

      // Use functional update to avoid race conditions
      set((state) => {
        const newOddsMap = { ...state.oddsMap, [eventId]: odds }
        console.log(`[OddsStore] Updated event ${eventId}, map now has ${Object.keys(newOddsMap).length} events`)
        return { oddsMap: newOddsMap, lastUpdate: Date.now() }
      })
    } catch (error: any) {
      console.error(`Failed to fetch odds for event ${eventId}:`, error)
    }
  },

  fetchAllEventOdds: async () => {
    const { events } = get()
    if (events.length === 0) return

    try {
      // Use batch endpoint instead of individual requests
      const eventIds = events.map((e) => e.id)
      const batchData = await oddsApi.getBatchOdds(eventIds)

      // Convert Decimal fields from strings to numbers
      const newOddsMap: Record<number, Odds[]> = {}
      for (const [eventIdStr, rawOdds] of Object.entries(batchData)) {
        const eventId = Number(eventIdStr)
        newOddsMap[eventId] = rawOdds.map((o) => ({
          ...o,
          odds_decimal: Number(o.odds_decimal),
          place_odds: o.place_odds != null ? Number(o.place_odds) : null,
        }))
      }

      console.log(`[OddsStore] Batch fetched odds for ${Object.keys(newOddsMap).length} events`)
      set({ oddsMap: newOddsMap, lastUpdate: Date.now() })
    } catch (error: any) {
      console.error('Failed to fetch batch odds:', error)
      // Fallback to individual requests if batch fails
      await Promise.all(events.map((event) => get().fetchEventOdds(event.id)))
    }
  },
}))
