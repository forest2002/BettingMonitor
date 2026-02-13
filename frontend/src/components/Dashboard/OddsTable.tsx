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
} from '@mui/material'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import { useOddsStore } from '../../stores/oddsStore'
import { Event } from '../../types'

export const OddsTable = () => {
  const { events, oddsMap } = useOddsStore()

  const formatTime = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleString('en-GB', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const getOddsForSelection = (eventId: number, selectionId: number) => {
    const eventOdds = oddsMap.get(eventId) || []
    return eventOdds.filter((odds) => odds.selection_id === selectionId)
  }

  const EventRow = ({ event }: { event: Event }) => {
    const hasOdds = oddsMap.has(event.id) && oddsMap.get(event.id)!.length > 0

    return (
      <Accordion key={event.id} defaultExpanded={hasOdds}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%' }}>
            <Chip
              label={event.event_type_name || 'Horse Racing'}
              color="primary"
              size="small"
            />
            <Typography variant="h6">{event.name}</Typography>
            {event.venue && (
              <Typography variant="body2" color="text.secondary">
                @ {event.venue}
              </Typography>
            )}
            <Typography variant="body2" color="text.secondary" sx={{ ml: 'auto' }}>
              {formatTime(event.scheduled_time)}
            </Typography>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          {event.selections.length === 0 ? (
            <Typography color="text.secondary">No selections available</Typography>
          ) : (
            <TableContainer component={Paper} variant="outlined">
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Selection</TableCell>
                    <TableCell>Bookmaker</TableCell>
                    <TableCell align="right">Win Odds</TableCell>
                    <TableCell align="right">Place Odds</TableCell>
                    <TableCell align="right">Place Terms</TableCell>
                    <TableCell align="right">Last Updated</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {event.selections.map((selection) => {
                    const selectionOdds = getOddsForSelection(event.id, selection.id)

                    if (selectionOdds.length === 0) {
                      return (
                        <TableRow key={selection.id}>
                          <TableCell>{selection.name}</TableCell>
                          <TableCell colSpan={5}>
                            <Typography variant="body2" color="text.secondary">
                              No odds available
                            </Typography>
                          </TableCell>
                        </TableRow>
                      )
                    }

                    return selectionOdds.map((odds, index) => (
                      <TableRow key={`${selection.id}-${odds.bookmaker_id}`}>
                        {index === 0 && (
                          <TableCell rowSpan={selectionOdds.length}>
                            <Typography fontWeight="medium">{selection.name}</Typography>
                            {selection.metadata?.rating && (
                              <Chip
                                label={`Rating: ${selection.metadata.rating}`}
                                size="small"
                                sx={{ mt: 0.5 }}
                              />
                            )}
                          </TableCell>
                        )}
                        <TableCell>{odds.bookmaker_name}</TableCell>
                        <TableCell align="right">
                          <Typography fontWeight="bold" color="primary">
                            {odds.odds_decimal.toFixed(2)}
                          </Typography>
                        </TableCell>
                        <TableCell align="right">
                          {odds.place_odds
                            ? odds.place_odds.toFixed(2)
                            : '-'}
                        </TableCell>
                        <TableCell align="right">
                          {odds.place_terms || '-'}
                        </TableCell>
                        <TableCell align="right">
                          <Typography variant="body2" color="text.secondary">
                            {new Date(odds.scraped_at).toLocaleTimeString('en-GB')}
                          </Typography>
                        </TableCell>
                      </TableRow>
                    ))
                  })}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </AccordionDetails>
      </Accordion>
    )
  }

  return (
    <Box>
      {events.map((event) => (
        <EventRow key={event.id} event={event} />
      ))}
    </Box>
  )
}
