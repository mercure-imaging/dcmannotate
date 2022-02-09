from typing import Any
from dcmannotate import serialization, readers
from dcmannotate.__main__ import read, parse_and_run
from collections import namedtuple

from dcmannotate.dicomvolume import DicomVolume

ReadArgs = namedtuple("ReadArgs", ["annotation_files", "volume_files"])

WriteArgs = namedtuple("WriteArgs", ["format", "annotations", "volume_files", "destination"])


def test_cli_read(input_volume_annotated: DicomVolume, tmpdir: Any) -> None:
    in_dir = tmpdir.mkdir(f"data_in")
    input_volume_annotated.save_as(str(in_dir / "slice.*.dcm"))

    for format in ["sr", "visage", "sc"]:
        print(f"Testing {format}.")
        out_dir = tmpdir.mkdir(f"data_{format}")

        files = getattr(input_volume_annotated, f"write_{format}")(
            str(out_dir / "slice.*.dcm")
        )
        volume_files = None
        if format == "visage":
            files = [files]
            volume_files = input_volume_annotated.files

        result_a = parse_and_run(
            ["read", "-i", str(out_dir / "slice.*.dcm"), "-v", str(in_dir / "slice.*.dcm")]
        )
        assert isinstance(result_a, str)
        result_b = read(ReadArgs(files, volume_files))

        # print(json.dumps(json.loads(result_a), sort_keys=True, indent=4))
        # print(json.dumps(json.loads(result_b), sort_keys=True, indent=4))
        assert serialization.read_annotations_from_json(
            input_volume_annotated, result_a
        ) == serialization.read_annotations_from_json(input_volume_annotated, result_b)
        # assert result_a == result_b
        deserialized = serialization.read_annotations_from_json(
            input_volume_annotated, result_b
        )
        assert input_volume_annotated.annotation_set == deserialized


def test_cli_write(input_volume_annotated: DicomVolume, tmpdir: Any) -> None:
    in_dir = tmpdir.mkdir(f"data_in")
    volume_files = input_volume_annotated.save_as(str(in_dir / "slice.*.dcm"))

    k = serialization.AnnotationEncoder()
    serialized = k.encode(input_volume_annotated.annotation_set)
    for format in ["sr", "sc", "visage"]:
        out_dir = tmpdir.mkdir(f"data_{format}")
        # result_files = write(
        #     WriteArgs(format, serialized, volume_files, str(tmpdir / "slice.*.dcm"))
        # )
        result_files: Any = parse_and_run(
            [
                "write",
                format,
                "-i",
                str(in_dir / "slice.*.dcm"),
                "-o",
                str(out_dir / "slice.*.dcm"),
                "-a",
                serialized,
            ]
        )
        assert isinstance(result_files, list)
        if format == "visage":
            result_files = result_files[0]

        read_annotations = getattr(readers, format).read_annotations(
            input_volume_annotated, result_files
        )
        assert input_volume_annotated.annotation_set == read_annotations
