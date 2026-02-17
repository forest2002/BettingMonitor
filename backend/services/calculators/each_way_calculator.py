"""
Each-Way Profit Maximiser / Sniper Calculator

Compares BOTH win AND place components against Betfair Exchange.
Edge formula: 0.5 * (bookie_win/betfair_win - 1) + 0.5 * (bookie_place/betfair_place - 1)
Simulates all 3 outcomes (win/place/lose) with proper lay stakes on both markets.
Only flags as profitable when profit >= 0 in ALL scenarios.
"""
import os
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

# Betfair commission rate (configurable via env var, default 2%)
BETFAIR_COMMISSION = Decimal(os.getenv('BETFAIR_COMMISSION', '0.02'))


class EachWayCalculator:
    """Calculate each-way profit maximiser opportunities"""

    @staticmethod
    def calculate_place_odds(win_odds: Decimal, place_terms: str) -> Optional[Decimal]:
        """
        Calculate place odds from win odds and place terms.

        place_odds = (win_odds - 1) * fraction + 1
        """
        try:
            if not place_terms:
                return None

            if '/' in place_terms:
                parts = place_terms.split('/')
                numerator = Decimal(parts[0].strip())
                denominator = Decimal(parts[1].strip())
                fraction = numerator / denominator
            else:
                fraction = Decimal(place_terms)

            place_odds = (win_odds - 1) * fraction + 1
            return place_odds.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        except Exception as e:
            logger.warning(f"Failed to calculate place odds: {e}")
            return None

    @staticmethod
    def parse_place_terms_details(place_terms: str) -> Dict[str, any]:
        """
        Parse place terms to extract fraction and number of places.

        Args:
            place_terms: e.g., "1/4 1-2-3", "1/5 1-2-3-4"
        """
        result = {
            'fraction': None,
            'num_places': 3,
            'places_text': '1-2-3'
        }

        try:
            parts = place_terms.split()

            if parts and '/' in parts[0]:
                result['fraction'] = parts[0]

            if len(parts) > 1:
                places_part = parts[1]
                result['places_text'] = places_part
                result['num_places'] = places_part.count('-') + 1

        except Exception as e:
            logger.warning(f"Failed to parse place terms details: {e}")

        return result

    @staticmethod
    def calculate_each_way_value(
        bookmaker_win_odds: Decimal,
        bookmaker_place_terms: str,
        betfair_win_lay_odds: Decimal,
        betfair_place_lay_odds: Decimal,
        stake: Decimal = Decimal('10'),
        commission: Decimal = BETFAIR_COMMISSION,
    ) -> Dict[str, any]:
        """
        Full EW profit maximiser calculation.

        Compares both win and place components against Betfair,
        calculates lay stakes for both markets, and simulates all 3 outcomes.
        """
        Q = Decimal('0.01')
        result = {
            'is_opportunity': False,
            'bookmaker_win_odds': bookmaker_win_odds,
            'bookmaker_place_odds': None,
            'betfair_win_lay_odds': betfair_win_lay_odds,
            'betfair_place_lay_odds': betfair_place_lay_odds,
            'win_edge': Decimal('0'),
            'place_edge': Decimal('0'),
            'total_edge': Decimal('0'),
            'win_lay_stake': Decimal('0'),
            'place_lay_stake': Decimal('0'),
            'profit_if_wins': Decimal('0'),
            'profit_if_places': Decimal('0'),
            'profit_if_loses': Decimal('0'),
            'rating': 0,
            'error': None,
        }

        try:
            terms = EachWayCalculator.parse_place_terms_details(bookmaker_place_terms)
            bookie_place_odds = EachWayCalculator.calculate_place_odds(
                bookmaker_win_odds, terms['fraction']
            )

            if not bookie_place_odds:
                result['error'] = "Could not calculate place odds"
                return result

            result['bookmaker_place_odds'] = bookie_place_odds
            result['num_places'] = terms['num_places']

            # --- Edge calculation ---
            win_edge = bookmaker_win_odds / betfair_win_lay_odds - 1
            place_edge = bookie_place_odds / betfair_place_lay_odds - 1
            total_edge = (win_edge + place_edge) / 2

            result['win_edge'] = win_edge.quantize(Q)
            result['place_edge'] = place_edge.quantize(Q)
            result['total_edge'] = total_edge.quantize(Q)

            # --- Lay stake calculation (matched betting) ---
            half_stake = stake / 2
            comm_factor = betfair_win_lay_odds - commission
            comm_factor_place = betfair_place_lay_odds - commission

            win_lay_stake = (half_stake * bookmaker_win_odds) / comm_factor
            place_lay_stake = (half_stake * bookie_place_odds) / comm_factor_place

            result['win_lay_stake'] = win_lay_stake.quantize(Q)
            result['place_lay_stake'] = place_lay_stake.quantize(Q)

            # --- Profit simulation ---
            # Win lay liability = win_lay_stake * (betfair_win_lay_odds - 1)
            # Place lay liability = place_lay_stake * (betfair_place_lay_odds - 1)
            win_lay_liability = win_lay_stake * (betfair_win_lay_odds - 1)
            place_lay_liability = place_lay_stake * (betfair_place_lay_odds - 1)

            # Win lay profit = win_lay_stake * (1 - commission)
            # Place lay profit = place_lay_stake * (1 - commission)
            win_lay_profit = win_lay_stake * (1 - commission)
            place_lay_profit = place_lay_stake * (1 - commission)

            # Bookmaker returns
            win_return = half_stake * bookmaker_win_odds  # win part return
            place_return = half_stake * bookie_place_odds  # place part return

            # Scenario 1: Horse WINS (both win and place bets pay at bookie,
            # both lays lose)
            profit_if_wins = (
                win_return + place_return - stake
                - win_lay_liability - place_lay_liability
            )

            # Scenario 2: Horse PLACES (only place bet pays at bookie,
            # win lay wins, place lay loses)
            profit_if_places = (
                place_return - stake
                + win_lay_profit - place_lay_liability
            )

            # Scenario 3: Horse LOSES (nothing from bookie,
            # both lays win)
            profit_if_loses = (
                win_lay_profit + place_lay_profit - stake
            )

            result['profit_if_wins'] = profit_if_wins.quantize(Q)
            result['profit_if_places'] = profit_if_places.quantize(Q)
            result['profit_if_loses'] = profit_if_loses.quantize(Q)

            # Rating based on total_edge percentage
            rating = int((total_edge * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
            result['rating'] = rating

            # Only flag as profitable when profit >= 0 in ALL scenarios
            all_profitable = (
                profit_if_wins >= 0
                and profit_if_places >= 0
                and profit_if_loses >= 0
            )
            result['is_opportunity'] = all_profitable

        except Exception as e:
            logger.error(f"Error calculating each-way value: {e}", exc_info=True)
            result['error'] = str(e)

        return result

    @staticmethod
    def find_opportunities(selections_with_odds: list) -> list:
        """
        Find all each-way profit maximiser opportunities.

        Checks ALL bookmakers against Betfair win lay + place lay data.
        Requires both "Betfair Exchange" (win) and "Betfair Exchange Place" entries.
        """
        opportunities = []

        for selection in selections_with_odds:
            betfair_win_lay = None
            betfair_place_lay = None
            betfair_place_back = None
            bookmaker_odds_list = []

            for odds in selection.get('odds', []):
                bk = odds['bookmaker_name']
                if bk == 'Betfair Exchange':
                    # Win market: place_odds field stores the lay price
                    if odds.get('place_odds'):
                        betfair_win_lay = Decimal(str(odds['place_odds']))
                elif bk == 'Betfair Exchange Place':
                    # Place market: place_odds field stores the lay price
                    if odds.get('place_odds'):
                        betfair_place_lay = Decimal(str(odds['place_odds']))
                    # Place market: odds_decimal stores the back price
                    if odds.get('odds_decimal'):
                        betfair_place_back = Decimal(str(odds['odds_decimal']))
                else:
                    # Regular bookmaker with EW terms
                    if odds.get('place_terms'):
                        bookmaker_odds_list.append({
                            'bookmaker': bk,
                            'win_odds': Decimal(str(odds['odds_decimal'])),
                            'place_terms': odds['place_terms'],
                        })

            # --- Normal pass: requires win lay + place lay ---
            normal_bookmakers = set()
            if betfair_win_lay and betfair_place_lay:
                for bk_odds in bookmaker_odds_list:
                    calc = EachWayCalculator.calculate_each_way_value(
                        bookmaker_win_odds=bk_odds['win_odds'],
                        bookmaker_place_terms=bk_odds['place_terms'],
                        betfair_win_lay_odds=betfair_win_lay,
                        betfair_place_lay_odds=betfair_place_lay,
                    )

                    if calc['is_opportunity']:
                        normal_bookmakers.add(bk_odds['bookmaker'])
                        opportunities.append({
                            'selection_name': selection['name'],
                            'event_name': selection['event_name'],
                            'venue': selection.get('venue'),
                            'scheduled_time': selection.get('scheduled_time'),
                            'bookmaker': bk_odds['bookmaker'],
                            'is_fair_odds': False,
                            **calc,
                        })

            # --- Fair Odds pass: use place BACK price (matches other platforms) ---
            if betfair_win_lay and betfair_place_back:
                for bk_odds in bookmaker_odds_list:
                    # Skip if already found as normal opportunity
                    if bk_odds['bookmaker'] in normal_bookmakers:
                        continue
                    calc = EachWayCalculator.calculate_each_way_value(
                        bookmaker_win_odds=bk_odds['win_odds'],
                        bookmaker_place_terms=bk_odds['place_terms'],
                        betfair_win_lay_odds=betfair_win_lay,
                        betfair_place_lay_odds=betfair_place_back,  # Use BACK price
                    )
                    # Only show FO opportunities with rating >= 10 (GOOD or EXCELLENT)
                    if calc['is_opportunity'] and calc['rating'] >= 10:
                        opportunities.append({
                            'selection_name': selection['name'],
                            'event_name': selection['event_name'],
                            'venue': selection.get('venue'),
                            'scheduled_time': selection.get('scheduled_time'),
                            'bookmaker': bk_odds['bookmaker'],
                            'is_fair_odds': True,
                            **calc,
                        })

        # Sort by rating (best first)
        opportunities.sort(key=lambda x: x['rating'], reverse=True)
        return opportunities
