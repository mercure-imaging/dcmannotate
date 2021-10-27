#!/usr/bin/python3
import time
import os
from generate_test_series import generate_series
from pathlib import Path
from pydicom import dcmread
import pydicom
import sys
import pathlib
import zlib
import random
import pydicom
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.sequence import Sequence
from pydicom.uid import generate_uid

from jinja2 import Environment, FileSystemLoader
from jinja2 import StrictUndefined

from annotations import *
import hashlib


pydicom.datadict.add_private_dict_entries('Visage',
                                          {0x00711062: ('OB', '1', 'AnnotationData'),
                                           0x00711064: ('OB', '1', 'ViewsData'),
                                           0x00711065: ('ST', '1', 'ViewsDataVersion'),
                                           0x00711066: ('OB', '1', 'AnnotationReferences')})


class VisageWriter():
    def __init__(self):
        env = Environment(
            loader=FileSystemLoader(pathlib.Path(
                __file__).parent.resolve() / 'templates' / 'visage'),
            autoescape=True,
            undefined=StrictUndefined
        )
        env.globals['generate_uid'] = generate_uid
        self.template = env.get_template("base.xml")
        self.key_views = env.get_template("key_views.xml")

    def decode(self, t):
        return zlib.decompress(t[4:]).decode('utf-8')

    def encode(self, t):
        compressed = zlib.compress(t.encode('utf-8'))
        length = len(t)

        compressed = bytearray([0]*4)+bytearray(compressed)
        compressed[0] = (length & 0xff000000) >> 24
        compressed[1] = (length & 0x00ff0000) >> 16
        compressed[2] = (length & 0x0000ff00) >> 8
        compressed[3] = (length & 0x000000ff)

        if len(compressed) % 2 == 1:
            compressed.append(0)
        return bytes(compressed)

    def render_xml(self, annotationSet, desc=""):
        # reference_dataset, ellipses, arrows = (
        #     annotations.reference, annotations.ellipses, annotations.arrows)

        return self.template.render(annotation_set=annotationSet)

    def computeVolumeHash(self, datasets):
        m = hashlib.md5()
        for d in datasets:
            m.update(d.SOPInstanceUID.encode('utf-8'))
        return m.digest().hex().strip().upper()

    def generate(self, dcm_series, annotation_set):
        ex = dcm_series[0]
        # File meta info data elements
        file_meta = FileMetaDataset()
        file_meta.FileMetaInformationGroupLength = 202
        file_meta.FileMetaInformationVersion = b'\x00\x01'
        file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.11.1'
        file_meta.MediaStorageSOPInstanceUID = pydicom.uid.generate_uid(
            prefix='1.2.276.0.45.1.7.4.')
        file_meta.TransferSyntaxUID = '1.2.840.10008.1.2.1'
        file_meta.ImplementationClassUID = '1.2.276.0.45.1.1.0.71.20130122'
        file_meta.ImplementationVersionName = 'DicomWeb_71'

        # Main data elements
        ds = Dataset()
        ds.SpecificCharacterSet = 'ISO_IR 100'
        ds.InstanceCreationDate = '20211018'  # TODO
        ds.InstanceCreationTime = '170058'  # TODO
        ds.SOPClassUID = '1.2.840.10008.5.1.4.1.1.11.1'
        ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
        ds.StudyDate = ex.StudyDate
        ds.StudyTime = ex.StudyTime

        ds.SeriesDate = ds.InstanceCreationDate
        ds.SeriesTime = ds.InstanceCreationTime

        ds.AccessionNumber = ex.AccessionNumber
        ds.Modality = 'PR'
        ds.Manufacturer = 'Visage PR'  # TODO
        ds.ReferringPhysicianName = ex.get('ReferringPhysicianName') or ''
        ds.StudyDescription = ex.get('StudyDescription') or ''
        ds.SeriesDescription = 'Visage Presentation State'
        ds.PatientName = ex.PatientName
        ds.PatientID = ex.PatientID
        ds.PatientBirthDate = ex.PatientBirthDate
        ds.PatientSex = ex.PatientSex
        ds.SoftwareVersions = '7.1.16 (Build 3355)'  # TODO
        ds.PatientPosition = ex.get('PatientPosition') or ''
        ds.StudyInstanceUID = ex.StudyInstanceUID
        ds.SeriesInstanceUID = pydicom.uid.generate_uid(
            prefix='1.2.276.0.45.1.7.3.')
        ds.StudyID = ex.StudyID
        ds.SeriesNumber = '9950'  # TODO
        ds.InstanceNumber = '1'
        ds.RescaleIntercept = ex.get('RescaleIntercept', '0')
        ds.RescaleSlope = ex.get('RescaleIntercept', '1')
        ds.RescaleType = ex.get('RescaleType', 'US')
        ds.ContentLabel = 'VISAGE_PR'
        ds.ContentDescription = 'Visage Presentation State'
        ds.PresentationCreationDate = ds.InstanceCreationDate
        ds.PresentationCreationTime = ds.InstanceCreationTime
        ds.ContentCreatorName = ''
        ds.PresentationLUTShape = 'IDENTITY'
        ds.file_meta = file_meta
        ds.is_implicit_VR = False
        ds.is_little_endian = True

        # Referenced Series Sequence
        refd_series_sequence = Sequence()
        ds.ReferencedSeriesSequence = refd_series_sequence

        # Referenced Series Sequence: Referenced Series 1
        refd_series1 = Dataset()

        # Referenced Image Sequence
        refd_image_sequence = Sequence()
        refd_series1.ReferencedImageSequence = refd_image_sequence

        first = True
        for r in dcm_series:
            refd_image = Dataset()
            refd_image.ReferencedSOPClassUID = r.SOPClassUID
            refd_image.ReferencedSOPInstanceUID = r.SOPInstanceUID
            if first:
                refd_image[(0x71, 0x10)] = pydicom.DataElement(
                    (0x71, 0x10), 'LO', 'Visage')
                refd_image[(0x71, 0x1061)] = pydicom.DataElement(
                    (0x71, 0x1061), 'UT', self.computeVolumeHash(dcm_series))
                refd_image[(0x71, 0x1062)] = pydicom.DataElement(
                    (0x71, 0x1062), 'OB', self.encode(self.render_xml(annotation_set)))
                refd_image[(0x71, 0x1063)] = pydicom.DataElement(
                    (0x71, 0x1063), 'ST', '1.0.0.0')
                # these aren't necessary
                # refd_image[(0x71, 0x1064)] = pydicom.DataElement(
                #     (0x71, 0x1064), 'OB', self.encode(self.key_views.render(datasets=dcm_series)))
                refd_image[(0x71, 0x1065)] = pydicom.DataElement(
                    (0x71, 0x1065), 'ST', '0.1.0.0')

                ref_sequence = pydicom.Sequence()
                for r in dcm_series:
                    d = Dataset()
                    d.ReferencedSOPInstanceUID = r.SOPInstanceUID
                    ref_sequence.append(d)
                refd_image[(0x71, 0x1066)] = pydicom.DataElement(
                    (0x71, 0x1066), 'SQ', ref_sequence
                )

                first = False
            refd_image_sequence.append(refd_image)

        refd_series1.SeriesInstanceUID = ex.SeriesInstanceUID

        refd_series_sequence.append(refd_series1)

        # Softcopy VOI LUT Sequence
        softcopy_voilut_sequence = Sequence()
        ds.SoftcopyVOILUTSequence = softcopy_voilut_sequence

        ds.ImageHorizontalFlip = ex.get('ImageHorizontalFlip', 'N')
        ds.ImageRotation = ex.get('ImageRotation', 0)

        # Displayed Area Selection Sequence
        displayed_area_selection_sequence = Sequence()
        ds.DisplayedAreaSelectionSequence = displayed_area_selection_sequence

        # Displayed Area Selection Sequence: Displayed Area Selection 1
        displayed_area_selection1 = Dataset()

        # Referenced Image Sequence
        refd_image_sequence = Sequence()
        for r in dcm_series:
            # Referenced Image Sequence
            refd_image = Dataset()
            refd_image.ReferencedSOPClassUID = r.SOPClassUID
            refd_image.ReferencedSOPInstanceUID = r.SOPInstanceUID
            refd_image_sequence.append(refd_image)

        displayed_area_selection1.ReferencedImageSequence = refd_image_sequence

        displayed_area_selection1.DisplayedAreaTopLeftHandCorner = [1, 1]
        displayed_area_selection1.DisplayedAreaBottomRightHandCorner = [
            512, 512]  # todo
        displayed_area_selection1.PresentationSizeMode = 'SCALE TO FIT'
        displayed_area_selection1.PresentationPixelSpacing = [1, 1]
        # displayed_area_selection1.PresentationPixelAspectRatio = [1.0, 1.0]
        displayed_area_selection_sequence.append(displayed_area_selection1)

        return ds


