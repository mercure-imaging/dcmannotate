
from jinja2 import Environment, FileSystemLoader
from jinja2 import StrictUndefined

import highdicom as hd
import numpy as np
from PIL import Image, ImageDraw

from vector import Vector
import pathlib

from pydicom import dcmread
from pydicom.uid import generate_uid


class SRWriter():
    def __init__(self):
        env = Environment(
            loader=FileSystemLoader(pathlib.Path(
                __file__).parent.resolve() / 'templates'),
            autoescape=True,
            undefined=StrictUndefined
        )
        env.globals['generate_uid'] = generate_uid
        self.template = env.get_template("base")

    def generate_xml(self, reference_dataset, description, ellipses=[], arrows=[]):
        if type(reference_dataset) is str:
            reference_dataset = dcmread(reference_dataset)
        return self.template.render(reference=reference_dataset, description=description, arrows=arrows, ellipses=ellipses)


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
        xb = x1-vec.x*10
        yb = y1-vec.y*10

        # Draw the line without arrows
        xy = ((ptA.x, ptA.y), (xb, yb))
        draw.line(xy, width=width, fill=color)

        vtx0 = (xb+-vec.y*10, yb+vec.x*10)
        vtx1 = (xb+vec.y*10, yb+-vec.x*10)
        # draw.point((xb,yb), fill=(255,0,0))    # DEBUG: draw point of base in red - comment out draw.polygon() below if using this line
        # im.save('DEBUG-base.png')              # DEBUG: save

        # Now draw the arrowhead triangle
        draw.polygon((vtx0, vtx1, (ptB.x, ptB.y)), fill=color)

    def generate(self, reference_dataset, ellipses, arrows, window):
        if type(reference_dataset) is str:
            reference_dataset = dcmread(reference_dataset)

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
        windowed_image = np.tile(windowed_image[:, :, np.newaxis], [1, 1, 3])

        # Cast to a PIL image for easy drawing of boxes and text
        pil_image = Image.fromarray(windowed_image)
        draw_obj = ImageDraw.Draw(pil_image)

        for ellipse in ellipses:
            draw_obj.ellipse(
                ((ellipse.topleft.x, ellipse.topleft.y),
                 (ellipse.bottomright.x, ellipse.bottomright.y)),
                outline='red',
                fill=None,
                width=3
            )
            draw_obj.text(xy=[ellipse.right.x, ellipse.right.y],
                          text=f"{ellipse.value} {ellipse.unit.value}", fill='red')

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

            self.arrowedLine(draw_obj, start_point, arrow, width=3)
            draw_obj.text(xy=[start_point.x + text_offset[0], start_point.y + text_offset[1]],
                          text=text, fill='red')

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
        sc_image = hd.sc.SCImage.from_ref_dataset(
            ref_dataset=reference_dataset,
            pixel_array=pixel_array,
            photometric_interpretation=hd.PhotometricInterpretationValues.RGB,
            bits_allocated=8,
            coordinate_system=hd.CoordinateSystemNames.PATIENT,
            series_instance_uid=hd.UID(),
            sop_instance_uid=hd.UID(),
            series_number=100,
            instance_number=1,
            manufacturer='Manufacturer',
            pixel_spacing=getattr(reference_dataset, 'PixelSpacing', None),
            patient_orientation=patient_orientation
        )
        return sc_image
