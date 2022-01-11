from os import PathLike
from typing import (
    Any,
    Dict,
    Iterator,
    KeysView,
    List,
    Optional,
    Union,
    ValuesView,
)
from pydicom.dataset import Dataset
from pydicom.sr.codedict import codes
from pydicom import dcmread

from .measurements import *
from itertools import chain


class Annotations:
    ellipses: List[Ellipse]
    arrows: List[PointMeasurement]
    reference: Dataset
    SOPInstanceUID: str

    def __init__(
        self, measurements: List[Measurement], reference_dataset: Union[Dataset, str]
    ):
        self.ellipses = [k for k in measurements if isinstance(k, Ellipse)]
        self.arrows = [k for k in measurements if isinstance(k, PointMeasurement)]
        if isinstance(reference_dataset, (str, PathLike)):
            reference_dataset = dcmread(reference_dataset)
        assert isinstance(reference_dataset, Dataset)

        self.reference = reference_dataset
        self.SOPInstanceUID = reference_dataset.SOPInstanceUID

    def __iter__(self) -> Iterator[Measurement]:
        yield from self.ellipses
        yield from self.arrows

    def __contains__(self, measurement: Measurement) -> bool:
        return measurement in self.ellipses or measurement in self.arrows

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Annotations):
            raise NotImplementedError

        if (
            self.reference != other.reference
            or self.SOPInstanceUID != other.SOPInstanceUID
        ):
            return False

        for m in self:
            if m not in other:
                return False

        for m in other:
            if m not in self:
                return False
        return True

    def __repr__(self) -> str:
        return (
            "<"
            + self.SOPInstanceUID
            + ": "
            + [self.ellipses + self.arrows].__repr__() # type: ignore
            + ">"
        )


class AnnotationSet:
    def __init__(self, annotations_list: List[Annotations]):
        self.__annotation_sets: Dict[Any, Annotations] = {}
        self.__list = annotations_list
        series_uid = annotations_list[0].reference.SeriesInstanceUID
        for set_ in annotations_list:
            if set_.SOPInstanceUID in self.__annotation_sets:
                raise ValueError("Two Annotations must not reference the same dataset.")
            if (
                set_.reference.SeriesInstanceUID is None
                or set_.reference.SeriesInstanceUID != series_uid
            ):
                raise ValueError(
                    "All Annotations in an AnnotationSet must reference the same series."
                )
            self.__annotation_sets[set_.SOPInstanceUID] = set_

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AnnotationSet):
            raise NotImplementedError
        return self.__list == other.__list

    def keys(self) -> KeysView[Any]:
        return self.__annotation_sets.keys()

    def values(self) -> ValuesView[Annotations]:
        return self.__annotation_sets.values()

    def __iter__(self) -> Iterator[Annotations]:
        yield from self.__list

    # def __next__(self):
    #     return self.__list.__next__()

    def __getitem__(self, key: Any) -> Annotations:
        return self.__annotation_sets[key]

    def get(
        self, key: Any, default: Optional[Annotations] = None
    ) -> Optional[Annotations]:
        return self.__annotation_sets.get(key, default)

    def __repr__(self) -> str:
        return self.__annotation_sets.__repr__()

    def __contains__(self, k: Any) -> bool:
        return self.__annotation_sets.__contains__(k)
