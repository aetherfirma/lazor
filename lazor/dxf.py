import ezdxf
from collections import defaultdict

from lazor.datastructures import Vec2, Line


def draw(layers, colours):
    dxf = ezdxf.new("R2007")
    modelspace = dxf.modelspace()

    for n, (layer, lines) in enumerate(layers.items()):
        dxf.layers.new(layer, dxfattribs={"color": colours[layer]})
        for line in lines:
            modelspace.add_line(*line, dxfattribs={"layer": layer})

    return dxf


def unpack(drawing):
    modelspace = drawing.modelspace()

    min_point = Vec2(float('inf'), float('inf'))
    max_point = Vec2(float('-inf'), float('-inf'))

    layers = defaultdict(list)
    colours = {}

    for entity in modelspace:
        if entity.dxf.layer not in colours:
            if entity.dxf.layer in drawing.layers:
                colours[entity.dxf.layer] = drawing.layers.get(entity.dxf.layer).dxf.color
            else:
                colours[entity.dxf.layer] = 0

        start = Vec2(*entity.dxf.start)
        end = Vec2(*entity.dxf.end)

        min_x = min(start.x, end.x, min_point.x)
        min_y = min(start.y, end.y, min_point.y)
        max_x = max(start.x, end.x, max_point.x)
        max_y = max(start.y, end.y, max_point.y)

        min_point = Vec2(min_x, min_y)
        max_point = Vec2(max_x, max_y)

        layers[entity.dxf.layer].append(Line(start, end))

    centre = min_point.midpoint(max_point)

    for layer in layers.values():
        for line in layer:
            line.start = line.start - centre
            line.end = line.end - centre

    return layers, colours
