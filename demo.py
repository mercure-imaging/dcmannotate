#!/usr/bin/env python3
import sys
from dcmannotate import (
    DicomVolume,
    Annotations,
    Ellipse,
    Point,
    PointMeasurement,
    AnnotationSet,
)
from pathlib import Path
from dcmannotate import generate_test_series

demo_path = Path(sys.argv[1] if len(sys.argv) > 1 else "./demo")

print("Writing test series... ", end="")
print(generate_test_series.generate_series(demo_path, 5))

in_files = list(demo_path.glob("slice.[0-9].dcm"))
volume = DicomVolume(in_files)
print(volume)
a_slice_1 = Annotations(
    [
        Ellipse(Point(128, 256), 72, 128, None, "Finding A"),
        Ellipse(Point(128, 256), 48, 48, "Millimeter", 2),
        Ellipse(Point(48, 256), 48, 48, "Millimeter", 3),
        # Ellipse(Point(192, 256), 64, 64, "SquareMillimeter", 4),
        PointMeasurement(128, 170, "Millimeter", 100),
        PointMeasurement(220, 320, None, "Finding B"),
    ],
    volume[0],
)

a_slice_2 = Annotations([Ellipse(Point(128, 256), 20, 20, "Millimeter", 1)], volume[1])
a_slice_3 = Annotations([Ellipse(Point(128, 276), 30, 30, "Millimeter", 1)], volume[2])
a_slice_4 = Annotations([Ellipse(Point(128, 296), 40, 40, "Millimeter", 1)], volume[3])

aset = AnnotationSet([a_slice_1, a_slice_2, a_slice_3, a_slice_4])
volume.annotate_with(aset)

print("Writing SR files... ", end="")
print(volume.write_sr())
print("Writing SC files... ", end="")
print(volume.write_sc(demo_path / "demo_slice_*_sc.dcm"))
print("Writing Visage file... ", end="")
print(volume.write_visage(demo_path / "demo_result_visage.dcm"))
print(f"Complete. Files written to {demo_path.absolute()}")
