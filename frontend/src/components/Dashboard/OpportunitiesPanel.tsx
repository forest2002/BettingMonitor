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
  ToggleButtonGroup,
  ToggleButton,
  Button,
} from '@mui/material'
import InfoIcon from '@mui/icons-material/Info'
import TrendingUpIcon from '@mui/icons-material/TrendingUp'
import HistoryIcon from '@mui/icons-material/History'
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline'
import RefreshIcon from '@mui/icons-material/Refresh'
import OpenInNewIcon from '@mui/icons-material/OpenInNew'
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown'
import KeyboardArrowUpIcon from '@mui/icons-material/KeyboardArrowUp'
import Collapse from '@mui/material/Collapse'
import { useOpportunitiesStore, Opportunity, HistoricalOpportunity, BookmakerEntry } from '../../stores/opportunitiesStore'

type ViewMode = 'live' | 'history'

export const OpportunitiesPanel = () => {
  const { opportunities, history, isLoading, error, fetchOpportunities, clearHistory, lastFetch } =
    useOpportunitiesStore()
  const [alertedKeys, setAlertedKeys] = useState<Set<string>>(new Set())
  const [viewMode, setViewMode] = useState<ViewMode>('live')
  const [sheetUrl, setSheetUrl] = useState<string | null>(null)

  const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

  useEffect(() => {
    fetchOpportunities(4) // Minimum rating of 5

    // Refresh every 30 seconds
    const interval = setInterval(() => {
      fetchOpportunities(4)
    }, 30000)

    // Fetch Google Sheet URL
    fetch(`${API_BASE_URL}/opportunities/sheet-url`)
      .then(res => res.json())
      .then(data => { if (data.url) setSheetUrl(data.url) })
      .catch(() => {})

    return () => clearInterval(interval)
  }, [])

  // Alert for new high-value opportunities (re-triggers for each new one)
  useEffect(() => {
    const highValueOpps = opportunities.filter((opp) => opp.rating >= 20)
    const newAlerts: string[] = []
    for (const opp of highValueOpps) {
      const key = `${opp.selection_name}:${opp.event_name}`
      if (!alertedKeys.has(key)) {
        newAlerts.push(key)
        if ('Notification' in window && Notification.permission === 'granted') {
          new Notification('High Value Opportunity!', {
            body: `${opp.selection_name} - Rating ${opp.rating}%`,
            icon: '/favicon.ico',
          })
        }
      }
    }
    if (newAlerts.length > 0) {
      setAlertedKeys((prev) => {
        const next = new Set(prev)
        newAlerts.forEach((k) => next.add(k))
        return next
      })
    }
    // Clean up keys for opportunities that no longer exist
    const currentKeys = new Set(
      opportunities.map((opp) => `${opp.selection_name}:${opp.event_name}`)
    )
    setAlertedKeys((prev) => {
      const pruned = new Set([...prev].filter((k) => currentKeys.has(k)))
      if (pruned.size !== prev.size) return pruned
      return prev
    })
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

  const formatRaceInfo = (venue: string | null, scheduledTime: string | null) => {
    if (!venue && !scheduledTime) return null
    const parts: string[] = []
    if (venue) parts.push(venue)
    if (scheduledTime) {
      const d = new Date(scheduledTime)
      parts.push(d.toLocaleString('en-GB', { hour: '2-digit', minute: '2-digit' }))
      parts.push(d.toLocaleString('en-GB', { day: 'numeric', month: 'short' }))
    }
    return parts.join(' - ')
  }

  const formatTime = (iso: string) => {
    const d = new Date(iso)
    return d.toLocaleString('en-GB', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
  }

  const formatDateTime = (iso: string) => {
    const d = new Date(iso)
    return d.toLocaleString('en-GB', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
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

  // Group opportunities by horse (selection + event)
  const groupedOpportunities = opportunities.reduce((acc, opp) => {
    const key = `${opp.selection_name}::${opp.event_name}`
    if (!acc[key]) {
      acc[key] = []
    }
    acc[key].push(opp)
    return acc
  }, {} as Record<string, typeof opportunities>)

  // Sort bookmakers within each group by rating
  Object.values(groupedOpportunities).forEach(group => {
    group.sort((a, b) => b.rating - a.rating)
  })

  const uniqueHorses = Object.keys(groupedOpportunities).length
  const goodOpportunities = opportunities.filter((opp) => opp.rating >= 10)
  const totalEV = opportunities.reduce(
    (sum, opp) => sum + opp.profit_if_wins + opp.profit_if_places + opp.profit_if_loses,
    0
  )

  // Determine which history entries are still live (by selection+event)
  const liveKeys = new Set(
    opportunities.map((opp) => `${opp.selection_name}::${opp.event_name}`)
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
                Horses Found
              </Typography>
              <Typography variant="h3" sx={{ fontWeight: 700, mb: 1 }}>
                {uniqueHorses}
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
                  {opportunities.length} bookmaker opportunities
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

      {/* Live / History Toggle + Refresh */}
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 2, mb: 3 }}>
        <ToggleButtonGroup
          value={viewMode}
          exclusive
          onChange={(_, v) => v && setViewMode(v)}
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
          <ToggleButton value="live">
            <TrendingUpIcon sx={{ mr: 1 }} fontSize="small" />
            Live
          </ToggleButton>
          <ToggleButton value="history">
            <HistoryIcon sx={{ mr: 1 }} fontSize="small" />
            History ({history.length})
          </ToggleButton>
        </ToggleButtonGroup>
        <Tooltip title="Refresh now">
          <IconButton
            onClick={() => fetchOpportunities(4)}
            disabled={isLoading}
            sx={{
              border: '1px solid rgba(100, 116, 139, 0.3)',
              '&:hover': {
                bgcolor: 'rgba(102, 126, 234, 0.1)',
                borderColor: 'primary.main',
              },
            }}
          >
            <RefreshIcon
              fontSize="small"
              sx={{
                animation: isLoading ? 'spin 1s linear infinite' : 'none',
                '@keyframes spin': {
                  '0%': { transform: 'rotate(0deg)' },
                  '100%': { transform: 'rotate(360deg)' },
                },
              }}
            />
          </IconButton>
        </Tooltip>
        {sheetUrl && (
          <Button
            variant="outlined"
            size="small"
            href={sheetUrl}
            target="_blank"
            rel="noopener noreferrer"
            startIcon={<OpenInNewIcon />}
            sx={{
              textTransform: 'none',
              fontWeight: 600,
              borderColor: '#4caf50',
              color: '#4caf50',
              '&:hover': {
                borderColor: '#388e3c',
                bgcolor: 'rgba(76, 175, 80, 0.08)',
              },
            }}
          >
            Google Sheet
          </Button>
        )}
      </Box>

      {viewMode === 'live' && <LiveOpportunities
        groupedOpportunities={groupedOpportunities}
        lastFetch={lastFetch}
        headerCellSx={headerCellSx}
        getRatingColor={getRatingColor}
        getRatingLabel={getRatingLabel}
        formatCurrency={formatCurrency}
        formatEdge={formatEdge}
        formatRaceInfo={formatRaceInfo}
      />}

      {viewMode === 'history' && <HistoryTable
        history={history}
        liveKeys={liveKeys}
        headerCellSx={headerCellSx}
        getRatingColor={getRatingColor}
        getRatingLabel={getRatingLabel}
        formatCurrency={formatCurrency}
        formatEdge={formatEdge}
        formatTime={formatTime}
        formatDateTime={formatDateTime}
        formatRaceInfo={formatRaceInfo}
        onClear={clearHistory}
      />}
    </Box>
  )
}

/* ─── Live Opportunities Table ─── */

interface LiveProps {
  groupedOpportunities: Record<string, Opportunity[]>
  lastFetch: Date | null
  headerCellSx: Record<string, any>
  getRatingColor: (r: number) => string
  getRatingLabel: (r: number) => string
  formatCurrency: (v: number) => string
  formatEdge: (v: number) => string
  formatRaceInfo: (venue: string | null, scheduledTime: string | null) => string | null
}

const LiveOpportunities = ({
  groupedOpportunities, lastFetch, headerCellSx,
  getRatingColor, getRatingLabel, formatCurrency, formatEdge, formatRaceInfo,
}: LiveProps) => {
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set())

  const toggleRow = (key: string) => {
    setExpandedRows(prev => {
      const next = new Set(prev)
      if (next.has(key)) {
        next.delete(key)
      } else {
        next.add(key)
      }
      return next
    })
  }

  if (Object.keys(groupedOpportunities).length === 0) {
    return (
      <Alert
        severity="info"
        icon={<TrendingUpIcon />}
        sx={{
          borderRadius: 2,
          border: '1px solid rgba(59, 130, 246, 0.3)',
          bgcolor: 'rgba(59, 130, 246, 0.05)',
          '& .MuiAlert-icon': { color: 'primary.main' },
        }}
      >
        No each-way profit maximiser opportunities found at the moment. The system is monitoring odds continuously.
      </Alert>
    )
  }

  const totalOpportunities = Object.values(groupedOpportunities).reduce((sum, group) => sum + group.length, 0)

  return (
    <>
      <Alert
        severity="success"
        sx={{
          mb: 3, borderRadius: 2,
          border: '1px solid rgba(16, 185, 129, 0.3)',
          bgcolor: 'rgba(16, 185, 129, 0.05)',
          '& .MuiAlert-icon': { color: 'success.main' },
        }}
      >
        <strong>{Object.keys(groupedOpportunities).length} horses found!</strong> All shown opportunities are profitable (profit &gt;= 0) in every scenario (win, place, lose).
      </Alert>

      <TableContainer
        component={Paper}
        sx={{
          borderRadius: 3, overflow: 'auto',
          boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.2), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
        }}
      >
        <Table size="small">
          <TableHead>
            <TableRow sx={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', '& .MuiTableCell-root': { borderBottom: 'none' } }}>
              <TableCell sx={headerCellSx} style={{ width: '40px' }}></TableCell>
              <TableCell sx={headerCellSx}>RATING</TableCell>
              <TableCell sx={headerCellSx}>HORSE</TableCell>
              <TableCell sx={headerCellSx}>RACE</TableCell>
              <TableCell sx={headerCellSx}>BOOKMAKERS</TableCell>
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
            {Object.entries(groupedOpportunities).map(([key, group]) => (
              <GroupedOpportunityRow
                key={key}
                rowKey={key}
                group={group}
                isExpanded={expandedRows.has(key)}
                onToggle={() => toggleRow(key)}
                getRatingColor={getRatingColor}
                getRatingLabel={getRatingLabel}
                formatCurrency={formatCurrency}
                formatEdge={formatEdge}
                formatRaceInfo={formatRaceInfo}
              />
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      {lastFetch && (
        <Box sx={{ mt: 2, p: 2, borderRadius: 2, bgcolor: 'rgba(100, 116, 139, 0.05)', border: '1px solid rgba(100, 116, 139, 0.1)' }}>
          <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 500, display: 'flex', alignItems: 'center', gap: 1 }}>
            <Box sx={{ width: 6, height: 6, borderRadius: '50%', bgcolor: 'success.main', animation: 'pulse 2s ease-in-out infinite' }} />
            Last updated: {lastFetch.toLocaleTimeString()}
          </Typography>
        </Box>
      )}
    </>
  )
}

/* ─── Grouped Opportunity Row (Expandable) ─── */

interface GroupedRowProps {
  rowKey: string
  group: Opportunity[]
  isExpanded: boolean
  onToggle: () => void
  getRatingColor: (r: number) => string
  getRatingLabel: (r: number) => string
  formatCurrency: (v: number) => string
  formatEdge: (v: number) => string
  formatRaceInfo: (venue: string | null, scheduledTime: string | null) => string | null
}

const GroupedOpportunityRow = ({ rowKey, group, isExpanded, onToggle, getRatingColor, getRatingLabel, formatCurrency, formatEdge, formatRaceInfo }: GroupedRowProps) => {
  const best = group[0] // Already sorted by rating
  const hasMultiple = group.length > 1

  return (
    <>
      {/* Main collapsed row showing best bookmaker */}
      <TableRow
        sx={{
          backgroundColor: best.rating >= 20 ? 'rgba(16, 185, 129, 0.08)' : best.rating >= 10 ? 'rgba(245, 158, 11, 0.08)' : 'inherit',
          borderLeft: best.rating >= 20 ? '4px solid #10b981' : best.rating >= 10 ? '4px solid #f59e0b' : '4px solid transparent',
          transition: 'all 0.3s ease',
          '&:hover': {
            backgroundColor: best.rating >= 20 ? 'rgba(16, 185, 129, 0.15)' : best.rating >= 10 ? 'rgba(245, 158, 11, 0.15)' : 'rgba(100, 116, 139, 0.1)',
            cursor: hasMultiple ? 'pointer' : 'default',
          },
        }}
        onClick={hasMultiple ? onToggle : undefined}
      >
        <TableCell sx={{ width: '40px' }}>
          {hasMultiple && (
            <IconButton size="small" onClick={(e) => { e.stopPropagation(); onToggle(); }}>
              {isExpanded ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
            </IconButton>
          )}
        </TableCell>
        <TableCell>
          <Chip label={`${best.rating}% ${getRatingLabel(best.rating)}`} sx={{ backgroundColor: getRatingColor(best.rating), color: 'white', fontWeight: 700, fontSize: '0.75rem', letterSpacing: '0.02em', boxShadow: '0 2px 4px rgba(0, 0, 0, 0.2)', border: '1px solid rgba(255, 255, 255, 0.2)' }} />
        </TableCell>
        <TableCell><Typography fontWeight={700} fontSize="0.9rem" color="text.primary">{best.selection_name}</Typography></TableCell>
        <TableCell><Typography variant="body2" color="text.secondary" fontWeight={500}>{formatRaceInfo(best.venue, best.scheduled_time) || best.event_name}</Typography></TableCell>
        <TableCell>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
            <Typography variant="body2" fontWeight={600} color="text.primary">
              {best.bookmaker} {best.bookmaker_win_odds.toFixed(1)}
            </Typography>
            {best.is_fair_odds && <Chip label="FO" size="small" variant="outlined" sx={{ color: '#f59e0b', borderColor: '#f59e0b', fontWeight: 700, fontSize: '0.65rem', height: 20 }} />}
            {hasMultiple && <Chip label={`+${group.length - 1} more`} size="small" sx={{ height: 20, fontSize: '0.7rem', bgcolor: 'rgba(102, 126, 234, 0.15)', color: 'primary.light', fontWeight: 600 }} />}
          </Box>
        </TableCell>
        <TableCell align="center">
          <Box sx={{ display: 'flex', gap: 0.5, justifyContent: 'center', flexWrap: 'wrap' }}>
            <Tooltip title="If horse WINS" arrow><Chip label={formatCurrency(best.profit_if_wins)} size="small" sx={{ backgroundColor: best.profit_if_wins >= 0 ? '#10b981' : '#ef4444', color: 'white', fontWeight: 700, fontSize: '0.7rem', boxShadow: best.profit_if_wins >= 0 ? '0 2px 4px rgba(16, 185, 129, 0.4)' : '0 2px 4px rgba(239, 68, 68, 0.4)', border: '1px solid rgba(255, 255, 255, 0.2)' }} /></Tooltip>
            <Tooltip title="If horse PLACES" arrow><Chip label={formatCurrency(best.profit_if_places)} size="small" sx={{ backgroundColor: best.profit_if_places >= 0 ? '#10b981' : '#ef4444', color: 'white', fontWeight: 700, fontSize: '0.7rem', boxShadow: best.profit_if_places >= 0 ? '0 2px 4px rgba(16, 185, 129, 0.4)' : '0 2px 4px rgba(239, 68, 68, 0.4)', border: '1px solid rgba(255, 255, 255, 0.2)' }} /></Tooltip>
            <Tooltip title="If horse LOSES" arrow><Chip label={formatCurrency(best.profit_if_loses)} size="small" sx={{ backgroundColor: best.profit_if_loses >= 0 ? '#10b981' : '#ef4444', color: 'white', fontWeight: 700, fontSize: '0.7rem', boxShadow: best.profit_if_loses >= 0 ? '0 2px 4px rgba(16, 185, 129, 0.4)' : '0 2px 4px rgba(239, 68, 68, 0.4)', border: '1px solid rgba(255, 255, 255, 0.2)' }} /></Tooltip>
          </Box>
        </TableCell>
      </TableRow>

      {/* Expanded rows showing other bookmakers */}
      {hasMultiple && isExpanded && group.slice(1).map((opp, idx) => (
        <TableRow key={idx} sx={{ backgroundColor: 'rgba(100, 116, 139, 0.03)' }}>
          <TableCell />
          <TableCell>
            <Chip label={`${opp.rating}%`} size="small" sx={{ backgroundColor: getRatingColor(opp.rating), color: 'white', fontWeight: 700, fontSize: '0.7rem' }} />
          </TableCell>
          <TableCell colSpan={2}></TableCell>
          <TableCell>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography variant="body2" fontWeight={600} color="text.secondary">
                {opp.bookmaker} {opp.bookmaker_win_odds.toFixed(1)}
              </Typography>
              {opp.is_fair_odds && <Chip label="FO" size="small" variant="outlined" sx={{ color: '#f59e0b', borderColor: '#f59e0b', fontWeight: 700, fontSize: '0.65rem', height: 20 }} />}
            </Box>
          </TableCell>
          <TableCell align="center">
            <Box sx={{ display: 'flex', gap: 0.5, justifyContent: 'center', flexWrap: 'wrap' }}>
              <Chip label={formatCurrency(opp.profit_if_wins)} size="small" sx={{ backgroundColor: opp.profit_if_wins >= 0 ? '#10b981' : '#ef4444', color: 'white', fontWeight: 600, fontSize: '0.65rem' }} />
              <Chip label={formatCurrency(opp.profit_if_places)} size="small" sx={{ backgroundColor: opp.profit_if_places >= 0 ? '#10b981' : '#ef4444', color: 'white', fontWeight: 600, fontSize: '0.65rem' }} />
              <Chip label={formatCurrency(opp.profit_if_loses)} size="small" sx={{ backgroundColor: opp.profit_if_loses >= 0 ? '#10b981' : '#ef4444', color: 'white', fontWeight: 600, fontSize: '0.65rem' }} />
            </Box>
          </TableCell>
        </TableRow>
      ))}
    </>
  )
}

/* ─── Shared Opportunity Row ─── */

interface RowProps {
  opp: Opportunity
  getRatingColor: (r: number) => string
  getRatingLabel: (r: number) => string
  formatCurrency: (v: number) => string
  formatEdge: (v: number) => string
  formatRaceInfo: (venue: string | null, scheduledTime: string | null) => string | null
}

const OpportunityRow = ({ opp, getRatingColor, getRatingLabel, formatCurrency, formatEdge, formatRaceInfo }: RowProps) => (
  <TableRow
    sx={{
      backgroundColor: opp.rating >= 20 ? 'rgba(16, 185, 129, 0.08)' : opp.rating >= 10 ? 'rgba(245, 158, 11, 0.08)' : 'inherit',
      borderLeft: opp.rating >= 20 ? '4px solid #10b981' : opp.rating >= 10 ? '4px solid #f59e0b' : '4px solid transparent',
      transition: 'all 0.3s ease',
      '&:hover': {
        backgroundColor: opp.rating >= 20 ? 'rgba(16, 185, 129, 0.15)' : opp.rating >= 10 ? 'rgba(245, 158, 11, 0.15)' : 'rgba(100, 116, 139, 0.1)',
        transform: 'scale(1.01)',
        boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.2)',
      },
    }}
  >
    <TableCell>
      <Chip label={`${opp.rating}% ${getRatingLabel(opp.rating)}`} sx={{ backgroundColor: getRatingColor(opp.rating), color: 'white', fontWeight: 700, fontSize: '0.75rem', letterSpacing: '0.02em', boxShadow: '0 2px 4px rgba(0, 0, 0, 0.2)', border: '1px solid rgba(255, 255, 255, 0.2)' }} />
    </TableCell>
    <TableCell><Typography fontWeight={700} fontSize="0.9rem" color="text.primary">{opp.selection_name}</Typography></TableCell>
    <TableCell><Typography variant="body2" color="text.secondary" fontWeight={500}>{formatRaceInfo(opp.venue, opp.scheduled_time) || opp.event_name}</Typography></TableCell>
    <TableCell>
      <Box sx={{ display: 'flex', alignItems: 'center' }}>
        <Typography variant="body2" fontWeight={600} color="text.primary">{opp.bookmaker}</Typography>
        {opp.is_fair_odds && <Chip label="FO" size="small" variant="outlined" sx={{ color: '#f59e0b', borderColor: '#f59e0b', fontWeight: 700, fontSize: '0.65rem', height: 20, ml: 0.5 }} />}
      </Box>
      <Chip label={`${opp.num_places} places`} size="small" sx={{ height: 20, fontSize: '0.7rem', mt: 0.5, bgcolor: 'rgba(102, 126, 234, 0.15)', color: 'primary.light', fontWeight: 600 }} />
    </TableCell>
    <TableCell align="right"><Typography fontWeight={700} fontSize="0.95rem" color="text.primary">{opp.bookmaker_win_odds.toFixed(2)}</Typography></TableCell>
    <TableCell align="right"><Typography fontWeight={700} fontSize="0.95rem" color="success.main">{opp.bookmaker_place_odds.toFixed(2)}</Typography></TableCell>
    <TableCell align="right"><Typography fontWeight={700} fontSize="0.95rem" color="text.primary">{opp.betfair_win_lay_odds.toFixed(2)}</Typography></TableCell>
    <TableCell align="right"><Typography fontWeight={700} fontSize="0.95rem" color="text.primary">{opp.betfair_place_lay_odds.toFixed(2)}</Typography></TableCell>
    <TableCell align="right"><Chip label={formatEdge(opp.win_edge)} size="small" sx={{ bgcolor: opp.win_edge >= 0 ? 'success.main' : 'error.main', color: 'white', fontWeight: 700, fontSize: '0.75rem' }} /></TableCell>
    <TableCell align="right"><Chip label={formatEdge(opp.place_edge)} size="small" sx={{ bgcolor: opp.place_edge >= 0 ? 'success.main' : 'error.main', color: 'white', fontWeight: 700, fontSize: '0.75rem' }} /></TableCell>
    <TableCell align="right"><Chip label={formatEdge(opp.total_edge)} size="small" sx={{ bgcolor: 'success.main', color: 'white', fontWeight: 700, fontSize: '0.8rem', boxShadow: '0 2px 4px rgba(16, 185, 129, 0.3)' }} /></TableCell>
    <TableCell align="center">
      <Box sx={{ display: 'flex', gap: 0.5, justifyContent: 'center', flexWrap: 'wrap' }}>
        <Tooltip title="If horse WINS" arrow><Chip label={formatCurrency(opp.profit_if_wins)} size="small" sx={{ backgroundColor: opp.profit_if_wins >= 0 ? '#10b981' : '#ef4444', color: 'white', fontWeight: 700, fontSize: '0.7rem', boxShadow: opp.profit_if_wins >= 0 ? '0 2px 4px rgba(16, 185, 129, 0.4)' : '0 2px 4px rgba(239, 68, 68, 0.4)', border: '1px solid rgba(255, 255, 255, 0.2)' }} /></Tooltip>
        <Tooltip title="If horse PLACES" arrow><Chip label={formatCurrency(opp.profit_if_places)} size="small" sx={{ backgroundColor: opp.profit_if_places >= 0 ? '#10b981' : '#ef4444', color: 'white', fontWeight: 700, fontSize: '0.7rem', boxShadow: opp.profit_if_places >= 0 ? '0 2px 4px rgba(16, 185, 129, 0.4)' : '0 2px 4px rgba(239, 68, 68, 0.4)', border: '1px solid rgba(255, 255, 255, 0.2)' }} /></Tooltip>
        <Tooltip title="If horse LOSES" arrow><Chip label={formatCurrency(opp.profit_if_loses)} size="small" sx={{ backgroundColor: opp.profit_if_loses >= 0 ? '#10b981' : '#ef4444', color: 'white', fontWeight: 700, fontSize: '0.7rem', boxShadow: opp.profit_if_loses >= 0 ? '0 2px 4px rgba(16, 185, 129, 0.4)' : '0 2px 4px rgba(239, 68, 68, 0.4)', border: '1px solid rgba(255, 255, 255, 0.2)' }} /></Tooltip>
      </Box>
      <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, fontWeight: 500, fontSize: '0.65rem' }}>
        Win | Place | Lose
      </Typography>
    </TableCell>
  </TableRow>
)

/* ─── History Table ─── */

interface HistoryProps {
  history: HistoricalOpportunity[]
  liveKeys: Set<string>
  headerCellSx: Record<string, any>
  getRatingColor: (r: number) => string
  getRatingLabel: (r: number) => string
  formatCurrency: (v: number) => string
  formatEdge: (v: number) => string
  formatTime: (iso: string) => string
  formatDateTime: (iso: string) => string
  formatRaceInfo: (venue: string | null, scheduledTime: string | null) => string | null
  onClear: () => void
}

const HistoryTable = ({
  history, liveKeys, headerCellSx,
  getRatingColor, getRatingLabel, formatCurrency, formatEdge,
  formatTime, formatDateTime, formatRaceInfo, onClear,
}: HistoryProps) => {
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set())

  const toggleRow = (index: number) => {
    setExpandedRows(prev => {
      const next = new Set(prev)
      if (next.has(index)) {
        next.delete(index)
      } else {
        next.add(index)
      }
      return next
    })
  }

  return (
    <>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="body2" color="text.secondary" fontWeight={500}>
          {history.length} opportunities seen this session
        </Typography>
        <Button
          variant="outlined"
          color="error"
          size="small"
          startIcon={<DeleteOutlineIcon />}
          onClick={onClear}
          disabled={history.length === 0}
          sx={{ textTransform: 'none', fontWeight: 600 }}
        >
          Clear History
        </Button>
      </Box>

      {history.length === 0 ? (
        <Alert severity="info" icon={<HistoryIcon />} sx={{ borderRadius: 2, border: '1px solid rgba(59, 130, 246, 0.3)', bgcolor: 'rgba(59, 130, 246, 0.05)' }}>
          No history yet. Opportunities will be recorded here as they appear and disappear.
        </Alert>
      ) : (
      <TableContainer
        component={Paper}
        sx={{
          borderRadius: 3, overflow: 'auto',
          boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.2), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
        }}
      >
        <Table size="small">
          <TableHead>
            <TableRow sx={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', '& .MuiTableCell-root': { borderBottom: 'none' } }}>
              <TableCell sx={headerCellSx} style={{ width: '40px' }}></TableCell>
              <TableCell sx={headerCellSx}>STATUS</TableCell>
              <TableCell sx={headerCellSx}>FIRST SEEN</TableCell>
              <TableCell sx={headerCellSx}>LAST SEEN</TableCell>
              <TableCell sx={headerCellSx}>BEST RATING</TableCell>
              <TableCell sx={headerCellSx}>HORSE</TableCell>
              <TableCell sx={headerCellSx}>RACE</TableCell>
              <TableCell sx={headerCellSx}>BOOKMAKERS</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {history.map((opp, index) => {
              const key = `${opp.selection_name}::${opp.event_name}`
              const isLive = liveKeys.has(key)

              const isExpanded = expandedRows.has(index)

              return (
                <>
                  <TableRow
                    key={index}
                    sx={{
                      opacity: isLive ? 1 : 0.7,
                      backgroundColor: isLive
                        ? 'rgba(16, 185, 129, 0.06)'
                        : 'inherit',
                      transition: 'all 0.3s ease',
                      '&:hover': {
                        backgroundColor: 'rgba(100, 116, 139, 0.1)',
                        cursor: 'pointer',
                      },
                    }}
                    onClick={() => toggleRow(index)}
                  >
                    <TableCell sx={{ width: '40px' }}>
                      <IconButton size="small" onClick={(e) => { e.stopPropagation(); toggleRow(index); }}>
                        {isExpanded ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
                      </IconButton>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={isLive ? 'LIVE' : 'EXPIRED'}
                        size="small"
                        sx={{
                          fontWeight: 700,
                          fontSize: '0.7rem',
                          bgcolor: isLive ? '#10b981' : '#9e9e9e',
                          color: 'white',
                        }}
                      />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" fontWeight={500} fontSize="0.85rem">
                        {formatDateTime(opp.firstSeen)}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" fontWeight={500} fontSize="0.85rem">
                        {formatDateTime(opp.lastSeen)}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={`${opp.bestRating}% ${getRatingLabel(opp.bestRating)}`}
                        sx={{
                          backgroundColor: getRatingColor(opp.bestRating),
                          color: 'white',
                          fontWeight: 700,
                          fontSize: '0.75rem',
                          boxShadow: '0 2px 4px rgba(0, 0, 0, 0.2)',
                          border: '1px solid rgba(255, 255, 255, 0.2)',
                        }}
                      />
                    </TableCell>
                    <TableCell><Typography fontWeight={700} fontSize="0.9rem" color="text.primary">{opp.selection_name}</Typography></TableCell>
                    <TableCell><Typography variant="body2" color="text.secondary" fontWeight={500}>{formatRaceInfo(opp.venue, opp.scheduled_time) || opp.event_name}</Typography></TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', alignItems: 'center' }}>
                        {opp.bookmakers.slice(0, 3).map((bm, idx) => (
                          <Chip
                            key={idx}
                            label={bm.bookmaker}
                            size="small"
                            sx={{
                              fontSize: '0.7rem',
                              height: 20,
                              bgcolor: idx === 0 ? 'rgba(102, 126, 234, 0.15)' : 'rgba(100, 116, 139, 0.1)',
                              fontWeight: idx === 0 ? 600 : 500,
                            }}
                          />
                        ))}
                        {opp.bookmakers.length > 3 && (
                          <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
                            +{opp.bookmakers.length - 3} more
                          </Typography>
                        )}
                      </Box>
                    </TableCell>
                  </TableRow>

                  {/* Expanded bookmaker details */}
                  {isExpanded && (
                    <TableRow>
                      <TableCell colSpan={8} sx={{ py: 0, bgcolor: 'rgba(100, 116, 139, 0.02)' }}>
                        <Collapse in={isExpanded}>
                          <Box sx={{ p: 2 }}>
                            <Typography variant="body2" fontWeight={600} sx={{ mb: 1.5 }}>
                              Bookmaker Details ({opp.bookmakers.length})
                            </Typography>
                            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                              {opp.bookmakers.map((bm, bmIdx) => (
                                <BookmakerHistoryRow
                                  key={bmIdx}
                                  bm={bm}
                                  isFirst={bmIdx === 0}
                                  getRatingColor={getRatingColor}
                                  getRatingLabel={getRatingLabel}
                                  formatCurrency={formatCurrency}
                                  formatEdge={formatEdge}
                                />
                              ))}
                            </Box>
                          </Box>
                        </Collapse>
                      </TableCell>
                    </TableRow>
                  )}
                </>
              )
            })}
          </TableBody>
        </Table>
      </TableContainer>
      )}
    </>
  )
}

/* ─── Bookmaker row within a history entry ─── */

interface BookmakerHistoryRowProps {
  bm: BookmakerEntry
  isFirst: boolean
  getRatingColor: (r: number) => string
  getRatingLabel: (r: number) => string
  formatCurrency: (v: number) => string
  formatEdge: (v: number) => string
}

const BookmakerHistoryRow = ({ bm, isFirst, getRatingColor, getRatingLabel, formatCurrency, formatEdge }: BookmakerHistoryRowProps) => (
  <Box
    sx={{
      display: 'flex',
      flexDirection: 'column',
      gap: 0.5,
      p: 1,
      borderRadius: 1,
      bgcolor: isFirst ? 'rgba(102, 126, 234, 0.06)' : 'rgba(100, 116, 139, 0.04)',
      border: isFirst ? '1px solid rgba(102, 126, 234, 0.15)' : '1px solid rgba(100, 116, 139, 0.1)',
    }}
  >
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
      <Typography variant="body2" fontWeight={700} fontSize="0.85rem" sx={{ minWidth: 80 }}>{bm.bookmaker}</Typography>
      {bm.is_fair_odds && <Chip label="FO" size="small" variant="outlined" sx={{ color: '#f59e0b', borderColor: '#f59e0b', fontWeight: 700, fontSize: '0.65rem', height: 20 }} />}
      <Chip label={`${bm.rating}%`} size="small" sx={{ backgroundColor: getRatingColor(bm.rating), color: 'white', fontWeight: 700, fontSize: '0.7rem', height: 20 }} />
      <Chip label={`${bm.num_places} places`} size="small" sx={{ height: 20, fontSize: '0.65rem', bgcolor: 'rgba(102, 126, 234, 0.15)', color: 'primary.light', fontWeight: 600 }} />
    </Box>
    <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', alignItems: 'center' }}>
      <Typography variant="caption" color="text.secondary" fontWeight={500}>
        Win: {bm.bookmaker_win_odds.toFixed(2)} / Lay: {bm.betfair_win_lay_odds.toFixed(2)}
      </Typography>
      <Typography variant="caption" color="text.secondary" fontWeight={500}>
        Place: {bm.bookmaker_place_odds.toFixed(2)} / Lay: {bm.betfair_place_lay_odds.toFixed(2)}
      </Typography>
      <Typography variant="caption" color="text.secondary" fontWeight={500}>
        Edge: {formatEdge(bm.total_edge)}
      </Typography>
    </Box>
    <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
      <Tooltip title="If horse WINS" arrow><Chip label={formatCurrency(bm.profit_if_wins)} size="small" sx={{ backgroundColor: bm.profit_if_wins >= 0 ? '#10b981' : '#ef4444', color: 'white', fontWeight: 700, fontSize: '0.65rem', height: 20, border: '1px solid rgba(255, 255, 255, 0.2)' }} /></Tooltip>
      <Tooltip title="If horse PLACES" arrow><Chip label={formatCurrency(bm.profit_if_places)} size="small" sx={{ backgroundColor: bm.profit_if_places >= 0 ? '#10b981' : '#ef4444', color: 'white', fontWeight: 700, fontSize: '0.65rem', height: 20, border: '1px solid rgba(255, 255, 255, 0.2)' }} /></Tooltip>
      <Tooltip title="If horse LOSES" arrow><Chip label={formatCurrency(bm.profit_if_loses)} size="small" sx={{ backgroundColor: bm.profit_if_loses >= 0 ? '#10b981' : '#ef4444', color: 'white', fontWeight: 700, fontSize: '0.65rem', height: 20, border: '1px solid rgba(255, 255, 255, 0.2)' }} /></Tooltip>
      <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.6rem', alignSelf: 'center' }}>W | P | L</Typography>
    </Box>
  </Box>
)
