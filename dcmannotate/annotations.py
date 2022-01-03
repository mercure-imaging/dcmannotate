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
        if type(reference_dataset) is str:
            reference_dataset = dcmread(reference_dataset)
        assert isinstance(reference_dataset, Dataset)

        self.reference = reference_dataset
        self.SOPInstanceUID = reference_dataset.SOPInstanceUID


class AnnotationSet:
    def __init__(self, annotations_list: List[Annotations]):
        self.__annotation_sets: Dict[Any, Annotations] = {}
        self.__list = annotations_list
        series_uid = annotations_list[0].reference.SeriesInstanceUID
        for set_ in annotations_list:
            if set_.reference.SOPInstanceUID in self.__annotation_sets:
                raise ValueError("Two Annotations must not reference the same dataset.")
            if (
                set_.reference.SeriesInstanceUID is None
                or set_.reference.SeriesInstanceUID != series_uid
            ):
                raise ValueError(
                    "All Annotations in an AnnotationSet must reference the same series."
                )
            self.__annotation_sets[set_.reference.SOPInstanceUID] = set_

    def keys(self) -> KeysView[Any]:
        return self.__annotation_sets.keys()

    def values(self) -> ValuesView[Annotations]:
        return self.__annotation_sets.values()

    def __iter__(self) -> Iterator[Annotations]:
        return self.__list.__iter__()

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
