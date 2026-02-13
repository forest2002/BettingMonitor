import { create } from 'zustand'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

interface Opportunity {
  selection_name: string
  event_name: string
  bookmaker: string
  bookmaker_place_odds: number
  betfair_lay_odds: number
  rating: number
  edge: number
  expected_value: number
  profit_if_places: number
  profit_if_wins: number
  profit_if_loses: number
  num_places: number
}

interface OpportunitiesState {
  opportunities: Opportunity[]
  isLoading: boolean
  error: string | null
  lastFetch: Date | null
  fetchOpportunities: (minRating?: number) => Promise<void>
}

export const useOpportunitiesStore = create<OpportunitiesState>((set) => ({
  opportunities: [],
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
      set({
        opportunities: data.opportunities,
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
}))
