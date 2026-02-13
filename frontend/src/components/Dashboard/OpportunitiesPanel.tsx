import { useEffect, useState } from 'react'
import {
  Box,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Alert,
  CircularProgress,
  Card,
  CardContent,
  Grid,
  Tooltip,
  IconButton,
} from '@mui/material'
import InfoIcon from '@mui/icons-material/Info'
import TrendingUpIcon from '@mui/icons-material/TrendingUp'
import { useOpportunitiesStore } from '../../stores/opportunitiesStore'

export const OpportunitiesPanel = () => {
  const { opportunities, isLoading, error, fetchOpportunities, lastFetch } =
    useOpportunitiesStore()
  const [hasShownAlert, setHasShownAlert] = useState(false)

  useEffect(() => {
    fetchOpportunities(5) // Minimum rating of 5

    // Refresh every 30 seconds
    const interval = setInterval(() => {
      fetchOpportunities(5)
    }, 30000)

    return () => clearInterval(interval)
  }, [])

  // Alert for new high-value opportunities
  useEffect(() => {
    const highValueOpps = opportunities.filter((opp) => opp.rating >= 20)
    if (highValueOpps.length > 0 && !hasShownAlert) {
      // Show browser notification if permitted
      if ('Notification' in window && Notification.permission === 'granted') {
        new Notification('High Value Opportunity!', {
          body: `${highValueOpps[0].selection_name} - Rating ${highValueOpps[0].rating}`,
          icon: '/favicon.ico',
        })
      }
      setHasShownAlert(true)
    }
  }, [opportunities])

  const getRatingColor = (rating: number) => {
    if (rating >= 20) return '#4caf50' // Green - Excellent
    if (rating >= 10) return '#ff9800' // Orange - Good
    return '#9e9e9e' // Grey - Marginal
  }

  const getRatingLabel = (rating: number) => {
    if (rating >= 20) return 'EXCELLENT'
    if (rating >= 10) return 'GOOD'
    return 'MARGINAL'
  }

  const formatCurrency = (value: number) => {
    return `£${value.toFixed(2)}`
  }

  if (isLoading && opportunities.length === 0) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    )
  }

  if (error) {
    return <Alert severity="error">{error}</Alert>
  }

  const goodOpportunities = opportunities.filter((opp) => opp.rating >= 10)
  const totalEV = opportunities.reduce((sum, opp) => sum + opp.expected_value, 0)

  return (
    <Box>
      {/* Summary Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Opportunities Found
              </Typography>
              <Typography variant="h4">
                {opportunities.length}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {goodOpportunities.length} rated Good or better
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Total Expected Value
              </Typography>
              <Typography variant="h4" color={totalEV > 0 ? 'success.main' : 'error.main'}>
                {formatCurrency(totalEV)}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Across all opportunities
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Best Opportunity
              </Typography>
              <Typography variant="h4">
                {opportunities[0]?.rating || 0}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {opportunities[0]?.selection_name || 'None'}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Opportunities Table */}
      {opportunities.length === 0 ? (
        <Alert severity="info" icon={<TrendingUpIcon />}>
          No each-way arbitrage opportunities found at the moment. The system is monitoring odds continuously.
        </Alert>
      ) : (
        <>
          <Alert severity="success" sx={{ mb: 2 }}>
            <strong>{opportunities.length} opportunities found!</strong> These are horses where the bookmaker's place odds are better than Betfair's lay odds, creating a profitable arbitrage.
          </Alert>

          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow sx={{ backgroundColor: '#1976d2' }}>
                  <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>
                    Rating
                  </TableCell>
                  <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>
                    Horse
                  </TableCell>
                  <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>
                    Race
                  </TableCell>
                  <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>
                    Bookmaker
                  </TableCell>
                  <TableCell sx={{ color: 'white', fontWeight: 'bold' }} align="right">
                    Place Odds
                  </TableCell>
                  <TableCell sx={{ color: 'white', fontWeight: 'bold' }} align="right">
                    Betfair Lay
                  </TableCell>
                  <TableCell sx={{ color: 'white', fontWeight: 'bold' }} align="right">
                    Edge
                  </TableCell>
                  <TableCell sx={{ color: 'white', fontWeight: 'bold' }} align="right">
                    Expected Value
                  </TableCell>
                  <TableCell sx={{ color: 'white', fontWeight: 'bold' }} align="center">
                    Profit Scenarios
                    <Tooltip title="Shows profit/loss for: Win | Place | Lose">
                      <IconButton size="small" sx={{ color: 'white', ml: 0.5 }}>
                        <InfoIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {opportunities.map((opp, index) => (
                  <TableRow
                    key={index}
                    sx={{
                      backgroundColor: opp.rating >= 20 ? '#e8f5e9' : opp.rating >= 10 ? '#fff3e0' : 'inherit',
                      '&:hover': {
                        backgroundColor: opp.rating >= 20 ? '#c8e6c9' : opp.rating >= 10 ? '#ffe0b2' : '#f5f5f5',
                      },
                    }}
                  >
                    {/* Rating */}
                    <TableCell>
                      <Chip
                        label={`${opp.rating} - ${getRatingLabel(opp.rating)}`}
                        sx={{
                          backgroundColor: getRatingColor(opp.rating),
                          color: 'white',
                          fontWeight: 'bold',
                        }}
                      />
                    </TableCell>

                    {/* Horse Name */}
                    <TableCell>
                      <Typography fontWeight="bold">{opp.selection_name}</Typography>
                    </TableCell>

                    {/* Race */}
                    <TableCell>
                      <Typography variant="body2">{opp.event_name}</Typography>
                    </TableCell>

                    {/* Bookmaker */}
                    <TableCell>
                      <Typography variant="body2">{opp.bookmaker}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {opp.num_places} places
                      </Typography>
                    </TableCell>

                    {/* Bookmaker Place Odds */}
                    <TableCell align="right">
                      <Typography fontWeight="bold" color="success.main">
                        {opp.bookmaker_place_odds.toFixed(2)}
                      </Typography>
                    </TableCell>

                    {/* Betfair Lay Odds */}
                    <TableCell align="right">
                      <Typography fontWeight="bold">
                        {opp.betfair_lay_odds.toFixed(2)}
                      </Typography>
                    </TableCell>

                    {/* Edge */}
                    <TableCell align="right">
                      <Chip
                        label={`+${(opp.edge * 100).toFixed(1)}%`}
                        size="small"
                        color="success"
                      />
                    </TableCell>

                    {/* Expected Value */}
                    <TableCell align="right">
                      <Typography
                        fontWeight="bold"
                        fontSize="1.1rem"
                        color={opp.expected_value > 0 ? 'success.main' : 'error.main'}
                      >
                        {formatCurrency(opp.expected_value)}
                      </Typography>
                    </TableCell>

                    {/* Profit Scenarios */}
                    <TableCell align="center">
                      <Box sx={{ display: 'flex', gap: 1, justifyContent: 'center' }}>
                        <Tooltip title="If horse WINS">
                          <Chip
                            label={formatCurrency(opp.profit_if_wins)}
                            size="small"
                            sx={{
                              backgroundColor: opp.profit_if_wins > 0 ? '#4caf50' : '#f44336',
                              color: 'white',
                            }}
                          />
                        </Tooltip>
                        <Tooltip title="If horse PLACES">
                          <Chip
                            label={formatCurrency(opp.profit_if_places)}
                            size="small"
                            sx={{
                              backgroundColor: opp.profit_if_places > 0 ? '#4caf50' : '#f44336',
                              color: 'white',
                            }}
                          />
                        </Tooltip>
                        <Tooltip title="If horse LOSES">
                          <Chip
                            label={formatCurrency(opp.profit_if_loses)}
                            size="small"
                            sx={{
                              backgroundColor: opp.profit_if_loses > 0 ? '#4caf50' : '#f44336',
                              color: 'white',
                            }}
                          />
                        </Tooltip>
                      </Box>
                      <Typography variant="caption" color="text.secondary">
                        Win | Place | Lose
                      </Typography>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>

          {lastFetch && (
            <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
              Last updated: {lastFetch.toLocaleTimeString()}
            </Typography>
          )}
        </>
      )}
    </Box>
  )
}
