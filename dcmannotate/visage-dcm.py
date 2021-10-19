#!/usr/bin/python3
from pydicom import dcmread
import pydicom
import sys

import pydicom
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.sequence import Sequence


def write_base(ex, refs):
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
    ds.SOPInstanceUID = pydicom.uid.generate_uid(prefix='1.2.276.0.45.1.7.4.')
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
    ds.SeriesNumber = '9788'  # TODO
    ds.InstanceNumber = '1'
    ds.RescaleIntercept = ex.get('RescaleIntercept', '0.0')
    ds.RescaleSlope = ex.get('RescaleIntercept', '1.0')
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

    for r in refs:
        # Referenced Image Sequence: Referenced Image 1
        refd_image = Dataset()
        refd_image.ReferencedSOPClassUID = r.SOPClassUID
        refd_image.ReferencedSOPInstanceUID = r.SOPInstanceUID
        # refd_image.PrivateCreator = 'Visage'
        refd_image[(0x71, 0x10)] = pydicom.DataElement(
            (0x71, 0x10), 'LO', 'Visage')
        refd_image[(0x71, 0x1061)] = pydicom.DataElement(
            (0x71, 0x1061), 'UT', [0]*32)
        refd_image[(0x71, 0x1062)] = pydicom.DataElement(
            (0x71, 0x1062), 'OB', [0]*610)
        refd_image[(0x71, 0x1063)] = pydicom.DataElement(
            (0x71, 0x1063), 'ST', '1.0.0.0')
        refd_image[(0x71, 0x1064)] = pydicom.DataElement(
            (0x71, 0x1064), 'OB', [0]*262)
        refd_image[(0x71, 0x1065)] = pydicom.DataElement(
            (0x71, 0x1065), 'ST', '0.1.0.0')

        d = Dataset()
        d.ReferencedSOPInstanceUID = r.SOPInstanceUID
        refd_image[(0x71, 0x1066)] = pydicom.DataElement(
            (0x71, 0x1066), 'SQ', pydicom.Sequence(
                [d])
        )

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
    for r in refs:
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
    displayed_area_selection1.PresentationPixelAspectRatio = [1, 1]
    displayed_area_selection_sequence.append(displayed_area_selection1)

    return ds


ds = dcmread(sys.argv[1])

PR = write_base(ds, [ds, ds])
print(PR)
