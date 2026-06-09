"""
Courier Selection Service for Shiprocket Integration

This service provides intelligent courier selection logic based on various strategies:
- Cheapest: Select courier with lowest rate
- Fastest: Select courier with shortest delivery time
- Balanced: Balance between cost and speed
"""

from typing import Optional
import logging

logger = logging.getLogger(__name__)


class CourierSelectionService:
    """Service for selecting optimal courier based on various strategies"""

    def select_cheapest_courier(self, couriers: list[dict]) -> Optional[dict]:
        """
        Select courier with lowest rate

        Args:
            couriers: List of available couriers from serviceability API

        Returns:
            Courier dict with lowest rate, or None if no couriers available
        """
        if not couriers:
            logger.warning("No couriers available for selection")
            return None

        try:
            cheapest = min(couriers, key=lambda c: c.get('rate', float('inf')))
            logger.info(f"Selected cheapest courier: {cheapest.get('courier_name')} (₹{cheapest.get('rate')})")
            return cheapest
        except (ValueError, KeyError) as e:
            logger.error(f"Error selecting cheapest courier: {e}")
            return None

    def select_fastest_courier(self, couriers: list[dict]) -> Optional[dict]:
        """
        Select courier with earliest delivery time (lowest ETD hours)

        Args:
            couriers: List of available couriers from serviceability API

        Returns:
            Courier dict with shortest delivery time, or None if no couriers available
        """
        if not couriers:
            logger.warning("No couriers available for selection")
            return None

        try:
            # Try etd_hours first, fall back to parsing etd string
            fastest = min(couriers, key=lambda c: c.get('etd_hours', float('inf')))
            logger.info(
                f"Selected fastest courier: {fastest.get('courier_name')} "
                f"(ETD: {fastest.get('etd', 'N/A')})"
            )
            return fastest
        except (ValueError, KeyError) as e:
            logger.error(f"Error selecting fastest courier: {e}")
            return None

    def select_balanced_courier(self, couriers: list[dict]) -> Optional[dict]:
        """
        Select courier balancing cost and speed

        Uses a weighted score: 60% cost, 40% speed
        Lower score is better

        Args:
            couriers: List of available couriers from serviceability API

        Returns:
            Courier with best balanced score, or None if no couriers available
        """
        if not couriers:
            logger.warning("No couriers available for selection")
            return None

        try:
            # Extract rates and etd_hours
            rates = [c.get('rate', 0) for c in couriers if c.get('rate') is not None]
            etd_hours_list = [c.get('etd_hours', 0) for c in couriers if c.get('etd_hours') is not None]

            if not rates or not etd_hours_list:
                logger.warning("Missing rate or ETD data, falling back to cheapest")
                return self.select_cheapest_courier(couriers)

            # Normalize values (0-1 scale)
            min_rate, max_rate = min(rates), max(rates)
            min_etd, max_etd = min(etd_hours_list), max(etd_hours_list)

            # Avoid division by zero
            rate_range = max_rate - min_rate if max_rate != min_rate else 1
            etd_range = max_etd - min_etd if max_etd != min_etd else 1

            def calculate_score(courier: dict) -> float:
                """Calculate weighted score for courier"""
                rate = courier.get('rate', float('inf'))
                etd = courier.get('etd_hours', float('inf'))

                # Normalize to 0-1 scale
                normalized_rate = (rate - min_rate) / rate_range
                normalized_etd = (etd - min_etd) / etd_range

                # Weighted score: 60% cost, 40% speed
                return (normalized_rate * 0.6) + (normalized_etd * 0.4)

            balanced = min(couriers, key=calculate_score)
            logger.info(
                f"Selected balanced courier: {balanced.get('courier_name')} "
                f"(₹{balanced.get('rate')}, ETD: {balanced.get('etd', 'N/A')})"
            )
            return balanced

        except (ValueError, KeyError, ZeroDivisionError) as e:
            logger.error(f"Error selecting balanced courier: {e}, falling back to cheapest")
            return self.select_cheapest_courier(couriers)

    def select_by_strategy(
        self,
        couriers: list[dict],
        strategy: str = 'cheapest',
        blacklisted_courier_ids: Optional[list[int]] = None
    ) -> Optional[dict]:
        """
        Select courier based on strategy with blacklist filtering

        Args:
            couriers: List of available couriers from serviceability API
            strategy: Selection strategy ('cheapest', 'fastest', 'balanced')
            blacklisted_courier_ids: Courier IDs to exclude from selection

        Returns:
            Selected courier dict or None if no suitable courier found
        """
        if not couriers:
            logger.warning("No couriers available for selection")
            return None

        # Filter blacklisted couriers
        if blacklisted_courier_ids:
            original_count = len(couriers)
            couriers = [
                c for c in couriers
                if c.get('courier_company_id') not in blacklisted_courier_ids
            ]
            filtered_count = original_count - len(couriers)
            if filtered_count > 0:
                logger.info(f"Filtered out {filtered_count} blacklisted couriers")

        if not couriers:
            logger.error("No couriers available after blacklist filtering")
            return None

        # Select based on strategy
        strategy = strategy.lower().strip()

        if strategy == 'fastest':
            return self.select_fastest_courier(couriers)
        elif strategy == 'balanced':
            return self.select_balanced_courier(couriers)
        else:  # Default to cheapest
            if strategy != 'cheapest':
                logger.warning(f"Unknown strategy '{strategy}', defaulting to 'cheapest'")
            return self.select_cheapest_courier(couriers)

    def calculate_savings(self, selected: dict, all_couriers: list[dict]) -> float:
        """
        Calculate cost savings vs most expensive courier

        Args:
            selected: The selected courier dict
            all_couriers: List of all available couriers

        Returns:
            Savings amount (positive number) or 0.0 if no savings
        """
        if not all_couriers or not selected:
            return 0.0

        try:
            max_rate = max(c.get('rate', 0) for c in all_couriers if c.get('rate') is not None)
            selected_rate = selected.get('rate', 0)

            if max_rate <= 0 or selected_rate <= 0:
                return 0.0

            savings = max_rate - selected_rate
            return max(savings, 0.0)  # Ensure non-negative

        except (ValueError, KeyError, TypeError) as e:
            logger.error(f"Error calculating savings: {e}")
            return 0.0

    def get_courier_summary(self, couriers: list[dict]) -> dict:
        """
        Get summary statistics of available couriers

        Args:
            couriers: List of available couriers

        Returns:
            Dictionary with summary stats (count, avg_rate, min_rate, max_rate, etc.)
        """
        if not couriers:
            return {
                "count": 0,
                "avg_rate": 0.0,
                "min_rate": 0.0,
                "max_rate": 0.0,
                "cheapest_courier": None,
                "fastest_courier": None
            }

        rates = [c.get('rate', 0) for c in couriers if c.get('rate') is not None]

        return {
            "count": len(couriers),
            "avg_rate": sum(rates) / len(rates) if rates else 0.0,
            "min_rate": min(rates) if rates else 0.0,
            "max_rate": max(rates) if rates else 0.0,
            "cheapest_courier": self.select_cheapest_courier(couriers),
            "fastest_courier": self.select_fastest_courier(couriers)
        }
