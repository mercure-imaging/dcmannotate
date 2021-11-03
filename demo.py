#!/usr/bin/python3
import tempfile
import random
import os
from dcmannotate import *
from pydicom import dcmread
from pathlib import Path
in_path = Path('/vagrant/test_series_2')

in_files = list(Path(in_path).glob('slice.[0-9].dcm'))
volume = DicomVolume(in_files)

a_slice_1 = Annotations([Ellipse.from_center(Point(128, 256), 128, 72, 'Millimeter', 1),
                         Ellipse.from_center(
    Point(128, 256), 48, 48, 'Millimeter', 2),
    Ellipse.from_center(
    Point(64, 256), 64, 64, 'Millimeter', 3),
    Ellipse.from_center(
    Point(192, 256), 64, 64, 'Millimeter', 4)
], [PointMeasurement(128, 170, 'Millimeter', 100)], volume[0])

a_slice_2 = Annotations([Ellipse.from_center(
    Point(128, 256), 20, 20, 'Millimeter', 1)], [], volume[1])
a_slice_3 = Annotations([Ellipse.from_center(
    Point(128, 276), 30, 30, 'Millimeter', 1)], [], volume[2])
a_slice_4 = Annotations([Ellipse.from_center(
    Point(128, 296), 40, 40, 'Millimeter', 1)], [], volume[3])

aset = AnnotationSet([a_slice_1, a_slice_2, a_slice_3, a_slice_4])
volume.annotate_with(aset)
volume.write_sr()
volume.write_sc(in_path / "demo_slice_*_sc.dcm")
volume.write_visage(in_path / "demo_result_visage.dcm")

# sr_writer = SRWriter()
# sr_writer.generate_dicoms(aset)

# sc_writer = SecondaryCaptureWriter()
# sc_result = sc_writer.generate(volume, aset, [0, 1])
# sc_result.save_as(in_path / 'demo_slice_*_sc.dcm')

# visage_writer = VisageWriter()
# visage_result = visage_writer.generate(volume, aset)
# visage_result.save_as(in_path / 'demo_result_visage.dcm')

# dcmread(in_path / 'demo_result_visage.dcm')
# os.system(f"dcmodify {in_path / 'demo_result_visage.dcm'}")
