#!/usr/bin/python3
# type: ignore

import os
import zlib
from pydicom import dcmread
import pydicom
import sys


def decode(t):
    return zlib.decompress(t[4:]).decode("utf-8")


ds = dcmread(sys.argv[1])
sequence = ds.ReferencedSeriesSequence[0].ReferencedImageSequence[0]


annotation_data = decode(sequence[(0x0071, 0x1062)].value)
views_data = decode(sequence[(0x0071, 0x1064)].value)

print(sequence)
print("VolumeHash", sequence[(0x0071, 0x1061)].value)
print(annotation_data)
print(views_data)
