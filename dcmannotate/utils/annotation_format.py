
from typing import List, Union
from pydicom import Dataset
from typing import TYPE_CHECKING
if TYPE_CHECKING:  # avoid circular import
    from dcmannotate.dicomvolume import DicomVolume


def annotation_format(datasets: Union["DicomVolume", List[Dataset], Dataset]) -> str:
    if isinstance(datasets, Dataset):
        dataset = datasets
    else:
        dataset = datasets[0]

    try:
        block = dataset.private_block(0x0091, "dcmannotate")
        return "sc"
    except KeyError as e:
        pass

    if dataset.SOPClassUID == "1.2.840.10008.5.1.4.1.1.88.22" and dataset.CodingSchemeIdentificationSequence[0].CodingSchemeDesignator == "99dcmjs":
        return "sr"
    elif dataset.Manufacturer == "Visage PR":
        return "visage"
    return format
