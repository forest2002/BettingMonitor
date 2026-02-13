import { useEffect } from 'react'
import { Box, Typography, CircularProgress, Alert } from '@mui/material'
import { OddsTable } from './OddsTable'
import { useOddsStore } from '../../stores/oddsStore'

export const Dashboard = () => {
  const { events, fetchEvents, isLoading, error } = useOddsStore()

  useEffect(() => {
    fetchEvents()
  }, [])

  if (isLoading && events.length === 0) {
    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: 400,
        }}
      >
        <CircularProgress />
      </Box>
    )
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        {error}
      </Alert>
    )
  }

  if (events.length === 0) {
    return (
      <Alert severity="info" sx={{ mb: 2 }}>
        No upcoming events found. The scraper may still be initializing.
      </Alert>
    )
  }

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Upcoming Events
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Showing {events.length} events in the next 24 hours
      </Typography>
      <OddsTable />
    </Box>
  )
}
