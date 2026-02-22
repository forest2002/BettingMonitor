import { useEffect, useState } from 'react'
import { Box, Typography, CircularProgress, Alert, Tabs, Tab } from '@mui/material'
import TrendingUpIcon from '@mui/icons-material/TrendingUp'
import ListIcon from '@mui/icons-material/List'
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet'
import { OddsTable } from './OddsTable'
import { OpportunitiesPanel } from './OpportunitiesPanel'
import { MyBets } from './MyBets'
import { useOddsStore } from '../../stores/oddsStore'

const REFRESH_INTERVAL = 2000 // 2 seconds (very fast updates)

export const Dashboard = () => {
  const { events, fetchEvents, isLoading, error } = useOddsStore()
  const [activeTab, setActiveTab] = useState(0)

  useEffect(() => {
    fetchEvents()
  }, [])

  useEffect(() => {
    if (activeTab !== 1) return // Only poll on All Races & Odds tab

    const intervalId = setInterval(() => {
      fetchEvents()
    }, REFRESH_INTERVAL)

    return () => clearInterval(intervalId)
  }, [activeTab])

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
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography
          variant="h4"
          component="h1"
          sx={{
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            fontWeight: 800,
          }}
        >
          Each-Way Tracker
        </Typography>
      </Box>

      <Tabs
        value={activeTab}
        onChange={handleTabChange}
        sx={{
          mb: 3,
          '& .MuiTabs-indicator': {
            height: 3,
            borderRadius: '3px 3px 0 0',
            background: 'linear-gradient(90deg, #667eea 0%, #764ba2 100%)',
          },
          '& .MuiTab-root': {
            textTransform: 'none',
            fontWeight: 600,
            fontSize: '1rem',
            minHeight: 56,
            transition: 'all 0.3s ease',
            '&:hover': {
              bgcolor: 'rgba(102, 126, 234, 0.08)',
            },
          },
        }}
      >
        <Tab icon={<TrendingUpIcon />} label="Each-Way Opportunities" iconPosition="start" />
        <Tab icon={<ListIcon />} label="All Races & Odds" iconPosition="start" />
        <Tab icon={<AccountBalanceWalletIcon />} label="My Bets" iconPosition="start" />
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
      {activeTab === 2 && <MyBets />}
    </Box>
  )
}
