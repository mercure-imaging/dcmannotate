#!/usr/bin/python3
import hashlib
import pathlib
import zlib
from datetime import datetime
from typing import TYPE_CHECKING

import pydicom

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.sequence import Sequence
from pydicom.uid import generate_uid

from dcmannotate.annotations import AnnotationSet

if TYPE_CHECKING:
    from dcmannotate.dicomvolume import DicomVolume  # pragma: no cover

pydicom.datadict.add_private_dict_entries(
    "Visage",
    {
        0x00711062: ("OB", "1", "AnnotationData", "Annotation data"),
        0x00711064: ("OB", "1", "ViewsData", "Views data"),
        0x00711065: ("ST", "1", "ViewsDataVersion", "Views data version"),
        0x00711066: (
            "OB",
            "1",
            "AnnotationReferences",
            "Annotation references",
        ),
    },
)


env = Environment(
    loader=FileSystemLoader(
        pathlib.Path(__file__).parent.parent.resolve() / "templates" / "visage"
    ),
    autoescape=True,
    undefined=StrictUndefined,
)
env.globals["generate_uid"] = generate_uid
template = env.get_template("base.xml")


def decode(t: bytes) -> str:
    return zlib.decompress(t[4:]).decode("utf-8")


def encode(t: str) -> bytes:
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


def render_xml(annotationSet: "AnnotationSet") -> str:
    # reference_dataset, ellipses, arrows = (
    #     annotations.reference, annotations.ellipses, annotations.arrows)

    return template.render(annotation_set=annotationSet)


def volume_hash(datasets: "DicomVolume") -> str:
    m = hashlib.md5()
    for d in datasets:
        m.update(d.SOPInstanceUID.encode("utf-8"))
    return m.hexdigest().upper()


