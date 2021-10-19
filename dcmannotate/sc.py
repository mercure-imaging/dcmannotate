#!/usr/bin/python3

import highdicom as hd
import numpy as np
from pydicom import dcmread
from PIL import Image, ImageDraw
import sys

def generate(reference_dataset, ellipses, window):
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
            ((ellipse.topleft.x,ellipse.topleft.y),
            (ellipse.bottomright.x,ellipse.bottomright.y)),
        outline='red',
        fill=None,
        width=3
        )
        draw_obj.text(xy=[ellipse.bottomright.x, ellipse.bottomright.y], text=f"{ellipse.value} {ellipse.unit.value}", fill='red')

    # Convert to numpy array
    pixel_array = np.array(pil_image)

    # The patient orientation defines the directions of the rows and columns of the
    # image, relative to the anatomy of the patient.  In a standard CT axial image,
    # the rows are oriented leftwards and the columns are oriented posteriorly, so
    # the patient orientation is ['L', 'P']
    patient_orientation=['L', 'P']

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
        pixel_spacing=getattr(reference_dataset,'PixelSpacing',None),
        patient_orientation=patient_orientation
    )
    return sc_image