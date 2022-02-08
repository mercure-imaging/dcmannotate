import math
from typing import Any, Generic, TypeVar

PointType = TypeVar("PointType", int, float)


class GenericPoint(Generic[PointType]):
    _x: PointType
    _y: PointType

    def __init__(self, x: PointType, y: PointType):
        self.x = x
        self.y = y

    @property
    def x(self) -> PointType:
        return self._x

    @property
    def y(self) -> PointType:
        return self._y

    @x.setter
    def x(self, x):
        self._x = x

    @y.setter
    def y(self, y):
        self._y = y

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, GenericPoint):
            return False
        if type(self.x) != type(other.x):
            return False
        if self.x == other.x and self.y == other.y:
            return True
        return False

    def __repr__(self) -> str:
        return f"{self.x},{self.y}"

    def __hash__(self) -> int:
        return hash((self.x, self.y))

    def __getitem__(self, idx: int) -> PointType:
        if idx == 0:
            return self.x
        elif idx == 1:
            return self.y
        else:
            raise IndexError


class Point(GenericPoint[float]):
    @GenericPoint.x.setter
    def x(self, x) -> float:
        # if float(x) != x:
        #     raise TypeError("Points must have integer coordinates.")
        self._x = float(x)

    @GenericPoint.y.setter
    def y(self, y) -> float:
        # if int(y) != y:
        #     raise TypeError("Points must have integer coordinates.")
        self._y = float(y)


class PointInt(GenericPoint[int]):
    @GenericPoint.x.setter
    def x(self, x) -> int:
        if int(x) != x:
            raise TypeError("Points must have integer coordinates.")
        self._x = int(x)

    @GenericPoint.y.setter
    def y(self, y) -> int:
        if int(y) != y:
            raise TypeError("Points must have integer coordinates.")
        self._y = int(y)


class Vector(GenericPoint[float]):
    def length(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y)

    def normed(self) -> "Vector":
        return self.__div__(self.length())

    def __div__(self, other: float) -> "Vector":
        return Vector(self.x / other, self.y / other)
