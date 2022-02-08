import math
from collections import namedtuple
from typing import Any, Dict, Optional, Union

from pydicom.sr.codedict import codes

from pydicom.sr.coding import Code

from .utils import Point


class Measurement:
    unit: Optional[Code]
    value: Union[str, int, float]

    def __init__(
        self, unit: Optional[Union[str, Code]], value: Union[str, int, float]
    ) -> None:
        if type(value) is str and unit is not None:
            raise TypeError("Measurements with units must have a numeric value.")

        if unit:
            if isinstance(unit, Code):
                self.unit = unit
            else:
                for u in dir(codes.UCUM):
                    if u.lower() == unit.lower():
                        self.unit = getattr(codes.UCUM, u)
                        break
                else:
                    raise ValueError(f"Unknown UCUM unit {unit}.")
        else:
            self.unit = None
        self.value = value

    def __json_serializable__(
        self,
    ) -> Dict[str, Union[Optional[str], int, float]]:
        return dict(value=self.value, unit=self.unit.value if self.unit else None)


class Ellipse(Measurement):
    rx: int
    ry: int
    center: Point

    @property
    def top(self):  # self.top = Point(c.x, c.y - ry)
        return Point(self.center.x, self.center.y - self.ry)

    @property
    def bottom(self):  # self.bottom = Point(c.x, c.y + ry)
        return Point(self.center.x, self.center.y + self.ry)

    @property
    def left(self):  # self.left = Point(c.x - rx, c.y)
        return Point(self.center.x - self.rx, self.center.y)

    @property
    def right(self):  # self.right = Point(c.x + rx, c.y)
        return Point(self.center.x + self.rx, self.center.y)

    @property
    def topleft(self):  # self.topleft = Point(c.x - rx, c.y - ry)
        return Point(self.center.x - self.rx, self.center.y - self.ry)

    @property
    def bottomright(self):  # self.bottomright = Point(c.x + rx, c.y + ry)
        return Point(self.center.x + self.rx, self.center.y + self.ry)

    def __init__(
        self,
        c: Point,
        rx: float,
        ry: float,
        unit: Optional[Union[str, Code]],
        value: Union[str, int, float],
    ):
        super().__init__(unit, value)
        self.center = c
        # if not (rx == int(rx) and ry == int(ry)):
        #     raise TypeError("Ellipse radii must be integers.")
        self.rx = float(rx)
        self.ry = float(ry)

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
            **dict(
                center_x=self.center.x,
                center_y=self.center.y,
                rx=self.rx,
                ry=self.ry,
            ),
        }


class PointMeasurement(Measurement):
    __point: Point

    @property
    def x(self):
        return self.__point.x

    @property
    def y(self):
        return self.__point.y

    @x.setter
    def x(self, x):
        self.__point.x = x

    @y.setter
    def y(self, y):
        self.__point.y = y

    def __init__(
        self,
        x: int,
        y: int,
        unit: Optional[Union[str, Code]],
        value: Union[str, int, float],
    ):
        super().__init__(unit, value)
        self.__point = Point(x, y)

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
