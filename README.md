# DCMAnnotate

DCMAnnotate is an experimental python library for generating simple annotations on DICOM volumes. 

## Supported output formats

- DICOM SR TID1500 Measurement Report
- DICOM Secondary Capture ("burned in" annotations)
- Visage 7 PR

## Supported annotations
- Elliptical ROI
- Point measurement

## Overview of Use
The `DicomVolume` class will read a list of DICOM files, and verify that they form a single DICOM volume. They are additionally sorted by their z-order.
```python
in_files = list(Path("./volume/").glob("slice.[0-9].dcm"))
volume = DicomVolume(in_files)
# volume[0] is the first slice, volume[-1] is the last, ordered by z-index
```
Now we need to add annotations to this volume. For each slice that needs annotating, create an `Annotations` object with the ROIs and point measurements, and the slice. These are combined into an `AnnotationSet` and then set on the volume.
```python
a_slice_0 = Annotations(
    [Ellipse(Point(128, 256), 20, 20, "Millimeter", 1)],
     PointMeasurement(128, 170, "Millimeter", 100)], 
    volume[0]
)
aset = AnnotationSet([a_slice_0])
volume.annotate_with(aset)
```
Writing each output format looks like this:
```python
# TID1500 SR
volume.write_sr() 
# Secondary Capture
volume.write_sc(result_path / "slice_*_sc.dcm") 
# Visage
volume.write_visage(result_path / "result_visage.dcm")
```

For a complete example, see [demo.py](https://github.com/mercure-imaging/dcmannotate/blob/main/demo.py).
## Creating Measurements

Measurements have two types of attributes: their location within the slice and the value of the measurement itself, which are all set in their constructors. In all cases the "unit" value is required to be a string corresponding to a [UCUM unit](https://ucum.nlm.nih.gov/) definition available in `pydicom.sr.codedict.codes.UCUM`, such as "Millimeter", "SquareMillimeter", "ArbitraryUnit", or "NoUnits". This is to ensure compatibility with TID1500, which is defined in terms of UCUM units. This may be relaxed in future. 

The available constructors are:

```python 
PointMeasurement(x: int, y: int, unit: str, value: any)

Ellipse(center: Point, width: int, height: int, unit: str, value: any)
```
## Output formats

### TID1500 SR

Writing SR results is a matter of calling ```volume.write_sr()```. The SR files for each slice that has annotations will be written next to it, so `slice0.dcm` will have `slice0_sr.dcm`. Development of this output format has been tested against [OHIF](https://ohif.org/) and may vary. 

### Secondary Capture

When writing a secondary capture, DCMAnnotate writes out a new volume with the annotations burned into the pixels of each slice. The parameter to `Volume.write_sc(path: str)` is a *path pattern*, such as `"./result/slice_*.dcm"`. The wildcard character `*` is replaced by the z-index of each slice. This may or may not lead to the resulting files sorting in the same order as the original files, since the first file might not correspond to the lowest z-index.

### Visage

The Visage writer attempts to match the Visage internal format for annotations as closely as possible, at least for these measurement types. However, this is a proprietary format that is not publicly documented, and issues may arise. The parameter to `Volume.write_visage(path: str)` should be a path to a single dicom file where the annotations for this volume will be written. 