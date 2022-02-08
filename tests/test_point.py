import pytest
from dcmannotate import Point


def test_point() -> None:
    k = Point(1, 2)
    assert type(k.x) == float

    with pytest.raises(OverflowError):
        k.x = 10**10000
