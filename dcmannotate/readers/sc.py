from os import PathLike
from typing import Optional, Sequence, Union
import pydicom
from pydicom.dataset import Dataset
from pathlib import Path
from dcmannotate.annotations import AnnotationSet, AnnotationsParsed
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # avoid circular import
    from dcmannotate.dicomvolume import DicomVolume
from dcmannotate.serialization import AnnotationDecoder

pydicom.datadict.add_private_dict_entries(
    "dcmannotate",
    {
        0x00911000: (
            "UL",
            "1",
            "AnnotationDataVersion",
            "Annotation data version",
        ),
        0x00911001: ("LT", "1", "AnnotationData", "Annotation data"),
    },
)


def get_measurements(dataset: Union[Dataset, str, Path]) -> Optional[AnnotationsParsed]:
    ds: Dataset
    if isinstance(dataset, (str, PathLike)):
        ds = pydicom.dcmread(dataset)
    else:
        ds = dataset

    try:
        block = ds.private_block(0x0091, "dcmannotate")
    except KeyError:
        raise KeyError(
            "Private creator 'dcmannotate' not found. This may not be a file created by dcmannotate."
        )
    version = block[0x00].value
    if version != 1:
        raise ValueError(f"Unknown annotation serialization version {version}")

    return parse_annotations(block[0x01].value)


def parse_annotations(json: str) -> Optional[AnnotationsParsed]:
    d = AnnotationDecoder()
    result = d.decode(json)
    if not isinstance(result, AnnotationsParsed):
        if result in ("", {}, None):
            return None
        else:
            raise Exception(f"Unexpected annotation data: {json}")
    return result


def read_annotations(
    volume: "DicomVolume",
    sc_files: Union["DicomVolume", Sequence[Union[Dataset, str, Path]]],
) -> AnnotationSet:
    annotations = []
    for f in sc_files:
        measurements = get_measurements(f)
        if measurements is None:
            continue
        for s in volume:
            if s.SOPInstanceUID == measurements.SOPInstanceUID:
                # measurements.reference = s
                annotations.append(measurements.with_reference(s))
                break
        else:
            raise Exception("ReferencedSOPInstanceUID for this SC does not exist in volume.")
    return AnnotationSet(annotations)
