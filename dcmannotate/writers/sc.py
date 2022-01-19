import math
import numpy as np  # type: ignore
from PIL import Image, ImageDraw, ImageFont  # type: ignore
from typing import Any, List,  Sequence

from pydicom.dataset import Dataset

import highdicom as hd
from highdicom.sc.sop import SCImage

from typing import TYPE_CHECKING


if TYPE_CHECKING:  # avoid circular import
    from dcmannotate.dicomvolume import DicomVolume

from dcmannotate.measurements import PointMeasurement, Point
from dcmannotate.annotations import Annotations, AnnotationSet
from dcmannotate.serialization import AnnotationEncoder


def arrowedLine(
    draw: ImageDraw,
    ptA: Point,
    ptB: PointMeasurement,
    width: int = 1,
    color: str = "red",
) -> None:
    """Draw line from ptA to ptB with arrowhead at ptB"""
    # Get drawing context

    # Now work out the arrowhead
    # = it will be a triangle with one vertex at ptB
    # - it will start at 95% of the length of the line
    # - it will extend 8 pixels either side of the line
    x0, y0 = (ptA.x, ptA.y)
    x1, y1 = (ptB.x, ptB.y)
    # Now we can work out the x,y coordinates of the bottom of the arrowhead triangle

    # generate a normalized vector from A to B
    vec = (ptB.x - ptA.x, ptB.y - ptA.y)
    vec_len = math.sqrt(sum(x * x for x in vec))
    vec = Point(vec[0] / vec_len, vec[1] / vec_len)

    xb = x1 - vec.x * 8
    yb = y1 - vec.y * 8

    # Draw the line without arrows
    xy = ((ptA.x, ptA.y), (x1 - vec.x * 2.0, y1 - vec.y * 2.0))
    draw.line(xy, width=width, fill=color)

    vtx0 = (xb + -vec.y * 8, yb + vec.x * 8)
    vtx1 = (xb + vec.y * 8, yb + -vec.x * 8)
    # draw.point((xb,yb), fill=(255,0,0))    # DEBUG: draw point of base in red - comment out draw.polygon() below if using this line
    # im.save('DEBUG-base.png')              # DEBUG: save

    # Now draw the arrowhead triangle

    draw.line(((ptB.x, ptB.y), vtx0), fill=color, width=2)
    draw.line(((ptB.x, ptB.y), vtx1), fill=color, width=2)


def sc_from_ref(reference_dataset: Dataset, pixel_array: Any) -> SCImage:
    sc = hd.sc.SCImage.from_ref_dataset(
        ref_dataset=reference_dataset,
        pixel_array=pixel_array,
        photometric_interpretation=hd.PhotometricInterpretationValues.RGB,
        bits_allocated=8,
        coordinate_system=hd.CoordinateSystemNames.PATIENT,
        series_instance_uid=hd.UID(),
        sop_instance_uid=hd.UID(),
        series_number=100,
        instance_number=getattr(reference_dataset, "InstanceNumber", 0),
        manufacturer="Manufacturer",
        pixel_spacing=getattr(reference_dataset, "PixelSpacing", None),
        patient_orientation=getattr(
            reference_dataset, "PatientOrientation", ("L", "P")
        ),
    )
    sc.ImageOrientationPatient = reference_dataset.ImageOrientationPatient
    sc.SpacingBetweenSlices = reference_dataset.SpacingBetweenSlices
    sc.ImagePositionPatient = reference_dataset.ImagePositionPatient
    sc.FrameOfReferenceUID = reference_dataset.FrameOfReferenceUID
    return sc


def generate(
    volume: "DicomVolume",
    annotation_set: AnnotationSet,
    window: List[int] = [0, 255],
) -> Sequence[SCImage]:
    # if not isinstance(volume, DicomVolume):
    #     raise TypeError(
    #         f"Expected 'volume' to be instance of DicomVolume, not {type(volume)}"
    #     )
    if not isinstance(annotation_set, AnnotationSet):
        raise TypeError(
            f"Expected 'annotation_set' to be instance of AnnotationSet, not {type(annotation_set)}"
        )

    scs = []
    uid = hd.UID()
    for slice in volume:
        sc = None
        pixels = None
        annotations = None
        if slice.SOPInstanceUID in annotation_set:
            annotations = annotation_set[slice.SOPInstanceUID]
            pixels = generate_pixels(
                annotations, window)
        else:
            pixels = window_image(slice, window)

        sc = sc_from_ref(slice, pixels)

        block = sc.private_block(0x0091, "dcmannotate", create=True)
        k = AnnotationEncoder()
        block.add_new(0, "UL", 1)
        if annotations:
            encoded = k.encode(annotations)
            block.add_new(1, "LT", encoded)
        else:
            block.add_new(1, "LT", "{}")
        sc.SeriesInstanceUID = uid
        scs.append(sc)
    return scs


