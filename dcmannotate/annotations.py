from subprocess import run, PIPE
import numpy as np
from collections.abc import Iterable
from pathlib import Path
from collections import namedtuple
import types
from pydicom.dataset import Dataset
from pydicom.sr.codedict import codes
from pydicom import dcmread
Point = namedtuple('Point', ['x', 'y'])


class DicomVolume():
    def __init__(self, datasets, read_pixels=True):
        self.load(datasets, read_pixels)

    def load(self, param, read_pixels=True):
        if type(param) is str:
            param = Path(param)

        if isinstance(param, Path) and param.is_dir():
            files = param.iterdir()
        elif isinstance(param, list) and isinstance(param[0], Dataset):
            self.files = []
            datasets = param
        else:
            # self.files = list(map(Path, param))
            datasets = []
            for path in param:
                ds = dcmread(path, stop_before_pixels=(not read_pixels))
                ds.from_path = Path(path)
                datasets.append(ds)

        self.verify(datasets)
        self.__datasets = self.sort_by_z(datasets)

    def save_as(self, pattern):
        pattern = str(pattern)
        if '*' not in pattern:
            raise Exception("Pattern must include a '*' wildcard.")
        for sc in self.__datasets:
            sc.save_as(pattern.replace('*', f'{sc.z_index:03}'))

    def sort_by_z(self, datasets):
        """
            Sort the dicoms along the orientation axis.
        """
        orientation = datasets[0].ImageOrientationPatient  # These will all be identical
        # Doesn't matter which one you use, we are moving relative to it
        start_position = np.asarray(datasets[0].ImagePositionPatient)

        normal = np.cross(orientation[0:3],  # A vector pointing along the ImageOrientation axis
                          orientation[3:6])

        self.axis_x = orientation[0:3]
        self.axis_y = orientation[3:6]
        self.axis_z = normal

        zs = {}
        for ds in datasets:
            if not zs:  # the z-value of the dicom at the start position will be zero
                zs[ds.SOPInstanceUID] = 0
            else:  # the z-value of every other dicom is relative to that
                pos = np.asarray(ds.ImagePositionPatient)
                # calculate the displacement along the normal (might be negative)
                z = np.dot(pos - start_position, normal)
                zs[ds.SOPInstanceUID] = z

        # actually sort by the calculated z values
        sorted_by_z = sorted(datasets, key=lambda x: zs[x.SOPInstanceUID])

        z_spacing = np.abs(np.linalg.norm(
            np.asarray(sorted_by_z[1].ImagePositionPatient)-np.asarray(sorted_by_z[0].ImagePositionPatient)))

        for k in range(len(sorted_by_z)):
            sorted_by_z[k].z_index = k
            sorted_by_z[k].z_spacing = z_spacing
        return sorted_by_z

    def verify(self, datasets):
        def attr_same(l, attr):
            return all(getattr(x, attr) == getattr(l[0], attr) for x in l)

        tags_equal = ['ImageOrientationPatient',
                      'SeriesInstanceUID',
                      'FrameOfReferenceUID', 'Rows', 'Columns', 'SpacingBetweenSlices']
        if not all(attr_same(datasets, attr) for attr in tags_equal):
            raise Exception(
                f"Not a volume: tags [{', '.join(tags_equal)}] must be present and identical")
        for tag in tags_equal:
            setattr(self, tag, getattr(datasets[0], tag))

    def __getitem__(self, key):
        return self.__datasets[key]

    def __len__(self):
        return self.__datasets.__len__()

    def get(self, key):
        return self.__datasets.get(key)

    def __iter__(self):
        return self.__datasets.__iter__()

    def __next__(self):
        return self.__datasets.__next__()

    def __repr__(self) -> str:
        return f"<Volume {self.__datasets[0].Rows}x{self.__datasets[0].Columns}x{len(self.__datasets)} -> {self.axis_z}>"
        # return self.__datasets.__repr__()


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

    def get(self, key, default=None):
        return self.__annotation_sets.get(key, default)

    def __repr__(self) -> str:
        return self.__annotation_sets.__repr__()

    def __contains__(self, k):
        return self.__annotation_sets.__contains__(k)


class Annotations():
    def __init__(self, ellipses, arrows, reference_dataset):
        self.ellipses = ellipses
        self.arrows = arrows
        if type(reference_dataset) is str:
            reference_dataset = dcmread(reference_dataset)

        self.reference = reference_dataset
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

    @ classmethod
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
