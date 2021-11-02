
from pathlib import Path
import tempfile
from subprocess import run, PIPE
from typing import Type
from jinja2 import Environment, FileSystemLoader
from jinja2 import StrictUndefined

import highdicom as hd
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .vector import Vector
import pathlib

from pydicom import dcmread
from pydicom.uid import generate_uid
from .annotations import AnnotationSet, DicomVolume, Point


class SRWriter():
    def __init__(self):
        env = Environment(
            loader=FileSystemLoader(pathlib.Path(
                __file__).parent.resolve() / 'templates' / 'tid1500'),
            autoescape=True,
            undefined=StrictUndefined
        )
        env.globals['generate_uid'] = generate_uid
        self.template = env.get_template("base.xml")

    def generate_slice_xml(self, annotations, description):
        reference_dataset, ellipses, arrows = (
            annotations.reference, annotations.ellipses, annotations.arrows)

        return self.template.render(reference=reference_dataset, description=description, arrows=arrows, ellipses=ellipses)

    def generate_dicoms(self, aset):
        xml_docs = self.generate_xml(aset)
        for annotations, xml in zip(aset, xml_docs):
            frompath = annotations.reference.from_path
            p = run(['xml2dsr', '-', str(frompath.with_name(frompath.stem+"_sr.dcm"))], stdout=PIPE,
                    input=xml, encoding='utf-8')

    def generate_xml(self, aset):
        return [self.generate_slice_xml(a, "") for a in aset]


