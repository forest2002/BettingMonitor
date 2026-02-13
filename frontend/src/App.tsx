import { Container, AppBar, Toolbar, Typography, Box, Button } from '@mui/material'
import RefreshIcon from '@mui/icons-material/Refresh'
import { Dashboard } from './components/Dashboard/Dashboard'
import { useOddsStore } from './stores/oddsStore'

function App() {
  const { fetchEvents, isLoading } = useOddsStore()

  const handleRefresh = () => {
    fetchEvents()
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Betting Monitor
          </Typography>
          <Button
            color="inherit"
            startIcon={<RefreshIcon />}
            onClick={handleRefresh}
            disabled={isLoading}
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
          py: 2,
          px: 2,
          mt: 'auto',
          backgroundColor: (theme) =>
            theme.palette.mode === 'light'
              ? theme.palette.grey[200]
              : theme.palette.grey[800],
        }}
      >
        <Container maxWidth="xl">
          <Typography variant="body2" color="text.secondary" align="center">
            Betting Monitor v1.0.0 - Real-time odds monitoring
          </Typography>
        </Container>
      </Box>
    </Box>
  )
}

export default App
