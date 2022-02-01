from pathlib import Path
from subprocess import run, PIPE
from typing import List, Optional
from jinja2 import Environment, FileSystemLoader, StrictUndefined
import pydicom

from pydicom.uid import generate_uid


from dcmannotate.annotations import Annotations, AnnotationSet


env = Environment(
    loader=FileSystemLoader(
        Path(__file__).parent.parent.resolve() / "templates" / "tid1500"
    ),
    autoescape=True,
    undefined=StrictUndefined,
)
env.globals["generate_uid"] = generate_uid
template = env.get_template("base.xml")


def generate_slice_xml(annotations: Annotations, description: str) -> str:
    reference_dataset, ellipses, arrows = (
        annotations.reference,
        annotations.ellipses,
        annotations.arrows,
    )

    return template.render(
        reference=reference_dataset,
        description=description,
        arrows=arrows,
        ellipses=ellipses,
    )


def generate_dicoms(
    aset: "AnnotationSet", pattern: Optional[str] = None
) -> List[Path]:
    for k in aset:
        for measurement in k:
            if type(measurement.value) not in (int, float) and measurement.unit:
                raise Exception(
                    f'{measurement} on slice {k.reference.z_index} has non-numeric value "{measurement.value}".'
                )
    xml_docs = generate_xml(aset)
    outfiles = []
    for annotations, xml in zip(aset, xml_docs):
        if pattern is None:
            frompath = annotations.reference.from_path
            outfile = str(frompath.with_name(frompath.stem + "_sr.dcm"))
        else:
            outfile = pattern.replace(
                "*", str(annotations.reference.z_index))
        p = run(
            ["xml2dsr", "-", outfile],
            stdout=PIPE,
            stderr=PIPE,
            input=xml,
            encoding="utf-8",
        )
        if p.returncode != 0:
            raise Exception(p.stderr)

        d = pydicom.dcmread(outfile)

        for elem in d.iterall():
            if elem.name == "Concept Code Sequence":
                try:
                    long_code_value = elem[0].LongCodeValue
                except Exception:
                    continue
                if long_code_value == "CORNERSTONEFREETEXT":
                    elem[0].add_new("CodeValue", "SH",
                                    "CORNERSTONEFREETEXT")
                    del elem[0][0x00080119]
                    # print(elem[0])

        d.save_as(outfile)

        outfiles.append(Path(outfile))
    return outfiles


def generate_xml(aset: AnnotationSet) -> List[str]:
    return [generate_slice_xml(a, "") for a in aset]
