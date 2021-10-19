from collections import namedtuple
from pydicom.sr.codedict import codes

Point = namedtuple('Point', ['x', 'y'])


class Measurement():
    def __init__(self, unit, value):
        if type(unit) is str:
            self.unit = getattr(codes.UCUM, unit)
        else:
            self.unit = unit
        self.value = value

    def from_dict(self, dict):
        Measurement.__init__(self, dict['unit'], dict['value'])


class Ellipse(Measurement):
    def __init__(self, top, bottom, left, right, unit, value):
        super().__init__(unit, value)
        self.top = top
        self.bottom = bottom
        self.left = left
        self.right = right
        self.topleft = Point(left.x, top.y)
        self.bottomright = Point(right.x, bottom.y)

    @classmethod
    def from_center(cls, c, r1, r2, unit, value):
        return Ellipse(Point(c.x, c.y-r1), Point(c.x, c.y+r1), Point(c.x-r2, c.y), Point(c.x+r2, c.y), unit, value)

    def __repr__(self):
        return f'Ellipse<{self.top},{self.bottom},{self.left},{self.right}>({self.value} {self.unit.value})'


class PointMeasurement(Measurement):
    def __init__(self, x, y, unit, value):
        super().__init__(unit, value)
        self.x = x
        self.y = y

    def __add__(self, other):
        return PointMeasurement(self.x+other.x, self.y+other.y, self.unit, self.value)

    def __repr__(self):
        return f'PointMeasurement<{self.x,self.y}>({self.value} {self.unit.value})'
