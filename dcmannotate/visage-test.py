#!/usr/bin/python3
# type: ignore
import os
import zlib
from pydicom import dcmread
import pydicom


def decode(t):
    return zlib.decompress(t[4:]).decode("utf-8")


def encode(t):
    compressed = zlib.compress(t.encode("utf-8"))
    length = len(t)

    compressed = bytearray([0] * 4) + bytearray(compressed)
    compressed[0] = (length & 0xFF000000) >> 24
    compressed[1] = (length & 0x00FF0000) >> 16
    compressed[2] = (length & 0x0000FF00) >> 8
    compressed[3] = length & 0x000000FF

    if len(compressed) % 2 == 1:
        compressed.append(0)
    return bytes(compressed)


def encode_for_dicom(t):
    enc_bytes = encode(t)
    return "/".join(f"{k:02x}" for k in enc_bytes)


def test(k):
    decoded = encode(decode(k))
    return k == decoded


pydicom.datadict.add_private_dict_entries(
    "Visage",
    {
        0x00711062: ("OB", "1", "AnnotationData", "Annotation data"),
        0x00711064: ("OB", "1", "ViewsData", "Views data"),
        0x00711065: ("ST", "1", "ViewsDataVersion", "Views data version"),
        0x00711066: ("OB", "1", "AnnotationReferences", "Annotation references"),
    },
)

# t = bytes.fromhex("00000376789c75534b8fdb2010bee75720df6303b6432c1156ab56957a58f590ddb3c53a5307958005e4f9eb0b8eb749565bcf651edf379e07c39f4e3b8d0ee0bcb26695911c67084c6737caf4abecedf5c77c993d891997c6d8204304f90774924ccc10ef94eb34440d71237780d426c633d43bbb1f56d97a2b07c8042f526c0475d6baf81319a0f5671f6097bc885ba77a6504c37983cb9a105cb10a35658e4b5cd2c5b22a4b84f3aa89df12377451135e4c94912e4fcab72711d9256e9230d2d488e47451d6558d598929cc3143981713f4463b8b39cd31ab28618cd5e5047cccf4c13bdff12e02a32839ad1715c1b42284b20976195b2dbeec95fb70be0e2c0d435b27081a25e1933946b432d01ed5266c05e5c59d35467f5b13d0bbd5d7597b7581a8444d05a955e75759dccdcb1aadb7a035faae7b147324ceb5ac7f05f0c1d9005d808d880dde8c714f0e6488d51c55df2b8753759367eca1b3c3d483dfda636b4d3b4827b506dd0e5a1af029e3ff42d72a3e52f03f703e2838fa6bbec96acd7ef70e7138bcf8e419d9f71cde83dd4170d3729cdca8bd176c99134a31634d451a5e4cde917c8fe7014ea11dac57e9918be7b7d75f2fcfaf3fbff1e23190a00e743c8503b4d274db7171f358de67ef2c6d7eba8af81e6e0724667f01d3ed0e3e00")
# doc = dcmread('/vagrant/IM00001.dcm')


def edit_donor():
    ds = dcmread("/vagrant/test_annotations/julia-annotate-donor.dcm")
    sequence = ds.ReferencedSeriesSequence[0].ReferencedImageSequence

    print(sequence[0])
    ds.SeriesNumber = "9794"
    original_value = sequence[0][(0x0071, 0x1062)].value

    print(decode(sequence[0][(0x0071, 0x1064)].value))
    # print(decode(sequence[0][(0x0071, 0x1062)].value))
    new_value = r"""<?xml version="1.0" encoding="UTF-8"?>
    <annotations version="1.0.0.0">
    <ellipse roi="1">
    <name id="1" group="ROI" appendix="2D"></name>
    <coordinate_system>
    <origin>1.9740447998 17.6970977783 0.5</origin>
    <axis_x>1 1.57042052251e-07 0</axis_x>
    <axis_y>-1.19442560731e-07 1 0</axis_y>
    <axis_z>0 0 1</axis_z>
    </coordinate_system>
    <style>
    <color>1 1 1 1</color>
    <line_width>2</line_width>
    <font bold="1" size="11" italics="0">MS Shell Dlg 2</font>
    </style>
    <label>ROI 1 (2D)</label>
    <protected>0</protected>
    <creator>wiggir01</creator>
    <scope>
    <show_on_parallel_planes>0</show_on_parallel_planes>
    </scope>
    <keyviews>
    <keyview_number>1</keyview_number>
    </keyviews>
    <geometry>
    <radius_x>17.05770874</radius_x>
    <radius_y>18.87789917</radius_y>
    </geometry>
    <text_position>AUTOMATIC</text_position>
    <relative_anchor>1 -1</relative_anchor>
    </ellipse>
    </annotations>
    """

    sequence[0][(0x0071, 0x1062)] = pydicom.DataElement(
        (0x71, 0x1062), "OB", encode(new_value)
    )  # encode(decode(original_value))
    ds.save_as("/vagrant/test_annotations/julia-annotate-donor-mod.dcm")
    os.system(
        f"dcmodify -gin -gse /vagrant/test_annotations/julia-annotate-donor-mod.dcm"
    )


# 'AF0492479C972440A898DB77B4F25666'

# sequence[0][(0x71, 0x1061)] = pydicom.DataElement(
#     (0x71, 0x1061), 'UT', 'AF0492479C972440A898DB77B4F25666')
# print(sequence[0])

# print(ds.ReferencedSeriesSequence[0].ReferencedImageSequence[1])
# ex_value = ds.ReferencedSeriesSequence[0].ReferencedImageSequence[1][
#     (
#         0x0071, 0x1064)]


# print(decode(ex_value))
# print(decode(ex_value))
# print(doc.get_private_item(0x71, 0x1062, 'Visage'))

# print(encode_for_dicom('foobar'))
# print(test(t))
