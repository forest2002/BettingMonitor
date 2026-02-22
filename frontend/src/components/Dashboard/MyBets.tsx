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
  ToggleButton,
  ToggleButtonGroup,
} from '@mui/material'
import { useBetsStore } from '../../stores/betsStore'

export const MyBets = () => {
  const {
    currentOrders,
    clearedOrders,
    totalProfit,
    isLoading,
    error,
    fetchCurrentOrders,
    fetchClearedOrders,
  } = useBetsStore()

  const [view, setView] = useState<'open' | 'settled'>('open')

  useEffect(() => {
    if (view === 'open') {
      fetchCurrentOrders()
    } else {
      fetchClearedOrders()
    }
  }, [view])

  const handleViewChange = (
    _: React.MouseEvent<HTMLElement>,
    newView: 'open' | 'settled' | null
  ) => {
    if (newView) setView(newView)
  }

  const sortedCurrentOrders = [...currentOrders].sort((a, b) => {
    if (!a.scheduledTime || !b.scheduledTime) return 0
    return new Date(a.scheduledTime).getTime() - new Date(b.scheduledTime).getTime()
  })

  const formatDate = (dateStr: string) => {
    if (!dateStr) return '-'
    const d = new Date(dateStr)
    return d.toLocaleString('en-GB', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const formatCurrency = (val: number) =>
    `£${val.toFixed(2)}`

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'center', mb: 3 }}>
        <ToggleButtonGroup
          value={view}
          exclusive
          onChange={handleViewChange}
          size="small"
          sx={{
            '& .MuiToggleButton-root': {
              textTransform: 'none',
              fontWeight: 600,
              px: 3,
              '&.Mui-selected': {
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                color: '#fff',
                '&:hover': {
                  background: 'linear-gradient(135deg, #5a6fd6 0%, #6a4296 100%)',
                },
              },
            },
          }}
        >
          <ToggleButton value="open">Open Bets</ToggleButton>
          <ToggleButton value="settled">Settled</ToggleButton>
        </ToggleButtonGroup>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {isLoading && currentOrders.length === 0 && clearedOrders.length === 0 && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress />
        </Box>
      )}

      {view === 'open' && <OpenBetsTable orders={sortedCurrentOrders} formatDate={formatDate} formatCurrency={formatCurrency} />}
      {view === 'settled' && (
        <SettledBetsTable
          orders={clearedOrders}
          totalProfit={totalProfit}
          formatDate={formatDate}
          formatCurrency={formatCurrency}
        />
      )}
    </Box>
  )
}

const headerSx = {
  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  '& .MuiTableCell-head': {
    color: '#fff',
    fontWeight: 700,
    fontSize: '0.75rem',
    textTransform: 'uppercase' as const,
    letterSpacing: 0.5,
    whiteSpace: 'nowrap' as const,
    py: 1.5,
  },
}

const rowHoverSx = {
  transition: 'all 0.2s ease',
  '&:hover': {
    bgcolor: 'rgba(102, 126, 234, 0.04)',
    transform: 'scale(1.005)',
  },
}

interface OpenBetsTableProps {
  orders: ReturnType<typeof useBetsStore.getState>['currentOrders']
  formatDate: (s: string) => string
  formatCurrency: (n: number) => string
}

