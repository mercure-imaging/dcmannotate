# DCMAnnotate

DCMAnnotate is an experimental python library for generating simple annotations on DICOM volumes. 

![GitHub](https://img.shields.io/github/license/mercure-imaging/dcmannotate)
[![workflow status](https://github.com/mercure-imaging/dcmannotate/actions/workflows/pythonapp.yml/badge.svg)](https://github.com/mercure-imaging/dcmannotate/actions/workflows/pythonapp.yml)

## Supported output formats

- DICOM SR TID1500 Measurement Report
- DICOM Secondary Capture ("burned in" annotations)
- Visage 7 PR

<p align="center">
  <img src="https://github.com/mercure-imaging/DCMAnnotate/blob/assets/example_sr.png" height="250" title="hover text">
  <img src="https://github.com/mercure-imaging/DCMAnnotate/blob/assets/example_sc.png" height="250" title="hover text">
  <img src="https://github.com/mercure-imaging/DCMAnnotate/blob/assets/example_pr.png" height="250" title="hover text">
</p>

## Requirements
- Tested in Windows and Linux
- python 3.6.9 or newer
- For TID1500 SR: OFFIS dcmtk 3.6.2 installed and available in `PATH`

## Supported annotations
- Elliptical ROI
- Point measurement

# Overview of Use
The `DicomVolume` class will read a list of DICOM files, and verify that they form a single DICOM volume. They are additionally sorted by their z-order.
```python
in_files = list(Path("./in/").glob("slice.*.dcm"))
volume = DicomVolume(in_files)
# volume[0] is the first slice, volume[-1] is the last, ordered by z-index
```
Now we need to add annotations to this volume. For each slice that needs annotating, create an `Annotations` object with the ROIs and point measurements, and the slice. 
```python
a_slice_0 = Annotations(
    [Ellipse(Point(128, 256), 20, 20, "Millimeter", 1)],
     PointMeasurement(128, 170, "Millimeter", 100)], 
    volume[0]
)
volume.annotate_with([a_slice_0])
## Alternatively, explicitly create an AnnotationSet
volume.annotate_with(AnnotationSet([a_slice_0]), force=True)
```
Writing each output format looks like this:
```python
# TID1500 SR
volume.write_sr(result_path / "slice_*_sr.dcm") 
# Secondary Capture
volume.write_sc(result_path / "slice_*_sc.dcm") 
# Visage
volume.write_visage(result_path / "result_visage.dcm")
```

For a complete example, see [demo.py](https://github.com/mercure-imaging/DCMAnnotate/blob/main/demo.py).

## Creating Measurements

Measurements have two types of attributes: their location within the slice and the value of the measurement itself, which are all set in their constructors. 

The "unit" value, if supplied, is a string corresponding to a [UCUM unit](https://ucum.nlm.nih.gov/) definition available in `pydicom.sr.codedict.codes.UCUM`, such as "Millimeter", "SquareMillimeter", "ArbitraryUnit", or "NoUnits". This is to ensure compatibility with TID1500, which is defined in terms of UCUM units. 

If the unit is `None`, the `value` must be a string comprising the entire label for the measurement. If it is not `None`, the `value` must be a number.

The available constructors are:

```python 
PointMeasurement(x: int, y: int, unit: Optional[str], value: any)

Ellipse(center: Point, width: int, height: int, unit: Optional[str], value: any)
```

## Reading Annotations

DCMAnnotate can read annotations from the files it writes. You can read them by constructing a DicomVolume object representing the series, and calling `annotate_from` on it, supplying the path to the annotation file(s). It will refuse to annotate a volume with annotations that do not reference it. 

```python
volume = DicomVolume(in_files)
volume.annotate_from(list(Path(result_path).glob("slice_*_sr.dcm")))
volume.annotate_from(pydicom.dcmread("visage_pr.dcm"), force=True)
```

## Command line interface

DCMAnnotate provides a command-line tool, `dcmannotate` for both reading writing annotations. It will *probably* fail on dicoms that weren't originally written by DCMAnnotate. 

### Reading
Reading a set of annotations is a matter of passing in the dicoms that contain the annotations, and in the case of Visage annotations, the original volume as well. For example:

```
dcmannotate read -i slice_*_sc.dcm
dcmannotate read -i visage_pr.dcm -v slice_*.dcm
```
The output is a JSON-formatted list of objects encoding the annotations on each slice. For example:

```json
[
  {
    "arrows": [
      {
        "value": 100, "unit": "mm",
        "x": 128, "y": 170
      }, ],
    "ellipses": [
      {
        "value": "Finding A", "unit": null,
        "center_x": 128, "center_y": 276,
        "rx": 72, "ry": 128
      }, ],
    "reference_sop_uid": "1.2.276.0.7230010.3.1.4.7906180978556"
  }, ]
```
### Writing 

To write a set of annotations, you must specify which output format to use (sc, sr, or visage), provide the input dicom series, and specify the output file(s) with a pattern. The annotations themselves are provided in the same JSON format as above, and if they aren't specified as a keyword parameter, they will be read from `stdin`.

```bash
dcmannotate write sc -i in/slice.*.dcm -o "out/slice_sc.*.dcm" -a '[{"arrows": ..., "reference_sop_uid": ...}]'

echo -a '[{"arrows": ..., "reference_sop_uid": ...}]' | dcmannotate write visage -i in/slice.*.dcm -o "out/visage_pr.dcm" 
```

When both reading and writing, the `-i` parameter can either be a list of files (such as those generated by globbing above) or a single string that will be globbed internally, eg
```bash
dcmannotate read -i "slice_*_sc.dcm"
```


## Output formats and considerations

### TID1500 SR

Writing SR results is a matter of calling ```volume.write_sr()```. The SR files for each slice that has annotations will be written next to it, so `slice0.dcm` will have `slice0_sr.dcm` if that slice has been annotated. Development of this output format has been tested against [OHIF](https://ohif.org/) and may not work elsewhere. 

You can also provide a path pattern (see Secondary Capture below). 

### Secondary Capture

When writing a secondary capture, DCMAnnotate writes out a new volume with the annotations burned into the pixels of each slice. The parameter to `Volume.write_sc(path: str)` is a *path pattern*, such as `"./result/slice_*.dcm"`. The wildcard character `*` is replaced by the z-index of each slice. This may or may not lead to the resulting files sorting in the same order as the original files, since the first file might not correspond to the lowest z-index.

DCMAnnotate additionally writes a JSON representation of the annotations into a private block (`0x0091`). The two tags are:

| Tag          | Name                  | VR  | VM  |
| ------------ | --------------------- | --- | --- |
| (0091, 1000) | AnnotationDataVersion | UL  | 1   |
| (0091, 1001) | AnnotationData        | LT  | 1   |

At present the only AnnotationDataVersion is 1. If the data representation changes, the AnnotationDataVersion will be incremented, and out-of-date versions of DCMAnnotate will refuse to read the file. 

### Visage

The Visage writer attempts to match the Visage internal format for annotations as closely as possible, at least for these measurement types. However, this is a proprietary format that is not publicly documented, and issues may arise. The parameter to `Volume.write_visage(path: Union[str, Path])` should be a path to a single dicom file where the annotations for this volume will be written. 
