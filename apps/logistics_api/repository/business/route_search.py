"""Route search and filtering logic."""

from datetime import timedelta

from contracts.routing import RouteConstraints, RouteOption
from contracts.shipment import Shipment


class RouteSearch:
    """Filters and sorts route options for a shipment."""

    @classmethod
    def filter_routes(
        cls,
        shipment: Shipment,
        routes: list[RouteOption],
        constraints: RouteConstraints,
    ) -> list[RouteOption]:
        """Apply constraints and return matching routes sorted by cost then id.

        Usage:
            Called by InMemoryLogisticsRepository.find_routes.

        Parameters:
            shipment: The shipment whose planned ETA is used for delay checks.
            routes: All route options for the shipment before filtering.
            constraints: Search filters to apply.

        Returns:
            A sorted list of matching routes, capped at max_results.
        """
        filtered: list[RouteOption] = []

        for route in routes:
            if constraints.require_capacity and not route.capacity_available:
                continue

            if (
                constraints.max_additional_cost_eur is not None
                and route.additional_cost_eur > constraints.max_additional_cost_eur
            ):
                continue

            if constraints.max_delay_hours is not None:
                max_eta = shipment.planned_eta + timedelta(hours=constraints.max_delay_hours)
                if route.eta > max_eta:
                    continue

            filtered.append(route)

        filtered.sort(key=lambda route: (route.additional_cost_eur, route.route_id))
        return filtered[: constraints.max_results]