# folder = "/vagrant/test_annotations"
# generate_series(folder, 1)
# time.sleep(1)
# datasets = [dcmread(x)
#             for x in Path(folder).glob("*.dcm")]
# annotations = Annotations([Ellipse(Point(256, 128), Point(256, 370), Point(
#     128, 256), Point(370, 256), unit='Millimeter', value=1234)],
#     [PointMeasurement(0, 0, 'Millimeter', 100),
#      PointMeasurement(512, 512, 'Millimeter', 10000),
#      PointMeasurement(0, 512, 'Millimeter', 10000),
#      PointMeasurement(512, 0, 'Millimeter', 1000000),
#      PointMeasurement(256, 256, 'Millimeter', 1000000)], datasets[0])
# aset = AnnotationSet([annotations])
# print(aset)

datasets = [dcmread('/vagrant/julia-volume/slice.0.dcm'),
            dcmread('/vagrant/julia-volume/slice.1.dcm'),
            dcmread('/vagrant/julia-volume/slice.2.dcm')]
aset = AnnotationSet([Annotations([Ellipse.from_center(Point(255, 255), 50, 50, 'mm', 0)], [], datasets[0]),
                      Annotations([Ellipse.from_center(
                          Point(255, 255), 40, 40, 'mm', 0)], [], datasets[1]),
                      Annotations([Ellipse.from_center(Point(255, 255), 30, 30, 'mm', 0)], [], datasets[2])])
writer = VisageWriter()

# print(writer.render_xml(aset))
result = writer.generate(datasets, aset)
result.save_as(f"/vagrant/julia-volume/annotations-gen.dcm")
os.system(f"dcmodify -gin /vagrant/julia-volume/annotations-gen.dcm")
# # print(result)
