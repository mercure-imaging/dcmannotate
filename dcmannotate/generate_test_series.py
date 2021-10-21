#!/usr/bin/python3

import pydicom
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.sequence import Sequence
from pydicom.uid import generate_uid

import numpy as np
# File meta info data elements


def mandelbrot(m=512, n=512):
    x = np.linspace(-2, 1, num=m).reshape((1, m))
    y = np.linspace(-1, 1, num=n).reshape((n, 1))
    C = np.tile(x, (n, 1)) + 1j * np.tile(y, (1, m))

    Z = np.zeros((n, m), dtype=complex)
    M = np.full((n, m), True, dtype=bool)
    for i in range(20):
        Z[M] = Z[M] * Z[M] + C[M]
        M[np.abs(Z) > 2] = False
    return M.astype(np.uint8)


def julia(arg, m=512, n=512):
    x = np.linspace(-2, 2, num=m).reshape((1, m))
    y = np.linspace(-2, 2, num=n).reshape((n, 1))
    C = np.tile(x, (n, 1)) + 1j * np.tile(y, (1, m))

    Z = np.zeros((n, m), dtype=complex)
    M = np.full((n, m), True, dtype=bool)
    # print(Z)
    for i in range(20):
        C[M] = C[M] * C[M] + arg
        M[np.abs(C) > 2] = False
    return M.astype(np.uint8)


def generate_file(study, series, slice_number, image):
    file_meta = FileMetaDataset()
    file_meta.FileMetaInformationGroupLength = 200
    file_meta.FileMetaInformationVersion = b'\x00\x01'
    file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.4'
    file_meta.MediaStorageSOPInstanceUID = pydicom.uid.generate_uid(
        prefix='1.2.276.0.45.1.7.4.')
    file_meta.TransferSyntaxUID = '1.2.840.10008.1.2.1'
    file_meta.ImplementationClassUID = '1.2.276.0.7230010.3.0.3.6.2'
    file_meta.ImplementationVersionName = 'OFFIS_DCMTK_362'

    # Main data elements
    ds = Dataset()
    ds.SOPClassUID = '1.2.840.10008.5.1.4.1.1.4'
    ds.SOPInstanceUID = pydicom.uid.generate_uid(
        prefix='1.2.276.0.45.1.7.4.')
    ds.StudyDate = '20210101'
    ds.StudyTime = '0000'
    ds.AccessionNumber = '0000000'
    ds.Modality = 'MR'
    ds.PatientName = 'Unknown^'
    ds.PatientID = 'Unknown'
    ds.PatientBirthDate = '19700101'
    ds.PatientSex = 'O'
    ds.StudyInstanceUID = study
    ds.SeriesInstanceUID = series
    ds.SeriesNumber = 1
    ds.InstanceNumber = str(slice_number+1)
    ds.StudyID = '1111111'
    ds.ImageComments = 'NOT FOR DIAGNOSTIC USE'
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = 'MONOCHROME2'
    ds.PixelData = image.tobytes()
    ds.Rows = 512
    ds.Columns = 512
    ds.BitsAllocated = 8
    ds.BitsStored = 8
    ds.HighBit = 7
    ds.PixelRepresentation = 0
    ds.file_meta = file_meta
    ds.is_implicit_VR = False
    ds.is_little_endian = True
    return ds


study = pydicom.uid.generate_uid(
    prefix='1.2.276.0.45.1.7.3.')
series = pydicom.uid.generate_uid(
    prefix='1.2.276.0.45.1.7.3.')

for i in range(10):
    array = julia(-0.4j+.1j*i)
    result = generate_file(study, series, i, array)
    result.save_as(f'/vagrant/test_series/slice.{i}.dcm')
# ds.save_as(r'../mandel_from_codify.dcm', write_like_original=False)
