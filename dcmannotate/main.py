#!/usr/bin/python3
import math
import json
import argparse

from writers import *
from annotations import *

writer = SecondaryCaptureWriter()

test_set = Annotations([Ellipse(Point(256, 128), Point(256, 370), Point(
    128, 256), Point(370, 256), unit='Millimeter', value=1234)],
    [PointMeasurement(0, 0, 'Millimeter', 100),
     PointMeasurement(512, 512, 'Millimeter', 10000),
     PointMeasurement(0, 512, 'Millimeter', 10000),
     PointMeasurement(512, 0, 'Millimeter', 1000000),
     PointMeasurement(256, 256, 'Millimeter', 1000000)], '../mandel.dcm')

writer.generate(test_set,
                [0, 255]).save_as('/vagrant/sc_test.dcm')

# k = Ellipse.from_dict(dict(top=Point(256,128), bottom=Point(256,370), left= Point(128, 256 ),right= Point(370,256), unit='Millimeter', value=1234))

# Ellipse = namedtuple('Ellipse', ['top', 'bottom', 'left', 'right', 'value'])

# def make_ellipse(c,r1,r2,v):
#     return Ellipse(Point(c.x,c.y-r1),Point(c.x,c.y+r1),Point(c.x-r2, c.y),Point(c.x+r2, c.y),value=v)

# def make_circle(c,r,v):
#     return make_ellipse(c,r,r,v)

# if __name__ == "__main__":
#     parser = argparse.ArgumentParser()
#     parser.add_argument('file')
#     parser.add_argument('--description')
#     parser.add_argument('--json')
#     args = parser.parse_args()
#     annotations = json.loads(args.json)

#     writer = SRWriter()
#     xml = writer.generate_xml(reference_dataset=args.file, description=args.description, **annotations)
#     print(xml)
#     exit()

# arrows = [dict(x=x,y=y, value=100) for x in range(0,512,32) for y in range(0,512,32)]

# arrows = [dict(x=256+128*math.sin(t*math.pi/10*2),y=256+128*math.cos(t*math.pi/10*2), value=100) for t in range(0,6)]

# print(make_ellipse(Point(256,256),128,999))

# ellipses = [make_ellipse(Point(256,256),128, 72 ,999),
#             make_circle(Point(256,256),64,999),
#             make_circle(Point(128,256),64,999),
#             make_circle(Point(384,256),64,999)
#             ]
# [Ellipse(Point(256,128), Point(256,370), Point(128, 256 ), Point(370,256), value=1234 ),
#             make_ellipse(Point(256,256),64,999)]

# print(template.render(reference=ds, description="3 more ellipses", arrows=[dict(x=256,y=256,value=1)], ellipses=ellipses))
# print(writer.generate_xml(reference_dataset=ds, description="idk", arrows=[dict(x=1,y=1,unit=dict(value='mm',meaning='millimeter'),value=1)]))
# print(writer.generate_xml(reference_dataset=ds, description="3 more ellipses", arrows=[], ellipses= [Ellipse(Point(256,128), Point(256,370), Point(128, 256 ), Point(370,256), 'Millimeter', value=1234 )]))
