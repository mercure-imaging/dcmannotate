import zlib
from os import PathLike
from pathlib import Path
from typing import Dict, List, TYPE_CHECKING, Union

import pydicom
from pydicom.dataset import Dataset
from pydicom.sr.codedict import codes

from dcmannotate import Ellipse, PointMeasurement
from dcmannotate.annotations import Annotations, AnnotationSet
from dcmannotate.utils import Point

if TYPE_CHECKING:  # avoid circular import
    from dcmannotate.dicomvolume import DicomVolume  # pragma: no cover
from defusedxml.ElementTree import fromstring as xml_from_string  # type: ignore

from dcmannotate.measurements import Measurement


def decode(t: bytes) -> str:
    return zlib.decompress(t[4:]).decode("utf-8")


def get_measurements(dataset: Union[Dataset, str, Path]) -> Dict[str, List[Measurement]]:
    """Retrieves measurements from this Visage dataset.

    Args:
        dataset (Union[Dataset, str, Path]): The dataset or a path to it

    Returns:
        Dict[str, List[Measurement]]: A dict with measurements keyed by ReferencedSOPInstanceUID
    """
    ds: Dataset
    if isinstance(dataset, (str, PathLike)):
        ds = pydicom.dcmread(dataset)
    else:
        ds = dataset

    data = ds.ReferencedSeriesSequence[0].ReferencedImageSequence[0][0x00711062]
    sop_uids = [
        k.ReferencedSOPInstanceUID
        for k in ds.ReferencedSeriesSequence[0].ReferencedImageSequence
    ]
    xml_data = xml_from_string(decode(data))
    measurements: Dict[str, List[Measurement]] = {
        sop_uids[z]: [] for z in range(len(sop_uids))
    }
    for measurement in xml_data:
        meas_type = measurement.tag
        origin = measurement.find("./coordinate_system/origin").text.split(" ")
        x, y = map(float, origin[0:2])
        z = float(origin[2])
        z_idx = int(z - 0.5)
        label = measurement.find("./label").text
        label_pieces = label.split(" ")
        value_str = " ".join(label_pieces[0:-1])
        unit = label_pieces[-1]
        unit_code = getattr(codes.UCUM, unit, None)
        value: Union[str, float]
        if unit_code is None:
            value = label
        else:
            value = float(value_str)

        if meas_type == "ellipse":
            rx = float(measurement.find("./geometry/radius_x").text)
            ry = float(measurement.find("./geometry/radius_y").text)
            measurement = Ellipse(Point(x, y), rx, ry, unit_code, value)
        elif meas_type == "text":
            measurement = PointMeasurement(x, y, unit_code, value)
        else:
            raise ValueError(f"Unknown measurement type {meas_type}")
        measurements[sop_uids[z_idx]].append(measurement)
    return measurements


def read_annotations(
    volume: "DicomVolume",
    visage_file: Union[Dataset, str, Path],
) -> AnnotationSet:
    """Read annotations in and verify that they reference the volume.

    Args:
        volume (DicomVolume): The volume being annotated
        sr_files (Dataset | str | Path): The annotation file.

    Returns: AnnotationSet
    """
    measurement_sets = get_measurements(visage_file)
    annotations = []
    for sop_uid, measurements in measurement_sets.items():
        if len(measurements) == 0:
            continue
        for s in volume:
            if s.SOPInstanceUID == str(sop_uid):
                annotations.append(Annotations(measurements, s))
                break
        else:
            raise Exception(
                "ReferencedSOPInstanceUID for this measurement does not exist in volume."
            )
    return AnnotationSet(annotations)
