import { Container, AppBar, Toolbar, Typography, Box, Button, Chip } from '@mui/material'
import RefreshIcon from '@mui/icons-material/Refresh'
import AutorenewIcon from '@mui/icons-material/Autorenew'
import { Dashboard } from './components/Dashboard/Dashboard'
import { useOddsStore } from './stores/oddsStore'
import { useOpportunitiesStore } from './stores/opportunitiesStore'

function App() {
  const { fetchEvents, isLoading } = useOddsStore()
  const { fetchOpportunities } = useOpportunitiesStore()

  const handleRefresh = () => {
    fetchEvents()
    fetchOpportunities()
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <AppBar
        position="static"
        elevation={0}
        sx={{
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
        }}
      >
        <Toolbar>
          <Typography
            variant="h6"
            component="div"
            sx={{
              flexGrow: 1,
              fontWeight: 700,
              letterSpacing: '-0.02em',
              display: 'flex',
              alignItems: 'center',
              gap: 1,
            }}
          >
            <Box
              sx={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                bgcolor: '#10b981',
                animation: 'pulse 2s ease-in-out infinite',
                '@keyframes pulse': {
                  '0%, 100%': { opacity: 1 },
                  '50%': { opacity: 0.5 },
                },
              }}
            />
            Betting Monitor
          </Typography>
          <Chip
            icon={<AutorenewIcon />}
            label="Auto-refresh: 60s"
            size="small"
            sx={{
              mr: 2,
              bgcolor: 'rgba(16, 185, 129, 0.15)',
              color: '#10b981',
              fontWeight: 600,
              '& .MuiChip-icon': {
                color: '#10b981',
                animation: 'spin 3s linear infinite',
                '@keyframes spin': {
                  '0%': { transform: 'rotate(0deg)' },
                  '100%': { transform: 'rotate(360deg)' },
                },
              },
            }}
          />
          <Button
            color="inherit"
            startIcon={<RefreshIcon />}
            onClick={handleRefresh}
            disabled={isLoading}
            sx={{
              bgcolor: 'rgba(255, 255, 255, 0.1)',
              '&:hover': {
                bgcolor: 'rgba(255, 255, 255, 0.2)',
              },
              backdropFilter: 'blur(10px)',
              transition: 'all 0.3s ease',
            }}
          >
            Refresh
          </Button>
        </Toolbar>
      </AppBar>

      <Container maxWidth="xl" sx={{ mt: 4, mb: 4, flexGrow: 1 }}>
        <Dashboard />
      </Container>

      <Box
        component="footer"
        sx={{
          py: 3,
          px: 2,
          mt: 'auto',
          borderTop: '1px solid rgba(255, 255, 255, 0.05)',
          background: 'linear-gradient(180deg, transparent 0%, rgba(0, 0, 0, 0.2) 100%)',
        }}
      >
        <Container maxWidth="xl">
          <Typography
            variant="body2"
            color="text.secondary"
            align="center"
            sx={{ fontWeight: 500 }}
          >
            Betting Monitor v1.0.0 - Real-time odds monitoring
          </Typography>
        </Container>
      </Box>
    </Box>
  )
}

export default App
