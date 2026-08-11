from decimal import Decimal

import pytest

from copro_auto.domain.calculations import calculate_shares, largest_remainder


def test_yasmin_shares(yasmin_project):
    shares = calculate_shares(yasmin_project)
    assert [share.ten_thousandths for share in shares] == [3522, 3239, 3239]
    assert sum(share.percentage for share in shares) == Decimal("100.00")


def test_equal_thirds_are_exact_and_stable():
    assert largest_remainder([Decimal("1"), Decimal("1"), Decimal("1")]) == [3334, 3333, 3333]


@pytest.mark.parametrize("surfaces", [[], [Decimal("0")], [Decimal("1"), Decimal("-1")]])
def test_invalid_surfaces_are_rejected(surfaces):
    with pytest.raises(ValueError):
        largest_remainder(surfaces)

