import { create } from 'zustand'
import { CurrentOrder, ClearedOrder } from '../types'
import { ordersApi } from '../services/api'

interface BetsState {
  currentOrders: CurrentOrder[]
  clearedOrders: ClearedOrder[]
  totalProfit: number
  isLoading: boolean
  error: string | null
  fetchCurrentOrders: () => Promise<void>
  fetchClearedOrders: (settledDate?: string) => Promise<void>
}

export const useBetsStore = create<BetsState>((set) => ({
  currentOrders: [],
  clearedOrders: [],
  totalProfit: 0,
  isLoading: false,
  error: null,

  fetchCurrentOrders: async () => {
    set({ isLoading: true, error: null })
    try {
      const data = await ordersApi.getCurrentOrders()
      set({ currentOrders: data.orders, isLoading: false })
    } catch (err: any) {
      set({
        error: err.response?.data?.detail || 'Failed to fetch current orders',
        isLoading: false,
      })
    }
  },

  fetchClearedOrders: async (settledDate?: string) => {
    set({ isLoading: true, error: null })
    try {
      const data = await ordersApi.getClearedOrders(settledDate)
      set({
        clearedOrders: data.orders,
        totalProfit: data.totalProfit,
        isLoading: false,
      })
    } catch (err: any) {
      set({
        error: err.response?.data?.detail || 'Failed to fetch cleared orders',
        isLoading: false,
      })
    }
  },
}))
