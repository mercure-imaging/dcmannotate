import math
from typing import Any, Generic, Union, TypeVar

PointType = TypeVar("PointType", int, float)


class GenericPoint(Generic[PointType]):
    _x: PointType
    _y: PointType

    @property
    def x(self) -> PointType:
        return self._x

    @x.setter
    def x(self, x: PointType) -> None:
        self._x = x

    @property
    def y(self) -> PointType:
        return self._y

    @y.setter
    def y(self, y: PointType) -> None:
        self._y = y

    def __init__(self, x: PointType, y: PointType):
        self.x = x
        self.y = y

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
    @property
    def x(self) -> float:
        return super().x

    @GenericPoint.x.setter
    def x(self, x: Union[int, float]) -> None:
        self._x = float(x)

    @property
    def y(self) -> float:
        return super().y

    @GenericPoint.y.setter
    def y(self, y: Union[int, float]) -> None:
        self._y = float(y)


class PointInt(GenericPoint[int]):
    @property
    def x(self) -> int:
        return super().x

    @GenericPoint.x.setter
    def x(self, x: Union[int, float]) -> None:
        if int(x) != x:
            raise TypeError("Points must have integer coordinates.")
        self._x = int(x)

    @property
    def y(self) -> int:
        return super().y

    @GenericPoint.y.setter
    def y(self, y: Union[int, float]) -> None:
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
