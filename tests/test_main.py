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


@pytest.fixture(scope="module")
def input_series(tmpdir_factory):
    tmpdir = tmpdir_factory.mktemp("data")
    return generate_test_series.generate_series(tmpdir, 5, [[1, 0, 0], [0, 1, 0]])


@pytest.fixture
def input_volume(input_series):
    return DicomVolume(input_series)


@pytest.fixture
def input_volume_annotated(input_volume):
    a = Ellipse(Point(256, 256), 128, 128, "Millimeter", 1)
    b = PointMeasurement(256, 256, "Millimeter", 200)
    slice0_annotations = Annotations(
        [a, b],
        input_volume[0],
    )

    c = Ellipse(Point(2, 2), 128, 128, "Millimeter", 1)
    d = PointMeasurement(1, 1, "Millimeter", 200)
    slice1_annotations = Annotations(
        [c, d],
        input_volume[1],
    )

    input_volume.annotate_with([slice0_annotations, slice1_annotations])
    return input_volume


def test_create_volume(input_series):
    print(input_series)
    volume = DicomVolume(input_series)
    assert len(volume) == 5


def test_create_annotation(input_volume):
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


def verify_measurement(meas, uid, meas_obj):
    assert meas.ConceptNameCodeSequence[0].CodeMeaning == "Measurement Group"
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
    assert measurement.MeasuredValueSequence[0].NumericValue == meas_obj.value
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


def test_make_sr(input_volume_annotated):
    srs = input_volume_annotated.make_sr()
    assert len(srs) == 2
    sr = srs[0]
    assert len(sr.ContentSequence) == 5

    for k in sr.ContentSequence:
        if k.ConceptNameCodeSequence[0].CodeMeaning == "Image Library":
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
        if k.ConceptNameCodeSequence[0].CodeMeaning == "Imaging Measurements":
            image_measurements = k
            break
    else:
        raise Exception()

    measurement_groups = image_measurements.ContentSequence

    slice0_annotations = input_volume_annotated.annotation_set[
        input_volume_annotated[0].SOPInstanceUID
    ]
    verify_measurement(
        measurement_groups[0],
        input_volume_annotated[0].SOPInstanceUID,
        slice0_annotations.arrows[0],
    )
    verify_measurement(
        measurement_groups[1],
        input_volume_annotated[0].SOPInstanceUID,
        slice0_annotations.ellipses[0],
    )


def test_make_sc(input_volume_annotated):
    sc = input_volume_annotated.make_sc()
    assert len(sc) == 5


def test_make_visage(input_volume_annotated):
    visage = input_volume_annotated.make_visage()


def test_invalid_annotations(tmpdir, input_volume):
    a = Ellipse(Point(256, 256), 128, 128, "Millimeter", 1)
    b = PointMeasurement(256, 256, "Millimeter", 200)
    slice0_annotations = Annotations(
        [a, b],
        input_volume[0],
    )

    other_volume = DicomVolume(
        generate_test_series.generate_series(tmpdir, 5, [[1, 0, 0], [0, -1, 0]])
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
