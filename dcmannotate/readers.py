from os import PathLike
from typing import List, Optional, Sequence, Tuple, Union, cast
import pydicom
from pydicom.dataset import Dataset
from pydicom.sr.codedict import _CodesDict, codes
from dcmannotate import PointMeasurement, Ellipse, Point
from pydicom.sr.coding import Code
from pathlib import Path
from dcmannotate.annotations import AnnotationSet, Annotations
from dcmannotate.dicomvolume import DicomVolume
from dcmannotate.measurements import Measurement

# sr_dataset = pydicom.dcmread("/vagrant/sr-tid1500-ct-liver-example.dcm")


class SRReader:
    @classmethod
    def find_value_type(cls, ds: Dataset, type: str) -> Dataset:
        for k in ds.ContentSequence:
            if k.ValueType == type:
                assert isinstance(k, Dataset)
                return k
        raise ValueError(f"Expected to find ValueType {type}")

    @classmethod
    def find_content_items(cls, sr: Dataset, code: Code) -> List[Dataset]:
        found_items = []
        for k in sr.ContentSequence:
            if (
                hasattr(k, "ConceptNameCodeSequence")
                and k.ConceptNameCodeSequence[0].CodeValue == code.value
            ):
                found_items.append(k)
            if hasattr(k, "ContentSequence"):
                found_items += SRReader.find_content_items(k, code)
        return found_items

    def get_measurements(
        self, dataset: Union[Dataset, str, Path]
    ) -> Tuple[List[Measurement], str]:
        assert type(codes.DCM) is _CodesDict

        ds: Dataset
        if isinstance(dataset, (str, PathLike)):
            ds = pydicom.dcmread(dataset)
        else:
            ds = dataset
        measurement_groups = SRReader.find_content_items(
            ds, cast(Code, codes.DCM.MeasurementGroup)
        )
        result: List[Measurement] = []
        referenced_sop_instance_uid = ""
        for m in measurement_groups:
            n = SRReader.find_value_type(m, "NUM")
            gtype = n.ContentSequence[0].GraphicType
            data = n.ContentSequence[0].GraphicData
            if not referenced_sop_instance_uid:
                referenced_sop_instance_uid = (
                    SRReader.find_value_type(n.ContentSequence[0], "IMAGE")
                    .ReferencedSOPSequence[0]
                    .ReferencedSOPInstanceUID
                )
            try:
                code = SRReader.find_value_type(m, "CODE")
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

            # print(type, data, value, unit)
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


demo_path = Path("/vagrant/demo-test/")
volume = DicomVolume(list(demo_path.glob("slice.[0-9].dcm")))

k = SRReader()
a = k.read_annotations([d for d in volume], list(demo_path.glob("slice.[0-9]_sr.dcm")))
print(a == a)