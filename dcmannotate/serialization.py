from json import JSONEncoder, JSONDecoder
from typing import Any, List, Union, Dict
from .measurements import Measurement, PointMeasurement, Ellipse, Point
from .annotations import AnnotationSet, AnnotationsParsed, AnnotationSetParsed

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .dicomvolume import DicomVolume


class AnnotationEncoder(JSONEncoder):
    def default(self, o: Any) -> Any:
        if hasattr(o, "__json_serializable__"):
            return o.__json_serializable__()
        return o


class AnnotationDecoder(JSONDecoder):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        JSONDecoder.__init__(
            self, object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, dct: Dict[str, Any]) -> Union[AnnotationsParsed, AnnotationSet, Dict[str, Any]]:
        if "arrows" in dct and "ellipses" in dct and "reference_sop_uid" in dct:
            arrows = [
                PointMeasurement(k["x"], k["y"], k["unit"], k["value"])
                for k in (dct["arrows"] or [])
            ]
            ellipses = [
                Ellipse(
                    Point(k["center"][0], k["center"][1]),
                    k["rx"],
                    k["ry"],
                    k["unit"],
                    k["value"],
                )
                for k in (dct["ellipses"] or [])
            ]
            measurements: List[Measurement]
            measurements = arrows + ellipses   # type: ignore
            return AnnotationsParsed(measurements,  dct["reference_sop_uid"])
        # and isinstance(dct[0], AnnotationsParsed):
        return dct


def read_annotations_from_json(volume: "DicomVolume", json: str) -> AnnotationSet:
    d = AnnotationDecoder()
    result = d.decode(json)
    if not isinstance(result, list) or not isinstance(result[0], AnnotationsParsed):
        raise Exception(
            f"Unexpected annotation data: {json}")

    return AnnotationSetParsed(result).with_reference(volume)
