import { useState, useMemo, useCallback } from 'react'
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Box,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  ToggleButtonGroup,
  ToggleButton,
} from '@mui/material'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import ViewListIcon from '@mui/icons-material/ViewList'
import ViewModuleIcon from '@mui/icons-material/ViewModule'
import { useOddsStore } from '../../stores/oddsStore'
import { Event, Odds } from '../../types'

type ViewMode = 'list' | 'venue'

const formatTimeOnly = (dateString: string) => {
  const date = new Date(dateString)
  return date.toLocaleString('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
  })
}

const getOddsForSelection = (oddsMap: Record<number, Odds[]>, eventId: number, selectionId: number) => {
  const eventOdds = oddsMap[eventId] || []
  return eventOdds.filter((odds) => odds.selection_id === selectionId)
}

const getOddsByBookmaker = (odds: Odds[]) => {
  const map: Record<string, Odds> = {}
  for (const o of odds) {
    map[o.bookmaker_name] = o
  }
  return map
}

const SelectionsTable = ({ event, oddsMap }: { event: Event; oddsMap: Record<number, Odds[]> }) => {
  if (event.selections.length === 0) {
    return (
      <Typography color="text.secondary" fontWeight={500}>
        No selections available
      </Typography>
    )
  }

  // Get all unique bookmakers for this event
  const allOdds = event.selections.flatMap((selection) =>
    getOddsForSelection(oddsMap, event.id, selection.id)
  )
  const bookmakerNames = Array.from(new Set(allOdds.map(o => o.bookmaker_name)))

  // Only show these specific bookmakers in alphabetical order
  const allowedBookmakers = [
    'Betvictor',
    'Coral',
    'Ladbrokes',
    'Paddy Power',
    'Sky Bet'
  ]

  // Filter to only allowed bookmakers that have data
  const sortedBookmakers = allowedBookmakers.filter(bm => bookmakerNames.includes(bm))

  // Get place terms for each bookmaker (should be same for all horses in the race)
  const placeTermsByBookmaker: Record<string, string> = {}
  sortedBookmakers.forEach(bookmaker => {
    const oddsWithTerms = allOdds.find(o => o.bookmaker_name === bookmaker && o.place_terms)
    if (oddsWithTerms?.place_terms) {
      placeTermsByBookmaker[bookmaker] = oddsWithTerms.place_terms
    }
  })

  // Add Betfair Exchange if available (for Back and Lay columns)
  const hasBetfair = bookmakerNames.includes('Betfair Exchange')

  return (
    <TableContainer
      component={Paper}
      variant="outlined"
      sx={{
        borderRadius: 2,
        border: '1px solid rgba(100, 116, 139, 0.2)',
      }}
    >
      <Table size="small">
        <TableHead>
          <TableRow
            sx={{
              bgcolor: 'rgba(100, 116, 139, 0.05)',
            }}
          >
            <TableCell sx={{ fontWeight: 700, fontSize: '0.75rem', textTransform: 'uppercase', minWidth: 150 }}>
              Selection
            </TableCell>
            {sortedBookmakers.map(bookmaker => (
              <TableCell
                key={bookmaker}
                align="center"
                sx={{ fontWeight: 700, fontSize: '0.75rem', textTransform: 'uppercase', minWidth: 90, verticalAlign: 'top' }}
              >
                <Box>
                  <Typography sx={{ fontWeight: 700, fontSize: '0.75rem', textTransform: 'uppercase' }}>
                    {bookmaker}
                  </Typography>
                  {placeTermsByBookmaker[bookmaker] && (
                    <Typography
                      sx={{
                        fontSize: '0.7rem',
                        color: 'text.secondary',
                        fontWeight: 500,
                        mt: 0.25
                      }}
                    >
                      {placeTermsByBookmaker[bookmaker]}
                    </Typography>
                  )}
                </Box>
              </TableCell>
            ))}
            {hasBetfair && (
              <>
                <TableCell align="center" sx={{ fontWeight: 700, fontSize: '0.75rem', textTransform: 'uppercase', minWidth: 90 }}>
                  Betfair Back
                </TableCell>
                <TableCell align="center" sx={{ fontWeight: 700, fontSize: '0.75rem', textTransform: 'uppercase', minWidth: 90 }}>
                  Betfair Lay
                </TableCell>
              </>
            )}
          </TableRow>
        </TableHead>
        <TableBody>
          {event.selections
            .sort((a, b) => {
              // Sort by Betfair Exchange back price (lowest to highest)
              const oddsA = getOddsForSelection(oddsMap, event.id, a.id)
              const oddsB = getOddsForSelection(oddsMap, event.id, b.id)
              const betfairA = getOddsByBookmaker(oddsA)['Betfair Exchange']
              const betfairB = getOddsByBookmaker(oddsB)['Betfair Exchange']

              const priceA = betfairA ? Number(betfairA.odds_decimal) : Infinity
              const priceB = betfairB ? Number(betfairB.odds_decimal) : Infinity

              return priceA - priceB
            })
            .map((selection) => {
            const selectionOdds = getOddsForSelection(oddsMap, event.id, selection.id)
            const byBookmaker = getOddsByBookmaker(selectionOdds)

            // Check if horse is a non-runner (from metadata)
            const isNonRunner = selection.metadata?.status === 'REMOVED' ||
                               selection.metadata?.runner_status === 'REMOVED'

            // Find best price across all displayed bookmakers
            const allPrices = sortedBookmakers
              .map(bm => byBookmaker[bm] ? Number(byBookmaker[bm].odds_decimal) : 0)
            const bestBookmakerPrice = Math.max(...allPrices, 0)

            return (
              <TableRow
                key={selection.id}
                sx={{
                  transition: 'all 0.2s ease',
                  opacity: isNonRunner ? 0.5 : 1,
                  bgcolor: isNonRunner ? 'rgba(0, 0, 0, 0.02)' : 'transparent',
                  '&:hover': {
                    bgcolor: isNonRunner ? 'rgba(0, 0, 0, 0.03)' : 'rgba(100, 116, 139, 0.05)',
                  },
                }}
              >
                <TableCell>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography
                      fontWeight={700}
                      fontSize="0.95rem"
                      color={isNonRunner ? "text.disabled" : "text.primary"}
                      sx={isNonRunner ? { textDecoration: 'line-through' } : {}}
                    >
                      {selection.name}
                    </Typography>
                    {isNonRunner && (
                      <Chip
                        label="Non Runner"
                        size="small"
                        color="error"
                        sx={{
                          height: '20px',
                          fontSize: '0.7rem',
                          fontWeight: 600
                        }}
                      />
                    )}
                  </Box>
                </TableCell>

                {sortedBookmakers.map(bookmaker => {
                  const odds = byBookmaker[bookmaker]
                  const price = odds ? Number(odds.odds_decimal) : 0
                  const isBest = price === bestBookmakerPrice && bestBookmakerPrice > 0 && !isNonRunner

                  return (
                    <TableCell key={bookmaker} align="center">
                      {odds ? (
                        <Typography
                          fontWeight={700}
                          fontSize="0.95rem"
                          color={isNonRunner ? 'text.disabled' : (isBest ? 'success.main' : 'text.primary')}
                          sx={isNonRunner ? { textDecoration: 'line-through' } : {}}
                        >
                          {Number(odds.odds_decimal).toFixed(2)}
                        </Typography>
                      ) : (
                        <Typography color="text.disabled" fontSize="0.85rem">-</Typography>
                      )}
                    </TableCell>
                  )
                })}

                {hasBetfair && (
                  <>
                    <TableCell align="center">
                      {byBookmaker['Betfair Exchange'] ? (
                        <Typography
                          fontWeight={700}
                          fontSize="0.95rem"
                          color={isNonRunner ? 'text.disabled' : 'primary.main'}
                          sx={isNonRunner ? { textDecoration: 'line-through' } : {}}
                        >
                          {Number(byBookmaker['Betfair Exchange'].odds_decimal).toFixed(2)}
                        </Typography>
                      ) : (
                        <Typography color="text.disabled" fontSize="0.85rem">-</Typography>
                      )}
                    </TableCell>
                    <TableCell align="center">
                      {byBookmaker['Betfair Exchange']?.place_odds ? (
                        <Typography
                          fontWeight={700}
                          fontSize="0.95rem"
                          color={isNonRunner ? 'text.disabled' : 'error.main'}
                          sx={isNonRunner ? { textDecoration: 'line-through' } : {}}
                        >
                          {Number(byBookmaker['Betfair Exchange'].place_odds).toFixed(2)}
                        </Typography>
                      ) : (
                        <Typography color="text.disabled" fontSize="0.85rem">-</Typography>
                      )}
                    </TableCell>
                  </>
                )}
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
    </TableContainer>
  )
}

const EventRow = ({
  event,
  oddsMap,
  viewMode,
  defaultCollapsed = false,
}: {
  event: Event
  oddsMap: Record<number, Odds[]>
  viewMode: ViewMode
  defaultCollapsed?: boolean
}) => {
  const hasOdds = oddsMap[event.id] && oddsMap[event.id].length > 0

  return (
    <Accordion
      key={event.id}
      defaultExpanded={defaultCollapsed ? false : hasOdds}
      sx={{
        mb: 2,
        borderRadius: '12px !important',
        overflow: 'hidden',
        border: '1px solid rgba(100, 116, 139, 0.2)',
        '&:before': {
          display: 'none',
        },
        boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
        transition: 'all 0.3s ease',
        '&:hover': {
          boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.2)',
        },
      }}
    >
      <AccordionSummary
        expandIcon={<ExpandMoreIcon />}
        sx={{
          background: 'linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%)',
          '&:hover': {
            background: 'linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%)',
          },
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%', flexWrap: 'wrap' }}>
          <Chip
            label={formatTimeOnly(event.scheduled_time)}
            size="small"
            sx={{
              bgcolor: 'primary.main',
              color: 'white',
              fontWeight: 700,
              fontSize: '0.75rem',
              boxShadow: '0 2px 4px rgba(59, 130, 246, 0.3)',
            }}
          />
          <Typography variant="h6" fontWeight={700} color="text.primary">
            {event.name}
          </Typography>
          {event.venue && viewMode === 'list' && (
            <Chip
              label={event.venue}
              size="small"
              variant="outlined"
              sx={{
                fontWeight: 600,
                borderColor: 'rgba(100, 116, 139, 0.3)',
              }}
            />
          )}
        </Box>
      </AccordionSummary>
      <AccordionDetails sx={{ p: 2 }}>
        <SelectionsTable event={event} oddsMap={oddsMap} />
      </AccordionDetails>
    </Accordion>
  )
}

const VenueGroup = ({
  venue,
  events,
  expandedVenues,
  toggleVenue,
  oddsMap,
  viewMode,
}: {
  venue: string
  events: Event[]
  expandedVenues: Set<string>
  toggleVenue: (venue: string) => void
  oddsMap: Record<number, Odds[]>
  viewMode: ViewMode
}) => {
  const isExpanded = expandedVenues.has(venue)

  return (
    <Box sx={{ mb: 3 }}>
      <Paper
        sx={{
          p: 2,
          mb: 2,
          background: 'linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%)',
          border: '2px solid rgba(102, 126, 234, 0.3)',
          borderRadius: 2,
          cursor: 'pointer',
          transition: 'all 0.2s ease',
          '&:hover': {
            background: 'linear-gradient(135deg, rgba(102, 126, 234, 0.15) 0%, rgba(118, 75, 162, 0.15) 100%)',
            border: '2px solid rgba(102, 126, 234, 0.5)',
          },
        }}
        onClick={() => toggleVenue(venue)}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <ExpandMoreIcon
            sx={{
              transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
              transition: 'transform 0.3s ease',
              color: 'primary.main',
            }}
          />
          <Typography variant="h5" fontWeight={800} color="primary.main">
            {venue}
          </Typography>
          <Chip
            label={`${events.length} race${events.length !== 1 ? 's' : ''}`}
            size="small"
            sx={{
              fontWeight: 600,
              bgcolor: 'rgba(102, 126, 234, 0.2)',
              color: 'primary.main',
            }}
          />
        </Box>
      </Paper>
      {isExpanded && events.map((event) => (
        <EventRow key={event.id} event={event} oddsMap={oddsMap} viewMode={viewMode} defaultCollapsed />
      ))}
    </Box>
  )
}

export const OddsTable = () => {
  // Use selector to only subscribe to events and oddsMap (not lastUpdate)
  // This prevents unnecessary re-renders when lastUpdate changes
  const events = useOddsStore((state) => state.events)
  const oddsMap = useOddsStore((state) => state.oddsMap)
  const [viewMode, setViewMode] = useState<ViewMode>('list')
  const [expandedVenues, setExpandedVenues] = useState<Set<string>>(new Set())

  // Sort events by date first, then time
  const sortedEvents = useMemo(() => {
    return [...events].sort((a, b) => {
      return new Date(a.scheduled_time).getTime() - new Date(b.scheduled_time).getTime()
    })
  }, [events])

  // Group events by venue and sort venues alphabetically
  const eventsByVenue = useMemo(() => {
    const grouped = new Map<string, Event[]>()
    sortedEvents.forEach((event) => {
      const venue = event.venue || 'Unknown Venue'
      if (!grouped.has(venue)) {
        grouped.set(venue, [])
      }
      grouped.get(venue)!.push(event)
    })

    // Convert to array, sort alphabetically, then back to Map
    const sortedEntries = Array.from(grouped.entries()).sort((a, b) =>
      a[0].localeCompare(b[0])
    )
    return new Map(sortedEntries)
  }, [sortedEvents])

  const toggleVenue = useCallback((venue: string) => {
    setExpandedVenues(prev => {
      const next = new Set(prev)
      if (next.has(venue)) {
        next.delete(venue)
      } else {
        next.add(venue)
      }
      return next
    })
  }, [])

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 3 }}>
        <ToggleButtonGroup
          value={viewMode}
          exclusive
          onChange={(_, newMode) => newMode && setViewMode(newMode)}
          size="small"
          sx={{
            '& .MuiToggleButton-root': {
              textTransform: 'none',
              fontWeight: 600,
              px: 2,
            },
          }}
        >
          <ToggleButton value="list">
            <ViewListIcon sx={{ mr: 1 }} fontSize="small" />
            List View
          </ToggleButton>
          <ToggleButton value="venue">
            <ViewModuleIcon sx={{ mr: 1 }} fontSize="small" />
            By Venue
          </ToggleButton>
        </ToggleButtonGroup>
      </Box>

      {viewMode === 'list' ? (
        <Box>
          {sortedEvents.map((event) => (
            <EventRow key={event.id} event={event} oddsMap={oddsMap} viewMode={viewMode} defaultCollapsed />
          ))}
        </Box>
      ) : (
        <Box>
          {Array.from(eventsByVenue.entries()).map(([venue, venueEvents]) => (
            <VenueGroup
              key={venue}
              venue={venue}
              events={venueEvents}
              expandedVenues={expandedVenues}
              toggleVenue={toggleVenue}
              oddsMap={oddsMap}
              viewMode={viewMode}
            />
          ))}
        </Box>
      )}
    </Box>
  )
}
