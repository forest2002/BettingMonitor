"""
Each-Way Arbitrage Calculator

Calculates expected value and profit for each-way arbitrage opportunities
where bookmaker place odds > Betfair Exchange lay odds
"""
from decimal import Decimal
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

class EachWayCalculator:
    """Calculate each-way arbitrage opportunities"""

    @staticmethod
    def calculate_place_odds(win_odds: Decimal, place_terms: str) -> Optional[Decimal]:
        """
        Calculate place odds from win odds and place terms

        Args:
            win_odds: Decimal odds for the win
            place_terms: e.g., "1/4", "1/5", "1/3"

        Returns:
            Place odds as Decimal, or None if can't parse
        """
        try:
            if not place_terms:
                return None

            # Parse fraction like "1/4" or "1/5"
            if '/' in place_terms:
                parts = place_terms.split('/')
                numerator = Decimal(parts[0].strip())
                denominator = Decimal(parts[1].strip())
                fraction = numerator / denominator
            else:
                # Sometimes it's just a decimal like "0.25"
                fraction = Decimal(place_terms)

            # Place odds = 1 + (win_odds - 1) * fraction
            place_odds = 1 + (win_odds - 1) * fraction
            return place_odds.quantize(Decimal('0.01'))

        except Exception as e:
            logger.warning(f"Failed to calculate place odds: {e}")
            return None

    @staticmethod
    def parse_place_terms_details(place_terms: str) -> Dict[str, any]:
        """
        Parse place terms to extract fraction and number of places

        Args:
            place_terms: e.g., "1/4 1-2-3", "1/5 1-2-3-4"

        Returns:
            Dict with 'fraction', 'num_places', 'places_text'
        """
        result = {
            'fraction': None,
            'num_places': 3,  # Default
            'places_text': '1-2-3'
        }

        try:
            parts = place_terms.split()

            # First part is usually the fraction
            if parts and '/' in parts[0]:
                result['fraction'] = parts[0]

            # Look for place indicators
            if len(parts) > 1:
                places_part = parts[1]
                result['places_text'] = places_part
                # Count the dashes to get number of places
                result['num_places'] = places_part.count('-') + 1

        except Exception as e:
            logger.warning(f"Failed to parse place terms details: {e}")

        return result

    @staticmethod
    def calculate_each_way_value(
        bookmaker_win_odds: Decimal,
        bookmaker_place_terms: str,
        betfair_lay_place_odds: Decimal,
        stake: Decimal = Decimal('100')
    ) -> Dict[str, any]:
        """
        Calculate the expected value and profit for an each-way arbitrage

        Args:
            bookmaker_win_odds: Bookmaker's win odds (e.g., 8.0)
            bookmaker_place_terms: e.g., "1/4 1-2-3"
            betfair_lay_place_odds: Betfair's lay odds for place (e.g., 1.8)
            stake: Bet stake (default 100)

        Returns:
            Dict with calculations and opportunity details
        """
        result = {
            'is_opportunity': False,
            'bookmaker_place_odds': None,
            'betfair_lay_odds': betfair_lay_place_odds,
            'expected_value': Decimal('0'),
            'profit_if_places': Decimal('0'),
            'profit_if_wins': Decimal('0'),
            'profit_if_loses': Decimal('0'),
            'rating': 0,
            'error': None
        }

        try:
            # Parse place terms
            terms = EachWayCalculator.parse_place_terms_details(bookmaker_place_terms)

            # Calculate bookmaker place odds
            place_odds = EachWayCalculator.calculate_place_odds(
                bookmaker_win_odds,
                terms['fraction']
            )

            if not place_odds:
                result['error'] = "Could not calculate place odds"
                return result

            result['bookmaker_place_odds'] = place_odds

            # Check if there's an opportunity
            # We want bookmaker place odds > Betfair lay odds
            if place_odds <= betfair_lay_place_odds:
                return result

            # Calculate profits for different outcomes
            ew_stake = stake / 2  # Each-way is split 50/50 between win and place

            # Betfair commission (typically 5%)
            commission = Decimal('0.05')

            # Scenario 1: Horse WINS (both win and place bets pay)
            win_return = ew_stake * bookmaker_win_odds
            place_return = ew_stake * place_odds
            bookmaker_total_return = win_return + place_return

            # Lay liability on Betfair place market
            lay_stake = ew_stake  # Match the place stake
            lay_liability = lay_stake * (betfair_lay_place_odds - 1)

            profit_if_wins = bookmaker_total_return - stake - lay_liability

            # Scenario 2: Horse PLACES (only place bet pays)
            place_return_only = ew_stake * place_odds
            profit_if_places = place_return_only - stake - lay_liability

            # Scenario 3: Horse LOSES (nothing pays, but we win the lay)
            lay_win = lay_stake * (1 - commission)
            profit_if_loses = lay_win - stake

            # Calculate expected value (simplified - assuming equal probability)
            # In reality, you'd use actual probabilities
            expected_value = (profit_if_places + profit_if_wins + profit_if_loses) / 3

            # Rating: higher is better
            # Based on the edge (difference between place odds)
            edge = float(place_odds - betfair_lay_place_odds)
            rating = int(edge * 100)  # Convert to percentage-like score

            result.update({
                'is_opportunity': True,
                'expected_value': expected_value.quantize(Decimal('0.01')),
                'profit_if_places': profit_if_places.quantize(Decimal('0.01')),
                'profit_if_wins': profit_if_wins.quantize(Decimal('0.01')),
                'profit_if_loses': profit_if_loses.quantize(Decimal('0.01')),
                'rating': rating,
                'edge': float(edge),
                'num_places': terms['num_places']
            })

        except Exception as e:
            logger.error(f"Error calculating each-way value: {e}", exc_info=True)
            result['error'] = str(e)

        return result

    @staticmethod
    def find_opportunities(selections_with_odds: list) -> list:
        """
        Find all each-way arbitrage opportunities from a list of selections

        Args:
            selections_with_odds: List of selections with odds from multiple bookmakers

        Returns:
            List of opportunities sorted by rating (best first)
        """
        opportunities = []

        for selection in selections_with_odds:
            # Need: bookmaker odds + Betfair lay place odds
            bookmaker_odds = None
            betfair_place_odds = None

            for odds in selection.get('odds', []):
                if odds['bookmaker_name'] == 'Betfair Exchange':
                    # Betfair should have place market odds
                    if odds.get('place_odds'):
                        betfair_place_odds = Decimal(str(odds['place_odds']))
                else:
                    # Other bookmakers - use the first one we find
                    if not bookmaker_odds and odds.get('place_terms'):
                        bookmaker_odds = {
                            'bookmaker': odds['bookmaker_name'],
                            'win_odds': Decimal(str(odds['odds_decimal'])),
                            'place_terms': odds['place_terms']
                        }

            # Calculate if we have both
            if bookmaker_odds and betfair_place_odds:
                calc = EachWayCalculator.calculate_each_way_value(
                    bookmaker_odds['win_odds'],
                    bookmaker_odds['place_terms'],
                    betfair_place_odds
                )

                if calc['is_opportunity']:
                    opportunities.append({
                        'selection_name': selection['name'],
                        'event_name': selection['event_name'],
                        'bookmaker': bookmaker_odds['bookmaker'],
                        **calc
                    })

        # Sort by rating (best opportunities first)
        opportunities.sort(key=lambda x: x['rating'], reverse=True)

        return opportunities
