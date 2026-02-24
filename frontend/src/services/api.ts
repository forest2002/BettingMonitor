import axios from 'axios'
import { Event, Odds, ScraperStatus, CurrentOrder, ClearedOrder } from '../types'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
})

export const eventsApi = {
  getEvents: async (params?: {
    event_type?: string
    hours_ahead?: number
    status?: string
  }): Promise<Event[]> => {
    const response = await api.get('/events/', { params })
    return response.data
  },

  getEvent: async (eventId: number): Promise<Event> => {
    const response = await api.get(`/events/${eventId}`)
    return response.data
  },
}

export const oddsApi = {
  getEventOdds: async (
    eventId: number,
    bookmakerIds?: string
  ): Promise<Odds[]> => {
    const response = await api.get(`/odds/events/${eventId}`, {
      params: { bookmaker_ids: bookmakerIds },
    })
    return response.data
  },

  getBatchOdds: async (
    eventIds: number[],
    bookmakerIds?: string
  ): Promise<Record<number, Odds[]>> => {
    const response = await api.get('/odds/batch', {
      params: {
        event_ids: eventIds.join(','),
        bookmaker_ids: bookmakerIds,
      },
    })
    return response.data
  },

  getSelectionHistory: async (
    selectionId: number,
    hours: number = 1,
    bookmakerIds?: string
  ): Promise<any> => {
    const response = await api.get(`/odds/selections/${selectionId}/history`, {
      params: { hours, bookmaker_ids: bookmakerIds },
    })
    return response.data
  },

  getBestOdds: async (params?: {
    event_type?: string
    hours_ahead?: number
  }): Promise<any[]> => {
    const response = await api.get('/odds/best', { params })
    return response.data
  },
}

export const statusApi = {
  getScraperStatus: async (): Promise<ScraperStatus[]> => {
    const response = await api.get('/status/scrapers')
    return response.data
  },

  getHealth: async (): Promise<any> => {
    const response = await api.get('/status/health')
    return response.data
  },
}

export const ordersApi = {
  getCurrentOrders: async (): Promise<{ orders: CurrentOrder[] }> => {
    const response = await api.get('/orders/current')
    return response.data
  },

  getClearedOrders: async (
    settledDate?: string
  ): Promise<{ orders: ClearedOrder[]; totalProfit: number; settledDate: string }> => {
    const response = await api.get('/orders/cleared', {
      params: settledDate ? { settled_date: settledDate } : undefined,
    })
    return response.data
  },
}
