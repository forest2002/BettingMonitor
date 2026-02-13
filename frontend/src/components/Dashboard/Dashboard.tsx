import { useEffect, useState } from 'react'
import { Box, Typography, CircularProgress, Alert, Tabs, Tab } from '@mui/material'
import TrendingUpIcon from '@mui/icons-material/TrendingUp'
import ListIcon from '@mui/icons-material/List'
import { OddsTable } from './OddsTable'
import { OpportunitiesPanel } from './OpportunitiesPanel'
import { useOddsStore } from '../../stores/oddsStore'

export const Dashboard = () => {
  const { events, fetchEvents, isLoading, error } = useOddsStore()
  const [activeTab, setActiveTab] = useState(0)

  useEffect(() => {
    fetchEvents()
  }, [])

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue)
  }

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

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Betting Monitor
      </Typography>

      <Tabs value={activeTab} onChange={handleTabChange} sx={{ mb: 3 }}>
        <Tab icon={<TrendingUpIcon />} label="Each-Way Opportunities" />
        <Tab icon={<ListIcon />} label="All Races & Odds" />
      </Tabs>

      {activeTab === 0 && <OpportunitiesPanel />}
      {activeTab === 1 && (
        <>
          {events.length === 0 ? (
            <Alert severity="info">
              No upcoming events found. The scraper may still be initializing.
            </Alert>
          ) : (
            <>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Showing {events.length} events in the next 24 hours
              </Typography>
              <OddsTable />
            </>
          )}
        </>
      )}
    </Box>
  )
}
