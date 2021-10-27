from collections import namedtuple
from pydicom.sr.codedict import codes
from pydicom import dcmread
Point = namedtuple('Point', ['x', 'y'])


class AnnotationSet():
    def __init__(self, annotation_sets):
        self.__annotation_sets = {}
        self.__list = annotation_sets
        for set_ in annotation_sets:
            self.__annotation_sets[set_.reference.SOPInstanceUID] = set_

    def keys(self):
        return self.__annotation_sets.keys()

    def values(self):
        return self.__annotation_sets.values()

    def __iter__(self):
        return self.__list.__iter__()

    def __next__(self):
        return self.__list.__next__()

    def __getitem__(self, key):
        return self.__annotation_sets[key]

    def get(self, key):
        return self.__annotation_sets.get(key)

    def __repr__(self) -> str:
        return self.__annotation_sets.__repr__()


class Annotations():
    def __init__(self, ellipses, arrows, reference_dataset=None):
        self.ellipses = ellipses
        self.arrows = arrows
        if type(reference_dataset) is str:
            reference_dataset = dcmread(reference_dataset)

        self.reference = reference_dataset
        if reference_dataset is not None:
            self.SOPInstanceUID = reference_dataset.SOPInstanceUID


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
        self.center = Point(top.x, left.y)
        self.ry = (bottom.y - top.y) / 2.0
        self.rx = (right.x - left.x) / 2.0

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
