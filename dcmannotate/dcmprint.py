#!/usr/bin/python3
from pydicom import dcmread
import sys

ds = dcmread(sys.argv[1])
print(ds)
