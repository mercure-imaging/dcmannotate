#!/usr/bin/python3

import datetime
from pathlib import Path
import os
from numpy.core.arrayprint import DatetimeFormat
import pydicom
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.sequence import Sequence
from pydicom.uid import generate_uid
import sys
import numpy as np
import random
import string
# File meta info data elements


def mandelbrot(m=512, n=256):
    x = np.linspace(-2, 1, num=m).reshape((1, m))
    y = np.linspace(-1, 1, num=n).reshape((n, 1))
    C = np.tile(x, (n, 1)) + 1j * np.tile(y, (1, m))

    Z = np.zeros((n, m), dtype=complex)
    M = np.full((n, m), True, dtype=bool)
    for i in range(20):
        Z[M] = Z[M] * Z[M] + C[M]
        M[np.abs(Z) > 2] = False
    return M.astype(np.uint8)


def julia(arg, m=256, n=512):
    x = np.linspace(-1, 1, num=m).reshape((1, m))
    y = np.linspace(-2, 2, num=n).reshape((n, 1))
    C = np.tile(x, (n, 1)) + 1j * np.tile(y, (1, m))

    Z = np.zeros((n, m), dtype=complex)
    M = np.full((n, m), True, dtype=bool)
    K = np.full((n, m), 1, dtype=np.uint16)

    for i in range(20):
        C[M] = C[M] * C[M] + arg
        M[np.abs(C) > 2] = False
        # np.log(np.abs(C)+.1).astype('uint16'))
        np.putmask(K, np.abs(C) > 2, 0)
        # K[np.abs(C) > 2] = np.abs(C)
    return K


def nums(n):
    return ''.join(random.choice(string.digits) for i in range(n))


dt = datetime.datetime.now()


def generate_file(study, series, slice_number, acc, studyid, desc, image, orientation=[[1, 0, 0], [0, 1, 0]]):
    normal_vec = np.cross(orientation[0], orientation[1])

    file_meta = FileMetaDataset()
    file_meta.FileMetaInformationGroupLength = 200
    file_meta.FileMetaInformationVersion = b'\x00\x01'
    file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.4'

    file_meta.MediaStorageSOPInstanceUID = pydicom.uid.generate_uid(
        prefix='1.2.276.0.7230010.3.1.4.')
    file_meta.TransferSyntaxUID = '1.2.840.10008.1.2.1'
    file_meta.ImplementationClassUID = '1.2.276.0.7230010.3.0.3.6.2'
    file_meta.ImplementationVersionName = 'OFFIS_DCMTK_362'

    # Main data elements
    ds = Dataset()
    ds.preamble = 128*b'\0'
    ds.SOPClassUID = '1.2.840.10008.5.1.4.1.1.4'
    ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
    # pydicom.uid.generate_uid(
    #    prefix='1.2.276.0.7230010.3.1.4.')
    ds.StudyDate = dt.strftime('%Y%m%d')
    ds.StudyTime = dt.strftime('%H%M')
    ds.AccessionNumber = acc
    ds.Modality = 'MR'
    ds.PatientName = 'Julia^Set'
    ds.PatientID = 'JULIATEST'
    ds.PatientBirthDate = '19700101'
    ds.PatientSex = 'O'
    ds.StudyInstanceUID = study
    ds.SeriesInstanceUID = series
    ds.FrameOfReferenceUID = series
    ds.SeriesDescription = desc
    # ds.SeriesNumber = 1
    ds.InstanceNumber = str(slice_number+1)
    ds.StudyID = studyid
    ds.ImageComments = 'NOT FOR DIAGNOSTIC USE'
    ds.PatientPosition = 'HFS'
    ds.ImageOrientationPatient = [*orientation[0], *orientation[1]]
    ds.SpacingBetweenSlices = 7.5
    ds.ImagePositionPatient = list([0, 0, 0] +
                                   normal_vec*ds.SpacingBetweenSlices*slice_number)
    print(ds.ImagePositionPatient)
    ds.SliceLocation = 7.5*slice_number+170
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = 'MONOCHROME2\0'
    ds.SliceThickness = 5
    ds.PixelData = image.tobytes()
    ds.NumberOfFrames = "1"
    ds.Rows = np.size(image, 0)
    ds.Columns = np.size(image, 1)
    ds.PixelSpacing = [2, 2]
    ds.PixelAspectRatio = [1, 1]
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 0
    ds.file_meta = file_meta
    ds.is_implicit_VR = False
    ds.is_little_endian = True
    return ds


def generate_test_series(pt=-.3-0.j, n=10, orientation=[[1, 0, 0], [0, 1, 0]]):
    study = pydicom.uid.generate_uid(
        prefix='1.2.276.0.7230010.3.1.2.')
    series = pydicom.uid.generate_uid(
        prefix='1.2.276.0.7230010.3.1.3.')
    acc = nums(7)
    study = nums(8)
    datasets = []

    description = f'Julia set around {pt}'
    for i in range(n):
        pt_at = pt+.1j*(i-n/2)
        array = julia(pt_at)
        # print(array)
        datasets.append(generate_file(study, series, i, acc,
                        study, description, array, orientation))
    return datasets


def generate_series(f, n):
    Path(f).mkdir(parents=True, exist_ok=True)
    datasets = generate_test_series(.3-0.j, n)
    for i, d in enumerate(datasets):
        d.save_as(f+f"/slice.{i}.dcm")


if __name__ == "__main__":
    generate_series(sys.argv[1], int(sys.argv[2]))
# result.save_as(f'/vagrant/test_series/slice.{i}.dcm')
# ds.save_as(r'../mandel_from_codify.dcm', write_like_original=False)
