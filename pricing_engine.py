"""
pricing_engine.py - Tiered Billing & Discount Engine (Business Logic Module)
Calculates invoices based on subscription tiers, consumption volume, and coupon codes.
"""

def calculate_invoice(base_amount: float, tier: str, volume: int = 1, coupon: str = None) -> float:
    """
    Tier multipliers:
      - 'STANDARD': 1.0 (no discount)
      - 'PRO': 0.85 (15% tier discount)
      - 'ENTERPRISE': 0.70 (30% tier discount)
    Volume discounts:
      - volume >= 10: additional 5% off subtotal
      - volume >= 50: additional 10% off subtotal
    Coupon codes:
      - 'SAVE10': flat $10.0 deduction
    """
    if base_amount < 0 or volume <= 0:
        raise ValueError("Invalid base amount or volume")

    tier_multipliers = {
        "STANDARD": 1.0,
        "PRO": 0.85,
        "ENTERPRISE": 0.70
    }
    multiplier = tier_multipliers.get(tier.upper(), 1.0)
    subtotal = base_amount * multiplier * volume

    # Volume discount tier
    if volume >= 50:
        subtotal *= 0.90
    elif volume >= 10:
        subtotal *= 0.95

    # Promotional coupon deduction
    if coupon == "SAVE10":
        subtotal = max(0.0, subtotal - 10.0)

    return round(subtotal, 2)