def generate(dcm_volume: "DicomVolume", annotation_set: AnnotationSet) -> Dataset:
    ex = dcm_volume[0]
    # File meta info data elements
    file_meta = FileMetaDataset()
    file_meta.FileMetaInformationGroupLength = 202
    file_meta.FileMetaInformationVersion = b"\x00\x01"
    file_meta.MediaStorageSOPClassUID = pydicom.uid.UID("1.2.840.10008.5.1.4.1.1.11.1")
    file_meta.MediaStorageSOPInstanceUID = pydicom.uid.generate_uid(
        prefix="1.2.276.0.45.1.7.4."
    )
    file_meta.TransferSyntaxUID = pydicom.uid.UID("1.2.840.10008.1.2.1")
    file_meta.ImplementationClassUID = pydicom.uid.UID("1.2.276.0.45.1.1.0.71.20130122")
    file_meta.ImplementationVersionName = "DicomWeb_71"

    dt = datetime.now()
    # Main data elements
    ds = Dataset()
    # Genuinely no idea why Dataset() doesn't include a default preamble
    # 128*b'\0' would be fine, but let's just borrow it from the original.
    ds.preamble = getattr(ex, "preamble", 128 * b"\0")
    ds.SpecificCharacterSet = "ISO_IR 100"
    ds.InstanceCreationDate = dt.strftime("%Y%m%d")
    ds.InstanceCreationTime = dt.strftime("%H%M%S")
    ds.SOPClassUID = "1.2.840.10008.5.1.4.1.1.11.1"
    ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
    ds.StudyDate = ex.StudyDate
    ds.StudyTime = ex.StudyTime

    ds.SeriesDate = ds.InstanceCreationDate
    ds.SeriesTime = ds.InstanceCreationTime

    ds.AccessionNumber = ex.AccessionNumber
    ds.Modality = "PR"
    ds.Manufacturer = "Visage PR"  # TODO
    ds.ReferringPhysicianName = ex.get("ReferringPhysicianName") or ""
    ds.StudyDescription = ex.get("StudyDescription") or ""
    ds.SeriesDescription = "Visage Presentation State"
    ds.PatientName = ex.PatientName
    ds.PatientID = ex.PatientID
    ds.PatientBirthDate = ex.PatientBirthDate
    ds.PatientSex = ex.PatientSex
    ds.SoftwareVersions = "7.1.16 (Build 3355)"  # TODO
    ds.PatientPosition = ex.get("PatientPosition") or ""
    ds.StudyInstanceUID = ex.StudyInstanceUID
    ds.SeriesInstanceUID = pydicom.uid.generate_uid(prefix="1.2.276.0.45.1.7.3.")
    ds.StudyID = ex.StudyID
    ds.SeriesNumber = "9950"  # TODO
    ds.InstanceNumber = "1"
    ds.RescaleIntercept = ex.get("RescaleIntercept", "0")
    ds.RescaleSlope = ex.get("RescaleIntercept", "1")
    ds.RescaleType = ex.get("RescaleType", "US")
    ds.ContentLabel = "VISAGE_PR"
    ds.ContentDescription = "Visage Presentation State"
    ds.PresentationCreationDate = ds.InstanceCreationDate
    ds.PresentationCreationTime = ds.InstanceCreationTime
    ds.ContentCreatorName = ""
    ds.PresentationLUTShape = "IDENTITY"
    file_meta.ImplementationClassUID = pydicom.uid.UID("1.2.276.0.7230010.3.0.3.6.2")
    file_meta.ImplementationVersionName = "OFFIS_DCMTK_362"
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
    for r in dcm_volume:
        refd_image = Dataset()
        refd_image.ReferencedSOPClassUID = r.SOPClassUID
        refd_image.ReferencedSOPInstanceUID = r.SOPInstanceUID
        if first:
            refd_image[(0x71, 0x10)] = pydicom.DataElement((0x71, 0x10), "LO", "Visage")
            refd_image[(0x71, 0x1061)] = pydicom.DataElement(
                (0x71, 0x1061), "UT", volume_hash(dcm_volume)
            )
            refd_image[(0x71, 0x1062)] = pydicom.DataElement(
                (0x71, 0x1062), "OB", encode(render_xml(annotation_set))
            )
            refd_image[(0x71, 0x1063)] = pydicom.DataElement((0x71, 0x1063), "ST", "1.0.0.0")
            # these aren't necessary
            # refd_image[(0x71, 0x1064)] = pydicom.DataElement(
            #     (0x71, 0x1064), 'OB', self.encode(self.key_views.render(datasets=dcm_series)))
            refd_image[(0x71, 0x1065)] = pydicom.DataElement((0x71, 0x1065), "ST", "0.1.0.0")

            ref_sequence = pydicom.Sequence()
            for r in dcm_volume:
                d = Dataset()
                d.ReferencedSOPInstanceUID = r.SOPInstanceUID
                ref_sequence.append(d)
            refd_image[(0x71, 0x1066)] = pydicom.DataElement(
                (0x71, 0x1066), "SQ", ref_sequence
            )

            first = False
        refd_image_sequence.append(refd_image)

    refd_series1.SeriesInstanceUID = ex.SeriesInstanceUID

    refd_series_sequence.append(refd_series1)

    # Softcopy VOI LUT Sequence
    softcopy_voilut_sequence = Sequence()
    ds.SoftcopyVOILUTSequence = softcopy_voilut_sequence

    ds.ImageHorizontalFlip = ex.get("ImageHorizontalFlip", "N")
    ds.ImageRotation = ex.get("ImageRotation", 0)

    # Displayed Area Selection Sequence
    displayed_area_selection_sequence = Sequence()
    ds.DisplayedAreaSelectionSequence = displayed_area_selection_sequence

    # Displayed Area Selection Sequence: Displayed Area Selection 1
    displayed_area_selection1 = Dataset()

    # Referenced Image Sequence
    refd_image_sequence = Sequence()
    for r in dcm_volume:
        # Referenced Image Sequence
        refd_image = Dataset()
        refd_image.ReferencedSOPClassUID = r.SOPClassUID
        refd_image.ReferencedSOPInstanceUID = r.SOPInstanceUID
        refd_image_sequence.append(refd_image)

    displayed_area_selection1.ReferencedImageSequence = refd_image_sequence

    displayed_area_selection1.DisplayedAreaTopLeftHandCorner = [1, 1]
    displayed_area_selection1.DisplayedAreaBottomRightHandCorner = [
        ex.Columns,
        ex.Rows,
    ]
    displayed_area_selection1.PresentationSizeMode = "SCALE TO FIT"
    displayed_area_selection1.PresentationPixelSpacing = [1, 1]
    # displayed_area_selection1.PresentationPixelAspectRatio = [1.0, 1.0]
    displayed_area_selection_sequence.append(displayed_area_selection1)

    ds.fix_meta_info()
    return ds
