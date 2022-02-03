from os import PathLike

from typing import (
    Any,
    Dict,
    Iterator,
    KeysView,
    List,
    Optional,
    Sequence as SequenceType,
    TYPE_CHECKING,
    Union,
    ValuesView,
)

from pydicom import dcmread
from pydicom.dataset import Dataset

from .measurements import Ellipse, Measurement, PointMeasurement

if TYPE_CHECKING:
    from .dicomvolume import DicomVolume


class Annotations:
    """Annotations for a slice."""

    ellipses: List[Ellipse]
    arrows: List[PointMeasurement]
    reference: Dataset
    SOPInstanceUID: str

    def __init__(
        self,
        measurements: SequenceType[Measurement],
        reference_dataset: Union[Dataset, str],
    ):
        self.ellipses = [k for k in measurements if isinstance(k, Ellipse)]
        self.arrows = [k for k in measurements if isinstance(k, PointMeasurement)]

        if isinstance(reference_dataset, (str, PathLike)):
            reference_dataset = dcmread(reference_dataset)

        assert isinstance(reference_dataset, Dataset)
        self.SOPInstanceUID = reference_dataset.SOPInstanceUID
        self.reference = reference_dataset

    def __iter__(self) -> Iterator[Measurement]:
        yield from self.ellipses
        yield from self.arrows

    def __contains__(self, measurement: Measurement) -> bool:
        return measurement in self.ellipses or measurement in self.arrows

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Annotations):
            raise NotImplementedError

        if self.reference != other.reference or self.SOPInstanceUID != other.SOPInstanceUID:
            return False

        for m in self:
            if m not in other:
                return False

        for m in other:
            if m not in self:
                return False
        return True

    def __repr__(self) -> str:
        return "<" + self.SOPInstanceUID + ": " + (self.ellipses + self.arrows).__repr__() + ">"  # type: ignore

    def __json_serializable__(self) -> Dict[str, Any]:
        return {
            "arrows": self.arrows,
            "ellipses": self.ellipses,
            "reference_sop_uid": self.SOPInstanceUID,
        }


class AnnotationsParsed(Annotations):
    """Represents annotations for a slice as parsed. Unlike Annotations objects, it has no `reference` member."""

    def __init__(
        self,
        measurements: List[Measurement],
        reference_sop_uid: str,
    ):
        self.measurements = measurements
        self.ellipses = [k for k in measurements if isinstance(k, Ellipse)]
        self.arrows = [k for k in measurements if isinstance(k, PointMeasurement)]
        self.SOPInstanceUID = reference_sop_uid

    def with_reference(self, reference: Dataset) -> Annotations:
        """Return a real Annotations object with the reference dataset filled in.

        Args:
            reference (Dataset): The dataset representing the referenced slice.

        Returns:
            Annotations: The resulting Annotations object.
        """
        return Annotations(self.measurements, reference)


class AnnotationSet:
    """All the annotations for a particular volume, organized by slice."""

    def __init__(self, annotations_list: List[Annotations]):
        self.__annotations: Dict[Any, Annotations] = {}
        self.__list = sorted(annotations_list, key=lambda x: x.reference.z_index)
        series_uid = annotations_list[0].reference.SeriesInstanceUID
        for set_ in annotations_list:
            if set_.reference is None:
                raise ValueError(
                    "all Annotations in an AnnotationSet must have a reference dataset"
                )
            if set_.SOPInstanceUID in self.__annotations:
                raise ValueError("Two Annotations must not reference the same dataset.")
            if (
                set_.reference.SeriesInstanceUID is None
                or set_.reference.SeriesInstanceUID != series_uid
            ):
                raise ValueError(
                    "All Annotations in an AnnotationSet must reference the same series."
                )
            self.__annotations[set_.SOPInstanceUID] = set_

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AnnotationSet):
            raise NotImplementedError
        return self.__list == other.__list

    def keys(self) -> KeysView[Any]:
        return self.__annotations.keys()

    def values(self) -> ValuesView[Annotations]:
        return self.__annotations.values()

    def __iter__(self) -> Iterator[Annotations]:
        yield from self.__list

    # def __next__(self):
    #     return self.__list.__next__()

    def __getitem__(self, key: Any) -> Annotations:
        return self.__annotations[key]

    def get(self, key: Any, default: Optional[Annotations] = None) -> Optional[Annotations]:
        return self.__annotations.get(key, default)

    def __repr__(self) -> str:
        return self.__annotations.__repr__()

    def __contains__(self, k: Any) -> bool:
        return self.__annotations.__contains__(k)

    def __json_serializable__(self) -> List[Annotations]:
        return self.__list


class AnnotationSetParsed:
    def __init__(self, annotations_list: List[AnnotationsParsed]):
        self.__list = annotations_list

    def with_reference(self, volume: "DicomVolume") -> "AnnotationSet":
        annotations: List[Annotations] = []
        for a in self.__list:
            for s in volume:
                if s.SOPInstanceUID == a.SOPInstanceUID:
                    # measurements.reference = s
                    annotations.append(a.with_reference(s))
                    break
            else:
                raise Exception(
                    "ReferencedSOPInstanceUID for this SC does not exist in volume."
                )

        return AnnotationSet(annotations)
