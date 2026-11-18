import pytest
from pricing_engine import calculate_invoice


def test_standard_tier():
    # 100 * 1.0 * 1 = 100.0
    assert calculate_invoice(100.0, "STANDARD", 1) == 100.0


def test_pro_tier_discount():
    # 15% discount on $100 -> $85.0
    assert calculate_invoice(100.0, "PRO", 1) == 85.0


def test_enterprise_tier_volume_discount():
    # 100 * 0.70 * 10 = 700. Volume >= 10 gives 5% off 700 -> 665.0
    assert calculate_invoice(100.0, "ENTERPRISE", 10) == 665.0


def test_coupon_deduction():
    # 100 * 1.0 - 10 = 90.0
    assert calculate_invoice(100.0, "STANDARD", 1, coupon="SAVE10") == 90.0


def test_invalid_input_validation():
    with pytest.raises(ValueError):
        calculate_invoice(-50.0, "PRO")
