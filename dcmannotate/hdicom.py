#!/usr/bin/python3
from pathlib import Path
import sys

import highdicom as hd
from highdicom.sr.content import FindingSite, SourceImageForRegion
from highdicom.sr.templates import Measurement, TrackingIdentifier
import numpy as np
from pydicom.filereader import dcmread
from pydicom.sr.codedict import codes
from pydicom.uid import generate_uid

# Path to single-frame CT image instance stored as PS3.10 file
image_file = Path(sys.argv[1])

# Read CT Image data set from PS3.10 files on disk
image_dataset = dcmread(str(image_file))

# Describe the context of reported observations: the person that reported
# the observations and the device that was used to make the observations
observer_person_context = hd.sr.ObserverContext(
    observer_type=codes.DCM.Person,
    observer_identifying_attributes=hd.sr.PersonObserverIdentifyingAttributes(
        name='Unknown^'
    )
)
observer_device_context = hd.sr.ObserverContext(
    observer_type=codes.DCM.Device,
    observer_identifying_attributes=hd.sr.DeviceObserverIdentifyingAttributes(
        uid=hd.UID()
    )
)
observation_context = hd.sr.ObservationContext(
    observer_person_context=observer_person_context,
    observer_device_context=observer_device_context,
)

# Describe the image region for which observations were made
# (in physical space based on the frame of reference)

referenced_region = hd.sr.ImageRegion(
    graphic_type=hd.sr.GraphicTypeValues.ELLIPSE,
    graphic_data=np.array([
        (256,128), (256,370), (128, 256 ), (370,256)
    ]),
    source_image=SourceImageForRegion.from_source_image(image_dataset)
    # frame_of_reference_uid=''# image_dataset.FrameOfReferenceUID
)

# Describe the anatomic site at which observations were made
# finding_sites = [
#     FindingSite(
#         anatomic_location=codes.SCT.CervicoThoracicSpine,
#         topographical_modifier=codes.SCT.VertebralForamen
#     ),
# ]

# Describe the imaging measurements for the image region defined above
measurements = [
    Measurement(
        name=codes.SCT.AreaOfDefinedRegion,
        # tracking_identifier=hd.sr.TrackingIdentifier(uid=generate_uid()),
        value=1.7,
        unit=codes.UCUM.SquareMillimeter,
        properties=hd.sr.MeasurementProperties(
            normality=hd.sr.CodedConcept(
                value="17621005",
                meaning="Normal",
                scheme_designator="SCT"
            ),
            level_of_significance=codes.SCT.NotSignificant
        )
    )
]
imaging_measurements = [
    hd.sr.MeasurementsAndQualitativeEvaluations(
        tracking_identifier=TrackingIdentifier(
            uid=hd.UID(),
            identifier='cornerstoneTools@^4.0.0:EllipticalRoi'
        ),
        # referenced_region=referenced_region,
        # finding_type=codes.SCT.SpinalCord,
        measurements=measurements,
        # finding_sites=finding_sites
    )
]

# Create the report content
measurement_report = hd.sr.MeasurementReport(
    observation_context=observation_context,
    procedure_reported=codes.SCT.ImagingProcedure,
    imaging_measurements=imaging_measurements
)

# Create the Structured Report instance
sr_dataset = hd.sr.EnhancedSR(
    evidence=[image_dataset],
    content=measurement_report[0],
    series_number=1,
    series_instance_uid=hd.UID(),
    sop_instance_uid=hd.UID(),
    instance_number=1,
    manufacturer='Manufacturer'
)

sr_dataset.save_as("hdicom.dcm")