from reidce.sales_shipping import SalesInputs, ShippingInputs, compute_sales, compute_shipping


def test_sales_summary() -> None:
    summary = compute_sales(SalesInputs(unit_price_usd=1200.0, unit_cost_usd=700.0, volume_units=10))
    assert summary.revenue_usd > 0.0
    assert summary.gross_margin_usd > 0.0


def test_shipping_summary() -> None:
    summary = compute_shipping(ShippingInputs(distance_km=1500.0, mass_kg=25.0, rate_usd_per_kg_km=0.002))
    assert summary.shipping_cost_usd > 0.0
    assert summary.total_cost_usd > 0.0
