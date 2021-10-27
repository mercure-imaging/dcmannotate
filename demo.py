#!/usr/bin/python3
import os
from dcmannotate import *
from pydicom import dcmread
from pathlib import Path
in_path = Path('/vagrant/julia-volume')

datasets = [dcmread(in_path / 'slice.0.dcm'),
            dcmread(in_path / 'slice.1.dcm'),
            dcmread(in_path / 'slice.2.dcm')]

annotations = Annotations([Ellipse.from_center(Point(256, 256), 128, 72, 'Millimeter', 1),
                           Ellipse.from_center(
                               Point(256, 256), 64, 64, 'Millimeter', 2),
                           Ellipse.from_center(
                               Point(128, 256), 64, 64, 'Millimeter', 3),
                           Ellipse.from_center(
                               Point(384, 256), 64, 64, 'Millimeter', 4)
                           ], [PointMeasurement(256, 256, 'Millimeter', 100)], datasets[0])

aset = AnnotationSet([annotations])

sr_writer = SRWriter()
sc_writer = SecondaryCaptureWriter()
visage_writer = VisageWriter()

sr_result = sr_writer.generate_xml(annotations, "")

sc_result = sc_writer.generate(annotations, [0, 1])
sc_result.save_as(in_path / 'demo_result_sc.dcm')

visage_result = visage_writer.generate(datasets, aset)
visage_result.save_as(in_path / 'demo_result_visage.dcm')
os.system(f"dcmodify {in_path / 'demo_result_visage.dcm'}")
# k=SRWriter()
# print(k.generate_xml('mandel.dcm', 'demo', ellipses=ellipses))


# generator.Ellipse()