class SecondaryCaptureWriter():

    def arrowedLine(self, draw, ptA, ptB, width=1, color='red'):
        """Draw line from ptA to ptB with arrowhead at ptB"""
        # Get drawing context

        # Now work out the arrowhead
        # = it will be a triangle with one vertex at ptB
        # - it will start at 95% of the length of the line
        # - it will extend 8 pixels either side of the line
        x0, y0 = (ptA.x, ptA.y)
        x1, y1 = (ptB.x, ptB.y)
        # Now we can work out the x,y coordinates of the bottom of the arrowhead triangle

        vec = Vector(ptB.x-ptA.x, ptB.y-ptA.y).normalize()
        xb = x1-vec.x*8
        yb = y1-vec.y*8

        # Draw the line without arrows
        xy = ((ptA.x, ptA.y), (xb, yb))
        draw.line(xy, width=width, fill=color)

        vtx0 = (xb+-vec.y*8, yb+vec.x*8)
        vtx1 = (xb+vec.y*8, yb+-vec.x*8)
        # draw.point((xb,yb), fill=(255,0,0))    # DEBUG: draw point of base in red - comment out draw.polygon() below if using this line
        # im.save('DEBUG-base.png')              # DEBUG: save

        # Now draw the arrowhead triangle
        draw.polygon((vtx0, vtx1, (ptB.x, ptB.y)), fill=color)

    def sc_from_ref(self, reference_dataset, pixel_array):
        sc = hd.sc.SCImage.from_ref_dataset(
            ref_dataset=reference_dataset,
            pixel_array=pixel_array,
            photometric_interpretation=hd.PhotometricInterpretationValues.RGB,
            bits_allocated=8,
            coordinate_system=hd.CoordinateSystemNames.PATIENT,
            series_instance_uid=hd.UID(),
            sop_instance_uid=hd.UID(),
            series_number=100,
            instance_number=getattr(reference_dataset, 'InstanceNumber', None),
            manufacturer='Manufacturer',
            pixel_spacing=getattr(reference_dataset, 'PixelSpacing', None),
            patient_orientation=getattr(
                reference_dataset, 'PatientOrientation', 'LP')
        )
        sc.ImageOrientationPatient = reference_dataset.ImageOrientationPatient
        sc.SpacingBetweenSlices = reference_dataset.SpacingBetweenSlices
        sc.ImagePositionPatient = reference_dataset.ImagePositionPatient
        sc.FrameOfReferenceUID = reference_dataset.FrameOfReferenceUID
        return sc

    def generate(self, volume, annotation_set, window=[0, 255]):
        if not isinstance(volume, DicomVolume):
            raise TypeError(
                f"Expected 'volume' to be instance of DicomVolume, not {type(volume)}")
        if not isinstance(annotation_set, AnnotationSet):
            raise TypeError(
                f"Expected 'annotation_set' to be instance of AnnotationSet, not {type(annotation_set)}")

        scs = []
        uid = hd.UID()
        for slice in volume:
            sc = None
            if slice.SOPInstanceUID in annotation_set:
                sc = self.generate_slice(
                    annotation_set[slice.SOPInstanceUID], window)
            else:
                sc = self.sc_from_ref(
                    slice, self.window_image(slice, window))
            sc.SeriesInstanceUID = uid
            scs.append(sc)
        return DicomVolume(scs)

    def window_image(self, reference_dataset, window):
        # Create an image for display by windowing the original image and drawing a
        # bounding box over it using Pillow's ImageDraw module
        slope = getattr(reference_dataset, 'RescaleSlope', 1)
        intercept = getattr(reference_dataset, 'RescaleIntercept', 0)
        original_image = reference_dataset.pixel_array * slope + intercept

        # Window the image to a soft tissue window (center 40, width 400)
        # and rescale to the range 0 to 255
        lower = window[0]
        upper = window[1]
        windowed_image = np.clip(original_image, lower, upper)
        windowed_image = (windowed_image - lower) * 255 / (upper - lower)
        windowed_image = windowed_image.astype(np.uint8)

        # Create RGB channels
        return np.tile(windowed_image[:, :, np.newaxis], [1, 1, 3])

    def generate_slice(self, annotations, window):
        reference_dataset, ellipses, arrows = (
            annotations.reference, annotations.ellipses, annotations.arrows)

        windowed_image = self.window_image(reference_dataset, window)
        # Cast to a PIL image for easy drawing of boxes and text
        pil_image = Image.fromarray(windowed_image)
        draw_obj = ImageDraw.Draw(pil_image)
        draw_obj.fontmode = "1"
        font = ImageFont.truetype(
            '/vagrant/UbuntuMono-Bold.ttf', 12)
        for ellipse in ellipses:
            draw_obj.ellipse(
                ((ellipse.topleft.x, ellipse.topleft.y),
                 (ellipse.bottomright.x, ellipse.bottomright.y)),
                outline='red',
                fill=None,
                width=3
            )

        for arrow in arrows:
            text = f"{arrow.value} {arrow.unit.value}"
            text_size = draw_obj.textsize(" "+text+" ")
            offset = Point(50, 50)
            start_point = arrow+offset
            text_offset = [0, 0]
            if start_point.x < 0 or start_point.x > pil_image.width:
                start_point.x = arrow.x - offset.x
            if start_point.y < 0 or start_point.y > pil_image.height:
                start_point.y = arrow.y - offset.y
                text_offset[1] = -11

            if start_point.x + text_size[0] > pil_image.width:
                text_offset[0] = pil_image.width - \
                    (start_point.x + text_size[0])

            self.arrowedLine(draw_obj, start_point, arrow, width=2)

        for arrow in arrows:
            draw_obj.text(xy=[start_point.x + text_offset[0], start_point.y + text_offset[1]],
                          text=text, fill='cyan', font=font)

        for ellipse in ellipses:
            draw_obj.text(xy=[int(ellipse.right.x), int(ellipse.right.y)],
                          text=f"{ellipse.value} {ellipse.unit.value}", fill='cyan', font=font)

            # Convert to numpy array
        pixel_array = np.array(pil_image)

        # The patient orientation defines the directions of the rows and columns of the
        # image, relative to the anatomy of the patient.  In a standard CT axial image,
        # the rows are oriented leftwards and the columns are oriented posteriorly, so
        # the patient orientation is ['L', 'P']
        patient_orientation = ['L', 'P']

        # Create the secondary capture image. By using the `from_ref_dataset`
        # constructor, all the patient and study information willl be copied from the
        # original image dataset
        sc_image = self.sc_from_ref(reference_dataset, pixel_array)
        return sc_image
