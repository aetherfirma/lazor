import ezdxf

from lazor.analysis import join_lines, collate_lines
from lazor.dxf import draw, unpack


def main():
    drawing = ezdxf.readfile(
        "c:/Users/drake/Dropbox/lasercut/tudor/tudor-farm-mdf-test.dxf")
    modelspace = drawing.modelspace()

    joined = join_lines(unpack(modelspace))
    collated = collate_lines(joined)

    print("{} lines, {} loops".format(len(collated), len(list(filter(lambda c: c.loop, collated)))))

    layers = []
    for line_set in collated:
        layer = []
        for line in line_set:
            _, new_lines = line.add_tab(29)
            layer += new_lines
        layers.append(layer)

    deduped = draw(**dict(enumerate(layers)))

    deduped.saveas("c:/Users/drake/Dropbox/lasercut/tudor/tudor-farm-mdf-deduped.dxf")
    # add_tabs(drawing).saveas("c:/Users/drake/Dropbox/lasercut/tudor/tudor-mdf-1-tabbed.dxf")


if __name__ == '__main__':
    main()



