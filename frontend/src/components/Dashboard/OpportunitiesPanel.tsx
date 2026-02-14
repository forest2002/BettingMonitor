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
      if ('Notification' in window && Notification.permission === 'granted') {
        new Notification('High Value Opportunity!', {
          body: `${highValueOpps[0].selection_name} - Rating ${highValueOpps[0].rating}%`,
          icon: '/favicon.ico',
        })
      }
      setHasShownAlert(true)
    }
  }, [opportunities])

  const getRatingColor = (rating: number) => {
    if (rating >= 20) return '#4caf50'
    if (rating >= 10) return '#ff9800'
    return '#9e9e9e'
  }

  const getRatingLabel = (rating: number) => {
    if (rating >= 20) return 'EXCELLENT'
    if (rating >= 10) return 'GOOD'
    return 'MARGINAL'
  }

  const formatCurrency = (value: number) => {
    return `£${value.toFixed(2)}`
  }

  const formatEdge = (value: number) => {
    return `${(value * 100).toFixed(1)}%`
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
  const totalEV = opportunities.reduce(
    (sum, opp) => sum + opp.profit_if_wins + opp.profit_if_places + opp.profit_if_loses,
    0
  )

  const headerCellSx = { color: 'white', fontWeight: 700, fontSize: '0.75rem', whiteSpace: 'nowrap' as const }

  return (
    <Box>
      {/* Summary Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={4}>
          <Card
            sx={{
              background: 'linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%)',
              border: '1px solid rgba(102, 126, 234, 0.2)',
            }}
          >
            <CardContent>
              <Typography
                color="text.secondary"
                gutterBottom
                sx={{ fontSize: '0.875rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}
              >
                Opportunities Found
              </Typography>
              <Typography variant="h3" sx={{ fontWeight: 700, mb: 1 }}>
                {opportunities.length}
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Box
                  sx={{
                    width: 8,
                    height: 8,
                    borderRadius: '50%',
                    bgcolor: 'success.main',
                  }}
                />
                <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 500 }}>
                  {goodOpportunities.length} rated Good or better
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card
            sx={{
              background: totalEV > 0
                ? 'linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(5, 150, 105, 0.1) 100%)'
                : 'linear-gradient(135deg, rgba(239, 68, 68, 0.1) 0%, rgba(220, 38, 38, 0.1) 100%)',
              border: totalEV > 0
                ? '1px solid rgba(16, 185, 129, 0.2)'
                : '1px solid rgba(239, 68, 68, 0.2)',
            }}
          >
            <CardContent>
              <Typography
                color="text.secondary"
                gutterBottom
                sx={{ fontSize: '0.875rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}
              >
                Profitable Opportunities
              </Typography>
              <Typography
                variant="h3"
                color={totalEV > 0 ? 'success.main' : 'error.main'}
                sx={{ fontWeight: 700, mb: 1 }}
              >
                {opportunities.length}
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 500 }}>
                All profit scenarios &gt;= 0
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card
            sx={{
              background: 'linear-gradient(135deg, rgba(245, 158, 11, 0.1) 0%, rgba(217, 119, 6, 0.1) 100%)',
              border: '1px solid rgba(245, 158, 11, 0.2)',
            }}
          >
            <CardContent>
              <Typography
                color="text.secondary"
                gutterBottom
                sx={{ fontSize: '0.875rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}
              >
                Best Rating
              </Typography>
              <Typography variant="h3" sx={{ fontWeight: 700, mb: 1 }}>
                {opportunities[0]?.rating || 0}%
              </Typography>
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{
                  fontWeight: 500,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
              >
                {opportunities[0]?.selection_name || 'None'}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Opportunities Table */}
      {opportunities.length === 0 ? (
        <Alert
          severity="info"
          icon={<TrendingUpIcon />}
          sx={{
            borderRadius: 2,
            border: '1px solid rgba(59, 130, 246, 0.3)',
            bgcolor: 'rgba(59, 130, 246, 0.05)',
            '& .MuiAlert-icon': {
              color: 'primary.main',
            },
          }}
        >
          No each-way profit maximiser opportunities found at the moment. The system is monitoring odds continuously.
        </Alert>
      ) : (
        <>
          <Alert
            severity="success"
            sx={{
              mb: 3,
              borderRadius: 2,
              border: '1px solid rgba(16, 185, 129, 0.3)',
              bgcolor: 'rgba(16, 185, 129, 0.05)',
              '& .MuiAlert-icon': {
                color: 'success.main',
              },
            }}
          >
            <strong>{opportunities.length} opportunities found!</strong> All shown opportunities are profitable (profit &gt;= 0) in every scenario (win, place, lose).
          </Alert>

          <TableContainer
            component={Paper}
            sx={{
              borderRadius: 3,
              overflow: 'auto',
              boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.2), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
            }}
          >
            <Table size="small">
              <TableHead>
                <TableRow
                  sx={{
                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    '& .MuiTableCell-root': {
                      borderBottom: 'none',
                    },
                  }}
                >
                  <TableCell sx={headerCellSx}>RATING</TableCell>
                  <TableCell sx={headerCellSx}>HORSE</TableCell>
                  <TableCell sx={headerCellSx}>RACE</TableCell>
                  <TableCell sx={headerCellSx}>BOOKMAKER</TableCell>
                  <TableCell sx={headerCellSx} align="right">BOOKIE WIN</TableCell>
                  <TableCell sx={headerCellSx} align="right">BOOKIE PLACE</TableCell>
                  <TableCell sx={headerCellSx} align="right">BF WIN LAY</TableCell>
                  <TableCell sx={headerCellSx} align="right">BF PLACE LAY</TableCell>
                  <TableCell sx={headerCellSx} align="right">WIN EDGE</TableCell>
                  <TableCell sx={headerCellSx} align="right">PLACE EDGE</TableCell>
                  <TableCell sx={headerCellSx} align="right">TOTAL EDGE</TableCell>
                  <TableCell sx={headerCellSx} align="center">
                    PROFIT (W|P|L)
                    <Tooltip title="Profit if horse: Wins | Places | Loses">
                      <IconButton size="small" sx={{ color: 'rgba(255, 255, 255, 0.9)', ml: 0.5 }}>
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
                      backgroundColor:
                        opp.rating >= 20
                          ? 'rgba(16, 185, 129, 0.08)'
                          : opp.rating >= 10
                          ? 'rgba(245, 158, 11, 0.08)'
                          : 'inherit',
                      borderLeft:
                        opp.rating >= 20
                          ? '4px solid #10b981'
                          : opp.rating >= 10
                          ? '4px solid #f59e0b'
                          : '4px solid transparent',
                      transition: 'all 0.3s ease',
                      '&:hover': {
                        backgroundColor:
                          opp.rating >= 20
                            ? 'rgba(16, 185, 129, 0.15)'
                            : opp.rating >= 10
                            ? 'rgba(245, 158, 11, 0.15)'
                            : 'rgba(100, 116, 139, 0.1)',
                        transform: 'scale(1.01)',
                        boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.2)',
                      },
                    }}
                  >
                    {/* Rating */}
                    <TableCell>
                      <Chip
                        label={`${opp.rating}% ${getRatingLabel(opp.rating)}`}
                        sx={{
                          backgroundColor: getRatingColor(opp.rating),
                          color: 'white',
                          fontWeight: 700,
                          fontSize: '0.75rem',
                          letterSpacing: '0.02em',
                          boxShadow: '0 2px 4px rgba(0, 0, 0, 0.2)',
                          border: '1px solid rgba(255, 255, 255, 0.2)',
                        }}
                      />
                    </TableCell>

                    {/* Horse Name */}
                    <TableCell>
                      <Typography fontWeight={700} fontSize="0.9rem" color="text.primary">
                        {opp.selection_name}
                      </Typography>
                    </TableCell>

                    {/* Race */}
                    <TableCell>
                      <Typography variant="body2" color="text.secondary" fontWeight={500}>
                        {opp.event_name}
                      </Typography>
                    </TableCell>

                    {/* Bookmaker */}
                    <TableCell>
                      <Typography variant="body2" fontWeight={600} color="text.primary">
                        {opp.bookmaker}
                      </Typography>
                      <Chip
                        label={`${opp.num_places} places`}
                        size="small"
                        sx={{
                          height: 20,
                          fontSize: '0.7rem',
                          mt: 0.5,
                          bgcolor: 'rgba(102, 126, 234, 0.15)',
                          color: 'primary.light',
                          fontWeight: 600,
                        }}
                      />
                    </TableCell>

                    {/* Bookie Win Odds */}
                    <TableCell align="right">
                      <Typography fontWeight={700} fontSize="0.95rem" color="text.primary">
                        {opp.bookmaker_win_odds.toFixed(2)}
                      </Typography>
                    </TableCell>

                    {/* Bookie Place Odds */}
                    <TableCell align="right">
                      <Typography fontWeight={700} fontSize="0.95rem" color="success.main">
                        {opp.bookmaker_place_odds.toFixed(2)}
                      </Typography>
                    </TableCell>

                    {/* Betfair Win Lay */}
                    <TableCell align="right">
                      <Typography fontWeight={700} fontSize="0.95rem" color="text.primary">
                        {opp.betfair_win_lay_odds.toFixed(2)}
                      </Typography>
                    </TableCell>

                    {/* Betfair Place Lay */}
                    <TableCell align="right">
                      <Typography fontWeight={700} fontSize="0.95rem" color="text.primary">
                        {opp.betfair_place_lay_odds.toFixed(2)}
                      </Typography>
                    </TableCell>

                    {/* Win Edge */}
                    <TableCell align="right">
                      <Chip
                        label={formatEdge(opp.win_edge)}
                        size="small"
                        sx={{
                          bgcolor: opp.win_edge >= 0 ? 'success.main' : 'error.main',
                          color: 'white',
                          fontWeight: 700,
                          fontSize: '0.75rem',
                        }}
                      />
                    </TableCell>

                    {/* Place Edge */}
                    <TableCell align="right">
                      <Chip
                        label={formatEdge(opp.place_edge)}
                        size="small"
                        sx={{
                          bgcolor: opp.place_edge >= 0 ? 'success.main' : 'error.main',
                          color: 'white',
                          fontWeight: 700,
                          fontSize: '0.75rem',
                        }}
                      />
                    </TableCell>

                    {/* Total Edge */}
                    <TableCell align="right">
                      <Chip
                        label={formatEdge(opp.total_edge)}
                        size="small"
                        sx={{
                          bgcolor: 'success.main',
                          color: 'white',
                          fontWeight: 700,
                          fontSize: '0.8rem',
                          boxShadow: '0 2px 4px rgba(16, 185, 129, 0.3)',
                        }}
                      />
                    </TableCell>

                    {/* Profit Scenarios */}
                    <TableCell align="center">
                      <Box sx={{ display: 'flex', gap: 0.5, justifyContent: 'center', flexWrap: 'wrap' }}>
                        <Tooltip title="If horse WINS" arrow>
                          <Chip
                            label={formatCurrency(opp.profit_if_wins)}
                            size="small"
                            sx={{
                              backgroundColor: opp.profit_if_wins >= 0 ? '#10b981' : '#ef4444',
                              color: 'white',
                              fontWeight: 700,
                              fontSize: '0.7rem',
                              boxShadow: opp.profit_if_wins >= 0
                                ? '0 2px 4px rgba(16, 185, 129, 0.4)'
                                : '0 2px 4px rgba(239, 68, 68, 0.4)',
                              border: '1px solid rgba(255, 255, 255, 0.2)',
                            }}
                          />
                        </Tooltip>
                        <Tooltip title="If horse PLACES" arrow>
                          <Chip
                            label={formatCurrency(opp.profit_if_places)}
                            size="small"
                            sx={{
                              backgroundColor: opp.profit_if_places >= 0 ? '#10b981' : '#ef4444',
                              color: 'white',
                              fontWeight: 700,
                              fontSize: '0.7rem',
                              boxShadow: opp.profit_if_places >= 0
                                ? '0 2px 4px rgba(16, 185, 129, 0.4)'
                                : '0 2px 4px rgba(239, 68, 68, 0.4)',
                              border: '1px solid rgba(255, 255, 255, 0.2)',
                            }}
                          />
                        </Tooltip>
                        <Tooltip title="If horse LOSES" arrow>
                          <Chip
                            label={formatCurrency(opp.profit_if_loses)}
                            size="small"
                            sx={{
                              backgroundColor: opp.profit_if_loses >= 0 ? '#10b981' : '#ef4444',
                              color: 'white',
                              fontWeight: 700,
                              fontSize: '0.7rem',
                              boxShadow: opp.profit_if_loses >= 0
                                ? '0 2px 4px rgba(16, 185, 129, 0.4)'
                                : '0 2px 4px rgba(239, 68, 68, 0.4)',
                              border: '1px solid rgba(255, 255, 255, 0.2)',
                            }}
                          />
                        </Tooltip>
                      </Box>
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        sx={{ mt: 0.5, fontWeight: 500, fontSize: '0.65rem' }}
                      >
                        Win | Place | Lose
                      </Typography>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>

          {lastFetch && (
            <Box
              sx={{
                mt: 2,
                p: 2,
                borderRadius: 2,
                bgcolor: 'rgba(100, 116, 139, 0.05)',
                border: '1px solid rgba(100, 116, 139, 0.1)',
              }}
            >
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{ fontWeight: 500, display: 'flex', alignItems: 'center', gap: 1 }}
              >
                <Box
                  sx={{
                    width: 6,
                    height: 6,
                    borderRadius: '50%',
                    bgcolor: 'success.main',
                    animation: 'pulse 2s ease-in-out infinite',
                  }}
                />
                Last updated: {lastFetch.toLocaleTimeString()}
              </Typography>
            </Box>
          )}
        </>
      )}
    </Box>
  )
}
