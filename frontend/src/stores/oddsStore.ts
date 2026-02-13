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
      const events = await eventsApi.getEvents({
        hours_ahead: 24,
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
      const odds = await oddsApi.getEventOdds(eventId)
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
