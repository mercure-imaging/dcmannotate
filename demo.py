from dcmannotate import *

ellipses = [Ellipse.from_center(Point(256,256),128, 72, 'Millimeter', 1),
            Ellipse.from_center(Point(256,256),64, 64, 'Millimeter',2),
            Ellipse.from_center(Point(128,256),64, 64, 'Millimeter',3),
            Ellipse.from_center(Point(384,256),64, 64, 'Millimeter',4)
    ]

k = SRWriter()
print(k.generate_xml('mandel.dcm','demo',ellipses=ellipses))


# generator.Ellipse()