const OpenBetsTable = ({ orders, formatDate, formatCurrency }: OpenBetsTableProps) => {
  const filteredOrders = orders.filter((order) => (order.sizeMatched || 0) >= 0.02)

  if (filteredOrders.length === 0) {
    return (
      <Alert severity="info">No open bets found.</Alert>
    )
  }

  return (
    <TableContainer component={Paper} elevation={2} sx={{ borderRadius: 2 }}>
      <Table size="small">
        <TableHead>
          <TableRow sx={headerSx}>
            <TableCell>Event</TableCell>
            <TableCell>Selection</TableCell>
            <TableCell align="center">Side</TableCell>
            <TableCell align="right">Price</TableCell>
            <TableCell align="right">Stake</TableCell>
            <TableCell align="right">Matched</TableCell>
            <TableCell align="center">Status</TableCell>
            <TableCell>Time</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {filteredOrders.map((order) => (
            <TableRow key={order.betId} sx={rowHoverSx}>
              <TableCell sx={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                <Typography variant="body2" fontWeight={600}>
                  {order.eventName || order.marketId}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {order.marketName}
                </Typography>
              </TableCell>
              <TableCell>
                <Typography variant="body2" fontWeight={500}>
                  {order.runnerName || order.selectionId}
                </Typography>
              </TableCell>
              <TableCell align="center">
                <Chip
                  label={order.side}
                  size="small"
                  sx={{
                    fontWeight: 700,
                    bgcolor: order.side === 'BACK' ? '#e3f2fd' : '#fce4ec',
                    color: order.side === 'BACK' ? '#1565c0' : '#c62828',
                  }}
                />
              </TableCell>
              <TableCell align="right">
                <Typography variant="body2" fontWeight={600}>
                  {order.price?.toFixed(2) ?? '-'}
                </Typography>
              </TableCell>
              <TableCell align="right">
                {formatCurrency(order.size || 0)}
                {order.isEachWay && (
                  <Chip
                    label="EW"
                    size="small"
                    sx={{
                      ml: 0.5,
                      height: 18,
                      fontSize: '0.65rem',
                      fontWeight: 700,
                      bgcolor: '#fff3e0',
                      color: '#e65100',
                    }}
                  />
                )}
              </TableCell>
              <TableCell align="right">{formatCurrency(order.sizeMatched || 0)}</TableCell>
              <TableCell align="center">
                <Chip
                  label={order.status || 'OPEN'}
                  size="small"
                  color={
                    order.sizeRemaining === 0
                      ? 'success'
                      : order.sizeMatched > 0
                        ? 'warning'
                        : 'default'
                  }
                  variant="outlined"
                  sx={{ fontWeight: 600, fontSize: '0.7rem' }}
                />
              </TableCell>
              <TableCell>
                <Typography variant="caption">
                  {formatDate(order.scheduledTime || order.placedDate)}
                </Typography>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  )
}

interface SettledBetsTableProps {
  orders: ReturnType<typeof useBetsStore.getState>['clearedOrders']
  totalProfit: number
  formatDate: (s: string) => string
  formatCurrency: (n: number) => string
}

const SettledBetsTable = ({ orders, totalProfit, formatDate, formatCurrency }: SettledBetsTableProps) => {
  const profitColor = totalProfit >= 0 ? '#4caf50' : '#f44336'

  return (
    <>
      <Card
        elevation={3}
        sx={{
          mb: 3,
          borderRadius: 2,
          borderLeft: `4px solid ${profitColor}`,
        }}
      >
        <CardContent sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', py: 2, '&:last-child': { pb: 2 } }}>
          <Typography variant="subtitle1" fontWeight={600}>
            Today's P/L
          </Typography>
          <Typography
            variant="h5"
            fontWeight={800}
            sx={{ color: profitColor }}
          >
            {totalProfit >= 0 ? '+' : ''}{formatCurrency(totalProfit)}
          </Typography>
        </CardContent>
      </Card>

      {orders.length === 0 ? (
        <Alert severity="info">No settled bets found for today.</Alert>
      ) : (
        <TableContainer component={Paper} elevation={2} sx={{ borderRadius: 2 }}>
          <Table size="small">
            <TableHead>
              <TableRow sx={headerSx}>
                <TableCell>Event</TableCell>
                <TableCell>Selection</TableCell>
                <TableCell align="center">Side</TableCell>
                <TableCell align="right">Price</TableCell>
                <TableCell align="right">Settled</TableCell>
                <TableCell align="right">Profit</TableCell>
                <TableCell>Settled Date</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {orders.map((order) => (
                <TableRow key={order.betId} sx={rowHoverSx}>
                  <TableCell sx={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    <Typography variant="body2" fontWeight={600}>
                      {order.eventName || order.marketId}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {order.marketName}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" fontWeight={500}>
                      {order.runnerName || order.selectionId}
                    </Typography>
                  </TableCell>
                  <TableCell align="center">
                    <Chip
                      label={order.side}
                      size="small"
                      sx={{
                        fontWeight: 700,
                        bgcolor: order.side === 'BACK' ? '#e3f2fd' : '#fce4ec',
                        color: order.side === 'BACK' ? '#1565c0' : '#c62828',
                      }}
                    />
                  </TableCell>
                  <TableCell align="right">
                    <Typography variant="body2" fontWeight={600}>
                      {order.priceMatched?.toFixed(2) ?? '-'}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    {formatCurrency(order.sizeSettled || 0)}
                    {order.isEachWay && (
                      <Chip
                        label="EW"
                        size="small"
                        sx={{
                          ml: 0.5,
                          height: 18,
                          fontSize: '0.65rem',
                          fontWeight: 700,
                          bgcolor: '#fff3e0',
                          color: '#e65100',
                        }}
                      />
                    )}
                  </TableCell>
                  <TableCell align="right">
                    <Chip
                      label={`${order.profit >= 0 ? '+' : ''}${formatCurrency(order.profit)}`}
                      size="small"
                      sx={{
                        fontWeight: 700,
                        bgcolor: order.profit >= 0 ? '#e8f5e9' : '#ffebee',
                        color: order.profit >= 0 ? '#2e7d32' : '#c62828',
                      }}
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption">
                      {formatDate(order.settledDate)}
                    </Typography>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </>
  )
}
