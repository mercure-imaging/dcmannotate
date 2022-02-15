import tempfile
import types
from pathlib import Path

from typing import Any, cast, Dict, Iterator, List, Optional, Sequence, TYPE_CHECKING, Union

import numpy as np  # type: ignore
import pydicom

from PIL import Image  # type: ignore
from pydicom import dcmread
from pydicom.dataset import Dataset

from dcmannotate import serialization

from . import readers, writers
from .annotations import Annotations, AnnotationSet
from .utils import annotation_format

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
        self.__load(datasets, read_pixels)
        self.annotation_set = annotations

    def annotate_with(
        self,
        annotation_set: "Union[AnnotationSet,List[Annotations]]",
        force: bool = False,
    ) -> None:
        """Annotate this dicom volume.

        Args:
            annotation_set (Union[AnnotationSet,List[Annotations]]):
                Supply a list of Annotations, or an instance of AnnotationSet
            force (bool, optional):
                Replace existing annotations, if any. Defaults to False.
        """
        if self.annotation_set and not force:
            raise ValueError(
                "This DicomVolume already has annotations. You must pass 'force=True' to replace them."
            )
        if type(annotation_set) is list:
            annotation_set = AnnotationSet(annotation_set)
        if not type(annotation_set) is AnnotationSet:
            raise ValueError(
                f"Unexpected annotation_set, expected AnnotationSet or List[Annotations], received {type(annotation_set)}"
            )
        for a in annotation_set:
            if a.reference and a.reference.SeriesInstanceUID != self.SeriesInstanceUID:
                raise ValueError(
                    "An Annotation does not reference this DicomVolume's SeriesInstanceUID."
                )
        self.annotation_set = annotation_set

    def annotate_from(
        self,
        datasets: Union[
            Dataset,
            "DicomVolume",
            Sequence[Union[Dataset, str, Path]],
            str,
            Path,
        ],
        force: bool = False,
    ) -> None:
        """Annotate this dicom volume with annotations from the provided dicom files or Datasets.

        Args:
            datasets (Sequence[Union[Dataset, str, Path]]): A list of dicom files or loaded datasets
            force (bool, optional): Replace existing annotations, if any. Defaults to False.
        """

        if isinstance(datasets, list) and isinstance(datasets[0], (str, Path)):
            datasets = [pydicom.dcmread(d) for d in datasets]
        elif isinstance(datasets, (str, Path)):
            datasets = pydicom.dcmread(datasets)
        format = annotation_format(datasets)  # type: ignore
        reader: types.ModuleType
        if format == "sr":
            reader = readers.sr
        elif format == "sc":
            reader = readers.sc
        elif format == "visage":
            reader = readers.visage
        else:
            raise Exception("Not a dcmannotate-formatted annotation file.")
        self.annotate_with(reader.read_annotations(self, datasets), force)

    def annotate_from_json(self, json: str, force: bool = False) -> None:
        """Annotate this dicom volume with annotations from the provided json string.

        Args:
            json (str): json-encoded annotations.
            force (bool, optional): Replace existing annotations, if any. Defaults to False.
        """
        self.annotate_with(serialization.read_annotations_from_json(self, json), force)

    def __load(
        self,
        param: Union[Sequence[Dataset], Sequence[PathLike]],
        read_pixels: bool = True,
    ) -> None:
        """Loads datasets from file paths if necessary.

        Args:
            param (Union[Sequence[Dataset], Sequence[PathLike]]): A list of datasets or paths.
            read_pixels (bool, optional):
                Read pixel data; usually want to do this but could be skipped in special cases.
                Defaults to True.
        """
        datasets: List[Dataset] = []
        if isinstance(param, list) and isinstance(param[0], Dataset):
            datasets = param
        else:
            for path in param:
                if param.count(path) > 1:
                    raise ValueError("A volume cannot reference the same file more than once.")
                # assert isinstance(path, PathLike)
                ds = dcmread(path, stop_before_pixels=(not read_pixels))
                ds.from_path = Path(path)
                datasets.append(ds)
        if len(datasets) < 2:
            raise ValueError("A volume must include at least two slices.")
        self.__verify(datasets)
        self.__datasets = self.sort_by_z(datasets)

    def make_sc(self) -> "DicomVolume":
        """Generate Dicom Secondary Capture datasets from attached annotations, returns a DicomVolume.

        Returns:
            DicomVolume: A DicomVolume with the resulting SC images as slices.
        """
        if self.annotation_set is None:
            raise Exception("There are no annotations for this volume.")
        pydicom.config.INVALID_KEYWORD_BEHAVIOR = "IGNORE"
        try:
            sc_result = writers.sc.generate(self, self.annotation_set, [0, 1])
            return DicomVolume(sc_result)
        finally:
            pydicom.config.INVALID_KEYWORD_BEHAVIOR = "WARN"

    def write_sc(
        self, pattern: Union[str, Path], *, force: Optional[bool] = False
    ) -> List[Path]:
        """Write out attached annotations as Dicom Secondary Capture files.

        Args:
            pattern (string): Pattern for output file names, eg "./out/slice_sr.*.dcm".

        Returns:
            List[Path]: A list of the created files.
        """

        return self.make_sc().save_as(pattern, force=force)

    def write_png(self, pattern: Union[str, Path]) -> List[Path]:
        volume = self.make_sc()
        files = []
        for slice in volume:
            im = Image.fromarray(slice.pixel_array)
            filename = str(pattern).replace("*", f"{slice.z_index:03}")
            im.save(filename, "png")

            files.append(Path(filename))
        return files

    def make_sr(self) -> List[Dataset]:
        """Generate Dicom Structured Report datasets from attached annotations.

        Returns:
            List[Dataset]: The generated datasets.
        """
        with tempfile.TemporaryDirectory() as dir:
            files = self.write_sr(dir + "/" + "slice.*.dcm")
            return [dcmread(f) for f in files]

    def write_sr(
        self, pattern: Optional[str] = None, *, force: Optional[bool] = False
    ) -> List[Path]:
        """Write out Dicom Structured Reports.

        Args:
            pattern (string, optional):
                Pattern for output file names, eg "./out/slice_sr.*.dcm".
                If None, uses input filenames as basis. Defaults to None.

        Raises:
            Exception: This volume must be annotated.

        Returns:
            List[Path]: A list of the created files.
        """
        if self.annotation_set is None:
            raise Exception("There are no annotations for this volume.")

        return writers.sr.generate(self.annotation_set, pattern, force=force)

    def make_visage(self) -> Dataset:
        """Generate Visage PR dataset from attached annotations.

        Returns:
            Dataset: The generated dataset.
        """

        if self.annotation_set is None:
            raise Exception("There are no annotations for this volume.")

        return writers.visage.generate(self, self.annotation_set)

    def write_visage(
        self, filepath: Union[str, Path], *, force: Optional[bool] = False
    ) -> Path:
        """Write out Visage PR file.

        Args:
            filepath (string): Output file names, eg "./out/visage.dcm"

        Returns:
            Path: The created file.
        """
        if Path(filepath).exists() and not force:
            raise FileExistsError(
                f"{filepath} already exists, aborting with no files written. Pass force=True to overwrite."
            )

        self.make_visage().save_as(filepath)
        return Path(filepath)

    def save_as(
        self, pattern: Union[str, PathLike], *, force: Optional[bool] = False
    ) -> List[Path]:
        """Write out this volume to files, slice by slice. Pass force=True to overwrite existing files.

        Args:
            pattern (str, Path): Pattern to use when writing files, eg "./out/slice_*.dcm"

        Returns:
            List[Path]: The created files.
        """

        pattern = str(pattern)
        if "*" not in pattern:
            raise Exception("Pattern must include a '*' wildcard.")
        files = [Path(pattern.replace("*", f"{sc.z_index:03}")) for sc in self.__datasets]

        if not force:
            for f in files:
                if f.exists():
                    raise FileExistsError(
                        f"{f} already exists, aborting with no files written. Pass force=True to overwrite."
                    )
        for sc, filename in zip(self.__datasets, files):
            sc.save_as(filename)
        self.files = files
        return files

    def sort_by_z(self, datasets: List[Dataset]) -> List[Dataset]:
        """
        Sort the given datasets along the orientation axis.
        """
        orientation = datasets[0].ImageOrientationPatient  # These will all be identical
        # Doesn't matter which one you use, we are moving relative to it
        start_position = np.asarray(datasets[0].ImagePositionPatient)

        normal = np.cross(
            # A vector pointing along the ImageOrientation axis
            orientation[0:3],
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

        def calc_spacing(i: int) -> float:
            return cast(
                float,
                np.abs(
                    np.linalg.norm(
                        np.asarray(sorted_by_z[i + 1].ImagePositionPatient)
                        - np.asarray(sorted_by_z[i].ImagePositionPatient)
                    )
                ),
            )

        spacings = set(calc_spacing(i) for i in range(len(sorted_by_z) - 1))
        if len(spacings) > 1:
            raise ValueError(
                f"Volume slices are not evenly spaced along the z-axis. The slice ImagePositionPatient z-values, relative to the first slice, appear to be {sorted(zs.values())}. Could a slice be missing?"
            )
        z_spacing = spacings.pop()

        for k in range(len(sorted_by_z)):
            sorted_by_z[k].z_index = k
            sorted_by_z[k].z_spacing = z_spacing
        return sorted_by_z

    def __verify(self, datasets: List[Dataset]) -> None:
        """Verifies that the given datasets appear to make up a single series.
            Additionally sets several tags on self as attributes, eg self.Columns, self.Rows.

        Args:
            datasets (List[Dataset]): The datasets to verify.
        """

        def attr_uniq(list: List[Any], attr: str) -> bool:
            """
            Returns True if all the values of the given attribute are unique.
            """
            return len(set([getattr(d, attr) for d in list])) == len(list)

        def attr_same(list: List[Any], attr: str) -> bool:
            return all(getattr(x, attr) == getattr(list[0], attr) for x in list)

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

        if not attr_uniq(datasets, "SOPInstanceUID"):
            raise ValueError(
                f"Duplicate SOPInstanceUID detected on volume. Possibly caused by a slice being accidentally included twice."
            )

    def __getitem__(self, key: int) -> Dataset:
        return self.__datasets[key]

    def __len__(self) -> int:
        return self.__datasets.__len__()

    def __iter__(self) -> Iterator[Dataset]:
        yield from self.__datasets

    def __repr__(self) -> str:
        return f"<Volume {self.Rows}x{self.Columns}x{len(self)} -> {self.axis_z}{', annotated' if self.annotation_set else ''}>"
