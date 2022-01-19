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
    AnnotationSet
)
import pytest

from pydicom.sr.codedict import _CodesDict, codes

from dcmannotate import readers
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
def input_volume_annotated(input_volume: DicomVolume, input_annotation_set: AnnotationSet) -> DicomVolume:
    input_volume.annotate_with(input_annotation_set)
    return input_volume


def test_create_volume(input_series: List[Path]) -> None:
    print(input_series)
    volume = DicomVolume(input_series)
    assert len(volume) == 5


def test_create_annotation(input_volume: DicomVolume) -> None:
    assert input_volume.annotation_set is None
    a = Ellipse(Point(256, 256), 128, 128, "Millimeter", 1)
    b = PointMeasurement(256, 256, "Millimeter", 200)
    slice0_annotations = Annotations(
        [a, b],
        input_volume[0],
    )
    assert slice0_annotations.ellipses == [a]
    assert slice0_annotations.arrows == [b]
    assert slice0_annotations.SOPInstanceUID == input_volume[0].SOPInstanceUID

    slice1_annotations = Annotations(
        [Ellipse(Point(128, 128), 128, 128, "Millimeter", 1)],
        input_volume[1],
    )

    aset = AnnotationSet([slice0_annotations, slice1_annotations])
    assert input_volume[0].SOPInstanceUID in aset
    assert aset[input_volume[0].SOPInstanceUID] == slice0_annotations
    input_volume.annotate_with(aset)
    assert input_volume.annotation_set == aset


def verify_measurement(meas: Dataset, uid: Any, meas_obj: Any) -> None:
    assert type(codes.DCM) is _CodesDict
    assert meas.ConceptNameCodeSequence[0].CodeValue == codes.DCM.MeasurementGroup.value
    for k in meas.ContentSequence:
        if k.ValueType == "NUM":
            measurement = k
            break
    else:
        raise Exception()
    measurement_seq0 = measurement.ContentSequence[0]
    assert (
        measurement_seq0.ContentSequence[0]
        .ReferencedSOPSequence[0]
        .ReferencedSOPInstanceUID
        == uid
    )
    if meas_obj.unit is not None:
        assert measurement.MeasuredValueSequence[0].NumericValue == meas_obj.value
    else:  # no unit, look for a free text value
        for k in meas.ContentSequence:
            if k.ValueType == "CODE":
                el = k
                break
        else:
            raise Exception("Expected a free text annotation value")
        assert el.ConceptCodeSequence[0].CodeMeaning == meas_obj.value

    assert measurement_seq0.GraphicType in ("POINT", "ELLIPSE")
    if measurement_seq0.GraphicType == "POINT":
        assert measurement_seq0.GraphicData == [meas_obj.x, meas_obj.y]
    elif measurement_seq0.GraphicType == "ELLIPSE":
        ellipse = meas_obj
        assert measurement_seq0.GraphicData == [
            ellipse.top.x,
            ellipse.top.y,
            ellipse.bottom.x,
            ellipse.bottom.y,
            ellipse.left.x,
            ellipse.left.y,
            ellipse.right.x,
            ellipse.right.y,
        ]


def test_make_sr(input_volume_annotated: DicomVolume) -> None:
    assert type(codes.DCM) is _CodesDict
    srs = input_volume_annotated.make_sr()
    assert input_volume_annotated.annotation_set is not None
    assert len(srs) == 2
    sr = srs[0]
    assert len(sr.ContentSequence) == 5

    for k in sr.ContentSequence:
        if k.ConceptNameCodeSequence[0].CodeValue == codes.DCM.ImageLibrary.value:
            image_library = k
            break
    else:
        raise Exception()

    assert (
        image_library.ContentSequence[0]
        .ContentSequence[0]
        .ReferencedSOPSequence[0]
        .ReferencedSOPInstanceUID
        == input_volume_annotated[0].SOPInstanceUID
    )

    for k in sr.ContentSequence:
        if (
            k.ConceptNameCodeSequence[0].CodeValue
            == cast(Code, codes.DCM.ImagingMeasurements).value
        ):
            image_measurements = k
            break
    else:
        raise Exception()

    measurement_groups = image_measurements.ContentSequence
    slice0_uid = input_volume_annotated[0].SOPInstanceUID
    slice0_annotations = input_volume_annotated.annotation_set[slice0_uid]
    verify_measurement(
        measurement_groups[0],
        slice0_uid,
        slice0_annotations.arrows[0],
    )
    verify_measurement(
        measurement_groups[1],
        slice0_uid,
        slice0_annotations.arrows[1],
    )
    verify_measurement(
        measurement_groups[2],
        slice0_uid,
        slice0_annotations.ellipses[0],
    )


def test_roundtrip_sr(input_volume_annotated: DicomVolume) -> None:
    srs = input_volume_annotated.make_sr()
    read_annotations = readers.sr.read_annotations(input_volume_annotated, srs)
    assert input_volume_annotated.annotation_set == read_annotations


def test_roundtrip_sc(input_volume_annotated: DicomVolume) -> None:
    srs = input_volume_annotated.make_sc()
    read_annotations = readers.sc.read_annotations(input_volume_annotated, srs)
    assert input_volume_annotated.annotation_set == read_annotations


def test_from_json(input_volume: DicomVolume, input_annotation_set: AnnotationSet) -> None:
    k = AnnotationEncoder()
    json = k.encode(input_annotation_set)
    annotation_set = readers.sc.read_annotations_from_json(input_volume, json)
    assert annotation_set == input_annotation_set

# def test_make_sc(input_volume_annotated: DicomVolume) -> None:
#     sc = input_volume_annotated.make_sc()
#     assert len(sc) == 5
#     r = SCReader()
#     for k in sc:
#         try:
#             m = r.get_measurements(k)
#             print(m)
#         except KeyError:
#             pass


def test_make_visage(input_volume_annotated: DicomVolume) -> None:
    visage = input_volume_annotated.make_visage()


def test_roundtrip_visage(input_volume_annotated: DicomVolume) -> None:
    srs = input_volume_annotated.make_visage()
    read_annotations = readers.visage.read_annotations(
        input_volume_annotated, srs)
    assert input_volume_annotated.annotation_set == read_annotations


def test_invalid_annotations(tmpdir: str, input_volume: DicomVolume) -> None:
    a = Ellipse(Point(256, 256), 128, 128, "Millimeter", 1)
    b = PointMeasurement(256, 256, "Millimeter", 200)

    with pytest.raises(
        TypeError, match="Measurements with units must have a numeric value."
    ):
        Ellipse(Point(256, 256), 128, 128, "Millimeter", "Finding")

    slice0_annotations = Annotations(
        [a, b],
        input_volume[0],
    )

    other_volume = DicomVolume(
        generate_test_series.generate_series(
            tmpdir, 5, [[1, 0, 0], [0, -1, 0]])
    )
    slice1_annotations = Annotations(
        [a, b],
        other_volume[1],
    )
    with pytest.raises(ValueError, match=".*must not reference the same dataset.*"):
        AnnotationSet([slice0_annotations, slice0_annotations])

    with pytest.raises(ValueError, match=".*must reference the same series.*"):
        aset = AnnotationSet([slice0_annotations, slice1_annotations])

    with pytest.raises(
        ValueError, match=".*does not reference this DicomVolume's SeriesInstanceUID.*"
    ):
        aset = AnnotationSet([slice1_annotations])
        input_volume.annotate_with(aset)

    with pytest.raises(ValueError, match=".*already has annotations.*"):
        aset = AnnotationSet([slice0_annotations])
        input_volume.annotate_with(aset)
        input_volume.annotate_with(aset)
