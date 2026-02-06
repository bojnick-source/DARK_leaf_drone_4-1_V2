from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class SalesInputs:
    unit_price_usd: float
    unit_cost_usd: float
    volume_units: int
    discount_rate: float = 0.0


@dataclass(frozen=True)
class ShippingInputs:
    distance_km: float
    mass_kg: float
    rate_usd_per_kg_km: float
    handling_fee_usd: float = 0.0


@dataclass(frozen=True)
class SalesSummary:
    revenue_usd: float
    cost_usd: float
    gross_margin_usd: float
    margin_rate: float


@dataclass(frozen=True)
class ShippingSummary:
    shipping_cost_usd: float
    total_cost_usd: float


def compute_sales(inputs: SalesInputs) -> SalesSummary:
    if inputs.unit_price_usd <= 0 or inputs.unit_cost_usd < 0:
        raise ValueError("invalid unit pricing")
    if inputs.volume_units <= 0:
        raise ValueError("volume_units must be > 0")
    if not 0.0 <= inputs.discount_rate < 1.0:
        raise ValueError("discount_rate must be within [0,1)")

    net_price = inputs.unit_price_usd * (1.0 - inputs.discount_rate)
    revenue = net_price * inputs.volume_units
    cost = inputs.unit_cost_usd * inputs.volume_units
    margin = revenue - cost
    margin_rate = margin / revenue if revenue > 0 else 0.0
    return SalesSummary(
        revenue_usd=revenue,
        cost_usd=cost,
        gross_margin_usd=margin,
        margin_rate=margin_rate,
    )


def compute_shipping(inputs: ShippingInputs) -> ShippingSummary:
    if inputs.distance_km <= 0 or inputs.mass_kg <= 0 or inputs.rate_usd_per_kg_km < 0:
        raise ValueError("invalid shipping inputs")
    shipping_cost = inputs.distance_km * inputs.mass_kg * inputs.rate_usd_per_kg_km
    total_cost = shipping_cost + inputs.handling_fee_usd
    return ShippingSummary(shipping_cost_usd=shipping_cost, total_cost_usd=total_cost)


def estimate_sales_and_shipping(sales: SalesInputs, shipping: ShippingInputs) -> Dict[str, float]:
    sales_summary = compute_sales(sales)
    shipping_summary = compute_shipping(shipping)
    net_profit = sales_summary.gross_margin_usd - shipping_summary.total_cost_usd
    return {
        "revenue_usd": sales_summary.revenue_usd,
        "gross_margin_usd": sales_summary.gross_margin_usd,
        "shipping_cost_usd": shipping_summary.shipping_cost_usd,
        "net_profit_usd": net_profit,
    }
