import argparse
import sys
from pathlib import Path
from typing import Any, List
from dcmannotate import serialization

from dcmannotate.annotations import AnnotationsParsed
from dcmannotate.serialization import AnnotationEncoder
from . import DicomVolume

from dcmannotate import readers
import pydicom
import logging
from .utils import annotation_format

log = logging.getLogger(f"{__package__}.{__name__}")


def log_config() -> logging.Logger:
    log.setLevel(logging.INFO)
    FORMAT = "%(levelname)s: %(message)s"
    formatter = logging.Formatter(FORMAT)
    # 2 handlers for the same logger:
    h1 = logging.StreamHandler(sys.stdout)
    h1.setLevel(logging.DEBUG)
    # filter out everything that is above INFO level (WARN, ERROR, ...)
    h1.addFilter(lambda record: record.levelno <= logging.INFO)
    h1.setFormatter(formatter)
    log.addHandler(h1)
    h2 = logging.StreamHandler(sys.stderr)
    # take only warnings and error logs
    h2.setLevel(logging.WARNING)
    h2.setFormatter(formatter)
    log.addHandler(h2)
    return log


def write(args: Any) -> None:
    in_files = maybe_glob(args.volume_files)
    volume = DicomVolume(in_files)

    if not args.annotations:
        annotations = "\n".join(sys.stdin.readlines())
    else:
        annotations = args.annotations
    annotation_set = serialization.read_annotations_from_json(volume, annotations)
    volume.annotate_with(annotation_set)

    if args.format == "sc":
        volume.write_sc(args.destination)
    elif args.format == "sr":
        volume.write_sr(args.destination)
    elif args.format == "visage":
        volume.write_visage(args.destination)
    else:
        log.error(f"Unsupported format {args.format}")
        exit(1)


def maybe_glob(path_list: List[Path]) -> List[Path]:
    if len(path_list) != 1:
        return path_list

    path = path_list[0]
    if str(path)[0] == "/":
        return list(Path("/").glob(str(path.relative_to("/"))))
    else:
        return list(Path(".").glob(str(path)))


def read(args: Any) -> None:
    if not args.annotation_files:
        log.fatal("No annotation files provided.")
        exit(1)
    in_files = maybe_glob(args.annotation_files)
    datasets = [pydicom.dcmread(f) for f in in_files]

    format = annotation_format(datasets)

    if format is None:
        log.fatal("Unable to detect annotation format. This may not be a dcmannotate file.")
        exit(1)

    annotations: Any = []

    if format == "sr":
        for d in datasets:
            measurements, sop_id = readers.sr.get_measurements(d)
            annotations.append(AnnotationsParsed(measurements, sop_id))

    elif format == "sc":
        for d in datasets:
            a = readers.sc.get_measurements(d)
            if a:
                annotations.append(a)
    elif format == "visage":
        if not args.volume_files:
            log.fatal(
                "Input appears to be a Visage PR. For these files, you must pass the original volume with -v"
            )
            exit(1)
        in_volume = DicomVolume(maybe_glob(args.volume_files))
        annotations = readers.visage.read_annotations(in_volume, in_files[0])
    k = AnnotationEncoder()
    print(k.encode(annotations))


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        "dcmannotate",
        description="Command-line interface to dcmannotate.",
        epilog="""Examples:
        python -m dcmannotate read -i ./slice_sr.*.dcm
        python -m dcmannotate read -i visage_pr.dcm -v slice.[0-9].dcm
        """,
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.set_defaults(func=lambda x: log.info(parser.format_help()))

    subparsers = parser.add_subparsers()

    write_parser = subparsers.add_parser("write", help="Write dicom annotations.")
    write_parser.add_argument(
        "format",
        choices=["sr", "sc", "visage"],
        help="Output format: Structured Report, Secondary Capture, or Visage",
    )
    write_parser.add_argument(
        "-i",
        "--volume-files",
        nargs="+",
        dest="volume_files",
        type=Path,
        help="Input volume paths. Accepts a list or a glob pattern.",
    )
    write_parser.add_argument(
        "-o",
        dest="destination",
        required=True,
        help="Output pattern or path, eg ./output/slice_annot.*.dcm or ./slice_visage.dcm",
    )
    write_parser.add_argument(
        "-a",
        "--annotations",
        nargs="?",
        dest="annotations",
        help="Annotations in JSON format. Omit to read from stdin.",
    )
    write_parser.set_defaults(func=write)

    read_parser = subparsers.add_parser("read", help="Read dicom annotations.")
    read_parser.add_argument(
        "-i",
        "--annotation-files",
        nargs="+",
        dest="annotation_files",
        type=Path,
        help="Annotation files to read. Accepts a list or a glob pattern.",
    )
    read_parser.add_argument(
        "-v",
        "--volume-files",
        nargs="+",
        dest="volume_files",
        type=Path,
        help="For Visage only: files corresponding to the referenced dicom volume. Accepts a list or a glob pattern.",
    )

    read_parser.set_defaults(func=read)
    return parser


def console_entry() -> None:
    log_config()
    args = make_parser().parse_args()
    args.func(args)  # call the default function


if __name__ == "__main__":
    console_entry()
