from os import PathLike
from pathlib import Path
from typing import cast, List, Sequence, Tuple, TYPE_CHECKING, Union

import pydicom
from pydicom.dataset import Dataset
from pydicom.sr.codedict import _CodesDict, codes
from pydicom.sr.coding import Code

from dcmannotate import Ellipse, PointMeasurement
from dcmannotate.annotations import Annotations, AnnotationSet
from dcmannotate.utils import Point

if TYPE_CHECKING:  # avoid circular import
    from dcmannotate.dicomvolume import DicomVolume  # pragma: no cover
from dcmannotate.measurements import Measurement


def find_value_type(ds: Dataset, type: str) -> Dataset:
    """Iterate through a dataset with a ContentSequence to find a tag with the given ValueType.

    Args:
        ds (Dataset): Input dataset
        type (str): The ValueType we are looking for.

    Raises:
        ValueError: If we didn't find it.

    Returns:
        Dataset: The tag we found.
    """
    for k in ds.ContentSequence:
        if k.ValueType == type:
            assert isinstance(k, Dataset)
            return k
    raise ValueError(f"Expected to find ValueType {type}")


def find_content_items(sr: Dataset, code: Code) -> List[Dataset]:
    """Recursively hunt through a dataset to find content items with a particular code."""
    found_items = []
    for k in sr.ContentSequence:
        if (
            hasattr(k, "ConceptNameCodeSequence")
            and k.ConceptNameCodeSequence[0].CodeValue == code.value
        ):
            found_items.append(k)
        if hasattr(k, "ContentSequence"):
            found_items += find_content_items(k, code)
    return found_items


def get_measurements(dataset: Union[Dataset, str, Path]) -> Tuple[List[Measurement], str]:
    """Retrieves measurements from this SR dataset.

    Args:
        dataset (Union[Dataset, str, Path]): The dataset or a path to it

    Returns:
        Tuple[List[Measurement], str]: A list of measurements and the ReferencedSOPInstanceUID.
    """
    assert type(codes.DCM) is _CodesDict

    ds: Dataset
    if isinstance(dataset, (str, PathLike)):
        ds = pydicom.dcmread(dataset)
    else:
        ds = dataset
    measurement_groups = find_content_items(ds, cast(Code, codes.DCM.MeasurementGroup))
    result: List[Measurement] = []
    referenced_sop_instance_uid = ""
    for m in measurement_groups:
        n = find_value_type(m, "NUM")
        gtype = n.ContentSequence[0].GraphicType
        data = n.ContentSequence[0].GraphicData
        if not referenced_sop_instance_uid:
            referenced_sop_instance_uid = (
                find_value_type(n.ContentSequence[0], "IMAGE")
                .ReferencedSOPSequence[0]
                .ReferencedSOPInstanceUID
            )
        try:
            code = find_value_type(m, "CODE")
        except ValueError:
            code = None
        if code and code.ConceptCodeSequence[0].CodeValue == "CORNERSTONEFREETEXT":
            value = code.ConceptCodeSequence[0].CodeMeaning
            unit = None
        else:
            value = float(n.MeasuredValueSequence[0].NumericValue)
            unit = n.MeasuredValueSequence[0].MeasurementUnitsCodeSequence[0].CodeMeaning

        if gtype == "POINT":
            result.append(PointMeasurement(data[0], data[1], unit, value))
        if gtype == "ELLIPSE":
            result.append(
                Ellipse(
                    Point(data[0], data[5]),
                    (data[6] - data[4]) / 2.0,
                    (data[3] - data[1]) / 2.0,
                    unit,
                    value,
                )
            )
    return result, referenced_sop_instance_uid


def read_annotations(
    volume: Union["DicomVolume", Sequence[Dataset]],
    sr_files: Sequence[Union[Dataset, str, Path]],
) -> AnnotationSet:
    """Read annotations in and verify that they reference the volume.

    Args:
        volume (DicomVolume): The volume being annotated
        sr_files (Sequence[Dataset | str | Path]): The annotation files.

    Returns: AnnotationSet
    """
    assert len(sr_files) > 0
    annotations = []
    for f in sr_files:
        measurements, uid = get_measurements(f)
        for s in volume:
            if s.SOPInstanceUID == str(uid):
                annotations.append(Annotations(measurements, s))
                break
        else:
            raise Exception("ReferencedSOPInstanceUID for this SR does not exist in volume.")
    return AnnotationSet(annotations)
