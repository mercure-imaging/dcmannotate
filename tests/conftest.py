from pathlib import Path
from typing import Any, List, cast

from pydicom.dataset import Dataset
from pydicom.sr.coding import Code


from dcmannotate import (
    generate_test_series,
    DicomVolume,
    Ellipse,
    Point,
    PointMeasurement,
    Annotations,
    AnnotationSet,
)
import pytest

from pydicom.sr.codedict import _CodesDict, codes

from dcmannotate import readers
from dcmannotate import serialization
from dcmannotate.serialization import AnnotationEncoder


@pytest.fixture(scope="module")
def input_series(tmpdir_factory: Any) -> List[Path]:
    tmpdir = tmpdir_factory.mktemp("data")
    return generate_test_series.generate_series(tmpdir, 5, [[1, 0, 0], [0, 1, 0]])


@pytest.fixture
def input_volume(input_series: List[Path]) -> DicomVolume:
    return DicomVolume(input_series)


@pytest.fixture
def input_annotation_set(input_volume: DicomVolume) -> AnnotationSet:
    a = Ellipse(Point(256, 256), 128, 128, None, "Finding 1")
    b = PointMeasurement(256, 256, "Millimeter", 200)
    c = PointMeasurement(256, 256, None, "Finding 2")
    slice0_annotations = Annotations(
        [a, b, c],
        input_volume[0],
    )

    e = Ellipse(Point(2, 2), 128, 128, "Millimeter", 1)
    f = PointMeasurement(1, 1, "Millimeter", 200)
    slice1_annotations = Annotations(
        [e, f],
        input_volume[1],
    )
    return AnnotationSet([slice0_annotations, slice1_annotations])


@pytest.fixture
def input_volume_annotated(
    input_volume: DicomVolume, input_annotation_set: AnnotationSet
) -> DicomVolume:
    input_volume.annotate_with(input_annotation_set)
    return input_volume
