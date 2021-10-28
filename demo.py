#!/usr/bin/python3
import random
import os
from dcmannotate import *
from pydicom import dcmread
from pathlib import Path
in_path = Path('/vagrant/julia-volume-2')

in_files = list(Path(in_path).glob('slice.*.dcm'))
random.shuffle(in_files)
datasets = DicomVolume(in_files)

a_slice_1 = Annotations([Ellipse.from_center(Point(128, 256), 128, 72, 'Millimeter', 1),
                         Ellipse.from_center(
    Point(128, 256), 48, 48, 'Millimeter', 2),
    Ellipse.from_center(
    Point(64, 256), 64, 64, 'Millimeter', 3),
    Ellipse.from_center(
    Point(192, 256), 64, 64, 'Millimeter', 4)
], [PointMeasurement(128, 170, 'Millimeter', 100)], datasets[0])

a_slice_2 = Annotations([Ellipse.from_center(
    Point(256, 256), 20, 20, 'Millimeter', 1)], [], datasets[1])
a_slice_3 = Annotations([Ellipse.from_center(
    Point(256, 276), 30, 30, 'Millimeter', 1)], [], datasets[2])
a_slice_4 = Annotations([Ellipse.from_center(
    Point(256, 286), 40, 40, 'Millimeter', 1)], [], datasets[3])

aset = AnnotationSet([a_slice_1, a_slice_2, a_slice_3, a_slice_4])

sr_writer = SRWriter()
sc_writer = SecondaryCaptureWriter()
visage_writer = VisageWriter()

sr_result = sr_writer.generate_xml(a_slice_1, "")

sc_result = sc_writer.generate(a_slice_1, [0, 1])
sc_result.save_as(in_path / 'demo_result_sc.dcm')

visage_result = visage_writer.generate(datasets, aset)
print(visage_writer.render_xml(aset))
visage_result.save_as(in_path / 'demo_result_visage.dcm')
os.system(f"dcmodify {in_path / 'demo_result_visage.dcm'}")
# k=SRWriter()
# print(k.generate_xml('mandel.dcm', 'demo', ellipses=ellipses))


# generator.Ellipse()
