from typing import (
    Any,
    Dict,
    Iterator,
    List,
    Optional,
    Sequence,
    Union,
)
import numpy as np  # type: ignore
from pathlib import Path
import pydicom
from pydicom.dataset import Dataset
from pydicom import dcmread

from .writers import SRWriter, SecondaryCaptureWriter
from .measurements import *

# from . import writers
from .visage import VisageWriter
import tempfile


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # https://mypy.readthedocs.io/en/latest/runtime_troubles.html#using-classes-that-are-generic-in-stubs-but-not-at-runtime
    import os

    PathLike = os.PathLike[str]
else:
    from os import PathLike


class DicomVolume:

    ImageOrientationPatient: str
    SeriesInstanceUID: str
    FrameOfReferenceUID: str
    Rows: int
    Columns: int
    SpacingBetweenSlices: Any

    annotation_set: Optional["AnnotationSet"]
    files: List[Path]

    def __init__(
        self,
        datasets: Union[Sequence[Dataset], Sequence[PathLike]],
        annotations: Optional["AnnotationSet"] = None,
        read_pixels: bool = True,
    ) -> None:
        self.load(datasets, read_pixels)
        self.annotation_set = annotations

    def annotate_with(self, annotation_set: "AnnotationSet") -> None:
        self.annotation_set = annotation_set

    def load(
        self,
        param: Union[Sequence[Dataset], Sequence[PathLike]],
        read_pixels: bool = True,
    ) -> None:
        if isinstance(param, list) and isinstance(param[0], Dataset):
            self._load_dsets(param)
            return

        datasets: List[Dataset] = []
        for path in param:
            # assert isinstance(path, PathLike)
            ds = dcmread(path, stop_before_pixels=(not read_pixels))
            ds.from_path = Path(path)
            datasets.append(ds)
        self._load_dsets(datasets)

    def _load_dsets(self, datasets: List[Dataset]) -> None:
        self.verify(datasets)
        self.__datasets = self.sort_by_z(datasets)

    def make_sc(self) -> "DicomVolume":
        if self.annotation_set is None:
            raise Exception("There are no annotations for this volume.")
        sc_writer = SecondaryCaptureWriter()
        pydicom.config.INVALID_KEYWORD_BEHAVIOR = "IGNORE"
        try:
            sc_result = sc_writer.generate(self, self.annotation_set, [0, 1])
            return DicomVolume(sc_result)
        finally:
            pydicom.config.INVALID_KEYWORD_BEHAVIOR = "WARN"

    def write_sc(self, pattern: Union[str, Path]) -> List[Path]:
        return self.make_sc().save_as(pattern)

    def make_sr(self) -> List[Dataset]:
        with tempfile.TemporaryDirectory() as dir:
            files = self.write_sr(dir + "/" + "slice.*.dcm")
            return [dcmread(f) for f in files]

    def write_sr(self, pattern: Optional[str] = None) -> List[Path]:
        if self.annotation_set is None:
            raise Exception("There are no annotations for this volume.")

        sr_writer = SRWriter()
        return sr_writer.generate_dicoms(self.annotation_set, pattern)

    def make_visage(self) -> Dataset:
        if self.annotation_set is None:
            raise Exception("There are no annotations for this volume.")
        visage_writer = VisageWriter()
        return visage_writer.generate(self, self.annotation_set)

    def write_visage(self, filepath: Union[str, Path]) -> Path:
        self.make_visage().save_as(filepath)
        return Path(filepath)

    def save_as(self, pattern: Union[str, PathLike]) -> List[Path]:
        pattern = str(pattern)
        if "*" not in pattern:
            raise Exception("Pattern must include a '*' wildcard.")
        files = []
        for sc in self.__datasets:
            filename = pattern.replace("*", f"{sc.z_index:03}")
            sc.save_as(filename)
            files.append(Path(filename))
        return files

    def sort_by_z(self, datasets: List[Dataset]) -> List[Dataset]:
        """
        Sort the dicoms along the orientation axis.
        """
        orientation = datasets[0].ImageOrientationPatient  # These will all be identical
        # Doesn't matter which one you use, we are moving relative to it
        start_position = np.asarray(datasets[0].ImagePositionPatient)

        normal = np.cross(
            orientation[0:3],  # A vector pointing along the ImageOrientation axis
            orientation[3:6],
        )

        self.axis_x = orientation[0:3]
        self.axis_y = orientation[3:6]
        self.axis_z = normal

        zs: Dict[str, float] = {}
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

        z_spacing = np.abs(
            np.linalg.norm(
                np.asarray(sorted_by_z[1].ImagePositionPatient)
                - np.asarray(sorted_by_z[0].ImagePositionPatient)
            )
        )

        for k in range(len(sorted_by_z)):
            sorted_by_z[k].z_index = k
            sorted_by_z[k].z_spacing = z_spacing
        return sorted_by_z

    def verify(self, datasets: List[Dataset]) -> None:
        def attr_same(l: List[Any], attr: str) -> bool:
            return all(getattr(x, attr) == getattr(l[0], attr) for x in l)

        tags_equal = [
            "ImageOrientationPatient",
            "SeriesInstanceUID",
            "FrameOfReferenceUID",
            "Rows",
            "Columns",
            "SpacingBetweenSlices",
        ]
        if not all(attr_same(datasets, attr) for attr in tags_equal):
            raise Exception(
                f"Not a volume: tags [{', '.join(tags_equal)}] must be present and identical"
            )
        for tag in tags_equal:
            setattr(self, tag, getattr(datasets[0], tag))

    def __getitem__(self, key: int) -> Dataset:
        return self.__datasets[key]

    def __len__(self) -> int:
        return self.__datasets.__len__()

    # def get(self, key) -> Dataset:
    #     return self.__datasets.get(key)

    def __iter__(self) -> Iterator[Dataset]:
        return self.__datasets.__iter__()

    # def __next__(self):
    #     return self.__datasets.__next__()

    def __repr__(self) -> str:
        return f"<Volume {self.Rows}x{self.Columns}x{len(self)} -> {self.axis_z}>"


from .annotations import AnnotationSet
