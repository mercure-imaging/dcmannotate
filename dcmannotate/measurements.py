from collections import namedtuple

Point = namedtuple("Point", ["x", "y"])

from collections import namedtuple
from pydicom.sr.codedict import codes
from typing import (
    Any,
    Optional,
    Union,
)


class Measurement:
    def __init__(self, unit: Optional[str], value: Union[str, int, float]) -> None:
        if type(value) is str and unit is not None:
            raise TypeError("Measurements with units must have a numeric value.")
        if type(unit) is str:
            self.unit = getattr(codes.UCUM, unit)
        else:
            self.unit = unit
        self.value = value

    # def from_dict(self, dict) -> Measurement:
    #     Measurement.__init__(self, dict["unit"], dict["value"])


class Ellipse(Measurement):
    def __init__(
        self,
        c: Point,
        rx: int,
        ry: int,
        unit: Optional[str],
        value: Union[str, int, float],
    ):
        super().__init__(unit, value)
        self.center = c
        self.rx = rx
        self.ry = ry
        self.top = Point(c.x, c.y - ry)
        self.bottom = Point(c.x, c.y + ry)
        self.left = Point(c.x - rx, c.y)
        self.right = Point(c.x + rx, c.y)
        self.topleft = Point(c.x - rx, c.y - ry)
        self.bottomright = Point(c.x + rx, c.y + ry)

    def __repr__(self) -> str:
        return f"Ellipse<{self.top},{self.bottom},{self.left},{self.right}>({self.value} {self.unit.value if self.unit else ''})"


class PointMeasurement(Measurement):
    def __init__(
        self, x: int, y: int, unit: Optional[str], value: Union[str, int, float]
    ):
        super().__init__(unit, value)
        self.x = x
        self.y = y

    def __add__(self, other: Union["PointMeasurement", Point]) -> "PointMeasurement":
        return PointMeasurement(
            self.x + other.x, self.y + other.y, self.unit, self.value
        )

    def __repr__(self) -> str:
        return f"PointMeasurement<{self.x,self.y}>({self.value}{' '+self.unit.value if self.unit else ''})"
