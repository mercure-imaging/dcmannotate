from typing import (
    Any,
    Dict,
    Optional,
    Union,
)
from pydicom.sr.codedict import codes
from collections import namedtuple

from pydicom.sr.coding import Code

Point = namedtuple("Point", ["x", "y"])


class Measurement:
    unit: Optional[Code]
    value: Union[str, int, float]

    def __init__(
        self, unit: Optional[Union[str, Code]], value: Union[str, int, float]
    ) -> None:
        if type(value) is str and unit is not None:
            raise TypeError(
                "Measurements with units must have a numeric value.")

        if unit:
            if isinstance(unit, Code):
                self.unit = unit
            else:
                for u in dir(codes.UCUM):
                    if u.lower() == unit.lower():
                        self.unit = getattr(codes.UCUM, u)
        else:
            self.unit = None
        self.value = value

    # def from_dict(self, dict) -> Measurement:
    #     Measurement.__init__(self, dict["unit"], dict["value"])

    def __json_serializable__(self) -> Dict[str, Union[Optional[str], int, float]]:
        return dict(value=self.value, unit=self.unit.value if self.unit else None)


class Ellipse(Measurement):
    def __init__(
        self,
        c: Point,
        rx: int,
        ry: int,
        unit: Optional[Union[str, Code]],
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
        return f"Ellipse<{self.center}, {self.rx}x{self.ry}>({self.value} {self.unit.value if self.unit else ''})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Measurement):
            raise NotImplementedError
        if not isinstance(other, Ellipse):
            return False
        return (
            self.center == other.center
            and self.rx == other.rx
            and self.ry == other.ry
            and getattr(self.unit, "value", None) == getattr(other.unit, "value", None)
            and self.value == other.value
        )

    def __json_serializable__(self) -> Dict[str, Any]:
        return {
            **super().__json_serializable__(),
            **dict(center_x=self.center.x, center_y=self.center.y, rx=self.rx, ry=self.ry),
        }


class PointMeasurement(Measurement):
    def __init__(
        self,
        x: int,
        y: int,
        unit: Optional[Union[str, Code]],
        value: Union[str, int, float],
    ):
        super().__init__(unit, value)
        self.x = x
        self.y = y

    def __add__(self, other: Union["PointMeasurement", Point]) -> "PointMeasurement":
        return PointMeasurement(
            self.x + other.x,
            self.y + other.y,
            self.unit,
            self.value,
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Measurement):
            raise NotImplementedError
        if not isinstance(other, PointMeasurement):
            return False

        return (
            self.x == other.x
            and self.y == other.y
            and getattr(self.unit, "value", None) == getattr(other.unit, "value", None)
            and self.value == other.value
        )

    def __repr__(self) -> str:
        return f"PointMeasurement<{self.x,self.y}>({self.value}{' '+self.unit.value if self.unit else ''})"

    def __json_serializable__(self) -> Dict[str, Any]:
        return {**super().__json_serializable__(), **dict(x=self.x, y=self.y)}
