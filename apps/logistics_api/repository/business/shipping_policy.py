"""Business shipping policy rules."""

from contracts.backend import ShippingPolicyResult
from contracts.routing import RouteOption
from contracts.shipment import Shipment


class ShippingPolicy:
    """Deterministic business rules for whether a route is allowed."""

    @classmethod
    def evaluate(cls, shipment: Shipment, route: RouteOption) -> ShippingPolicyResult:
        """Check whether the route is allowed for the given shipment.

        Usage:
            Called by the repository and reroute handler before accepting a route.

        Parameters:
            shipment: The shipment being evaluated.
            route: The route alternative being checked.

        Returns:
            A ShippingPolicyResult with allowed flag, reasons, and rule_ids.
        """
        if shipment.status == "delivered":
            return ShippingPolicyResult(
                allowed=False,
                reasons=["Delivered shipments cannot be rerouted."],
                rule_ids=["delivered-shipment"],
            )

        if shipment.cargo_type == "temperature_controlled" and "BEANR" in route.via_ports:
            return ShippingPolicyResult(
                allowed=False,
                reasons=["Temperature-controlled cargo cannot transit Antwerp (BEANR)."],
                rule_ids=["temp-controlled-beanr"],
            )

        return ShippingPolicyResult(
            allowed=True,
            reasons=["Route meets shipping policy requirements."],
            rule_ids=["shipping-policy-ok"],
        )
