"""
pricing_engine.py - Tiered Billing & Discount Engine (Self-Healed Implementation)
Calculates invoices based on subscription tiers, consumption volume, and coupon codes.
"""

def calculate_invoice(base_amount: float, tier: str, volume: int = 1, coupon: str = None) -> float:
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
