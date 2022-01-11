from os import PathLike
from typing import Dict, List, Optional, Sequence, Tuple, Union, cast
import zlib
import pydicom
from pydicom.dataset import Dataset
from pydicom.sr.codedict import _CodesDict, codes
from dcmannotate import PointMeasurement, Ellipse, Point
from pydicom.sr.coding import Code
from pathlib import Path
from dcmannotate.annotations import AnnotationSet, Annotations
from dcmannotate.dicomvolume import DicomVolume
from dcmannotate.measurements import Measurement
from defusedxml.ElementTree import fromstring as xml_from_string # type: ignore


def find_value_type(ds: Dataset, type: str) -> Dataset:
    for k in ds.ContentSequence:
        if k.ValueType == type:
            assert isinstance(k, Dataset)
            return k
    raise ValueError(f"Expected to find ValueType {type}")


def find_content_items(sr: Dataset, code: Code) -> List[Dataset]:
    found_items = []
    for k in sr.ContentSequence:
        if (
            hasattr(k, "ConceptNameCodeSequence")
            and k.ConceptNameCodeSequence[0].CodeValue == code.value
        ):
            found_items.append(k)
        if hasattr(k, "ContentSequence"):
            found_items += find_content_items(k, code)
    return found_items


class VisageReader:
    def decode(self, t: bytes) -> str:
        return zlib.decompress(t[4:]).decode("utf-8")

    def get_measurements(
        self, dataset: Union[Dataset, str, Path]
    ) -> Dict[str, List[Measurement]]:
        ds: Dataset
        if isinstance(dataset, (str, PathLike)):
            ds = pydicom.dcmread(dataset)
        else:
            ds = dataset

        data = ds.ReferencedSeriesSequence[0].ReferencedImageSequence[0][0x00711062]
        sop_uids = [
            k.ReferencedSOPInstanceUID
            for k in ds.ReferencedSeriesSequence[0].ReferencedImageSequence
        ]
        xml_data = xml_from_string(self.decode(data))
        measurements: Dict[str, List[Measurement]] = {
            sop_uids[z]: [] for z in range(len(sop_uids))
        }
        for measurement in xml_data:
            meas_type = measurement.tag
            origin = measurement.find("./coordinate_system/origin").text.split(" ")
            x,y = map(int, origin[0:2])
            z = float(origin[2])
            z_idx = int(z - 0.5)
            label = measurement.find("./label").text
            label_pieces = label.split(" ")
            value_str = " ".join(label_pieces[0:-1])
            unit = label_pieces[-1]
            unit_code = getattr(codes.UCUM, unit, None)
            value: Union[str, float]
            if unit_code is None:
                value = label
            else:
                value = float(value_str)

            if meas_type == "ellipse":
                rx = int(measurement.find("./geometry/radius_x").text)
                ry = int(measurement.find("./geometry/radius_y").text)
                measurement = Ellipse(Point(x, y), rx, ry, unit_code, value)
            elif meas_type == "text":
                measurement = PointMeasurement(x, y, unit_code, value)
            else:
                raise ValueError(f"Unknown measurement type {meas_type}")
            measurements[sop_uids[z_idx]].append(measurement)
        return measurements

    def read_annotations(
        self,
        volume: DicomVolume,
        visage_files: Union[Dataset, str, Path],
    ) -> AnnotationSet:
        measurement_sets = self.get_measurements(visage_files)
        annotations = []
        for sop_uid, measurements in measurement_sets.items():
            if len(measurements) == 0:
                continue
            for s in volume:
                if s.SOPInstanceUID == str(sop_uid):
                    annotations.append(Annotations(measurements, s))
                    break
            else:
                raise Exception(
                    "ReferencedSOPInstanceUID for this measurement does not exist in volume."
                )
        return AnnotationSet(annotations)


class SRReader:
    def get_measurements(
        self, dataset: Union[Dataset, str, Path]
    ) -> Tuple[List[Measurement], str]:
        assert type(codes.DCM) is _CodesDict

        ds: Dataset
        if isinstance(dataset, (str, PathLike)):
            ds = pydicom.dcmread(dataset)
        else:
            ds = dataset
        measurement_groups = find_content_items(
            ds, cast(Code, codes.DCM.MeasurementGroup)
        )
        result: List[Measurement] = []
        referenced_sop_instance_uid = ""
        for m in measurement_groups:
            n = find_value_type(m, "NUM")
            gtype = n.ContentSequence[0].GraphicType
            data = n.ContentSequence[0].GraphicData
            if not referenced_sop_instance_uid:
                referenced_sop_instance_uid = (
                    find_value_type(n.ContentSequence[0], "IMAGE")
                    .ReferencedSOPSequence[0]
                    .ReferencedSOPInstanceUID
                )
            try:
                code = find_value_type(m, "CODE")
            except ValueError:
                code = None
            if code and code.ConceptCodeSequence[0].CodeValue == "CORNERSTONEFREETEXT":
                value = code.ConceptCodeSequence[0].CodeMeaning
                unit = None
            else:
                value = float(n.MeasuredValueSequence[0].NumericValue)
                unit = (
                    n.MeasuredValueSequence[0]
                    .MeasurementUnitsCodeSequence[0]
                    .CodeMeaning
                )

            if gtype == "POINT":
                result.append(PointMeasurement(data[0], data[1], unit, value))
            if gtype == "ELLIPSE":
                result.append(
                    Ellipse(
                        Point(data[0], data[5]),
                        (data[6] - data[4]) / 2.0,
                        (data[3] - data[1]) / 2.0,
                        unit,
                        value,
                    )
                )
        return result, referenced_sop_instance_uid

    def read_annotations(
        self,
        volume: Union[DicomVolume, Sequence[Dataset]],
        sr_files: Sequence[Union[Dataset, str, Path]],
    ) -> AnnotationSet:
        assert len(sr_files) > 0
        annotations = []
        for f in sr_files:
            measurements, uid = self.get_measurements(f)
            for s in volume:
                if s.SOPInstanceUID == str(uid):
                    annotations.append(Annotations(measurements, s))
                    break
            else:
                raise Exception(
                    "ReferencedSOPInstanceUID for this SR does not exist in volume."
                )
        return AnnotationSet(annotations)


if __name__ == "__main__":
    demo_path = Path("/vagrant/demo-test/")
    volume = DicomVolume(list(demo_path.glob("slice.[0-9].dcm")))
    k = VisageReader()
    # ms = k.get_measurements(demo_path / "demo_result_visage.dcm")
    a = k.read_annotations(volume, demo_path / "demo_result_visage.dcm")
    volume.annotate_with(a)
    print(volume)
# k = SRReader()
# a = k.read_annotations([d for d in volume], list(demo_path.glob("slice.[0-9]_sr.dcm")))