def window_image(reference_dataset: Dataset, window: List[int]) -> Any:
    # Create an image for display by windowing the original image and drawing a
    # bounding box over it using Pillow's ImageDraw module
    slope = getattr(reference_dataset, "RescaleSlope", 1)
    intercept = getattr(reference_dataset, "RescaleIntercept", 0)
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


def generate_pixels(annotations: Annotations, window: List[int]) -> Any:
    reference_dataset, ellipses, arrows = (
        annotations.reference,
        annotations.ellipses,
        annotations.arrows,
    )

    windowed_image = window_image(reference_dataset, window)
    # Cast to a PIL image for easy drawing of boxes and text
    pil_image = Image.fromarray(windowed_image)
    draw_obj = ImageDraw.Draw(pil_image)
    draw_obj.fontmode = "1"
    font = ImageFont.load_default()

    for ellipse in ellipses:
        draw_obj.ellipse(
            (
                (ellipse.topleft.x, ellipse.topleft.y),
                (ellipse.bottomright.x, ellipse.bottomright.y),
            ),
            outline="red",
            fill=None,
            width=3,
        )

    arrow_text_to_draw = []
    for arrow in arrows:
        text = f"{arrow.value}"
        if arrow.unit:
            text += f" {arrow.unit.value}"
        text_size = draw_obj.textsize(" " + text + " ")
        offset = Point(50, 50)
        start_point = arrow + offset
        text_offset = [0, 0]
        if start_point.x < 0 or start_point.x > pil_image.width:
            start_point.x = arrow.x - offset.x
        if start_point.y < 0 or start_point.y > pil_image.height:
            start_point.y = arrow.y - offset.y
            text_offset[1] = -11

        if start_point.x + text_size[0] > pil_image.width:
            text_offset[0] = pil_image.width - \
                (start_point.x + text_size[0])

        arrowedLine(
            draw_obj, Point(start_point.x, start_point.y), arrow, width=2
        )
        arrow_text_to_draw.append(
            ((start_point.x + text_offset[0],
                start_point.y + text_offset[1]), text)
        )

    for ellipse in ellipses:
        text = f"{ellipse.value}"
        if ellipse.unit:
            text += f" {ellipse.unit.value}"
        text_size = draw_obj.textsize(text)
        text_loc = [int(ellipse.right.x) + 3,
                    int(ellipse.top.y - text_size[1] / 2)]
        flip_x = 1
        flip_y = 1

        if (text_loc[0] + text_size[0]) > pil_image.width:
            text_loc[0] = int(ellipse.left.x) - text_size[0]
            flip_x = -1

        if (text_loc[1] - text_size[1]) < 0:
            text_loc[1] = int(ellipse.bottom.y)
            flip_y = -1

        a = ellipse.rx
        b = ellipse.ry
        x = (math.sqrt(2) * a ** (1.5) * b ** (1.5) + a ** 3 - a ** 2 * b) / (
            a ** 2 + b ** 2
        )
        y = b * math.sqrt(1 - x ** 2 / a ** 2)
        draw_obj.line(
            (
                (flip_x * x + ellipse.center.x, -flip_y * y + ellipse.center.y),
                int(ellipse.center.x + flip_x * ellipse.rx),
                int(ellipse.center.y - flip_y * ellipse.ry),
            ),
            width=2,
            fill="red",
        )
        draw_obj.text(
            xy=text_loc,
            text=text,
            fill="orange",
            font=font,
        )
    for r in arrow_text_to_draw:
        draw_obj.text(
            xy=r[0],
            text=r[1],
            fill="orange",
            font=font,
        )

        # Convert to numpy array
    return np.array(pil_image)
