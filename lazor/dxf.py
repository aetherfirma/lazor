import ezdxf

from lazor.datastructures import Vec2, Line


def draw(*layers):
    dxf = ezdxf.new("R2007")
    modelspace = dxf.modelspace()

    for layer, lines in enumerate(layers):
        layer_name = "Layer {}".format(layer)
        dxf.layers.new(layer_name, dxfattribs={"color": layer})
        for line in lines:
            modelspace.add_line(*line, dxfattribs={"layer": layer_name})

    return dxf


def unpack(modelspace):
    lines = []
    min_point = Vec2(float('inf'), float('inf'))
    max_point = Vec2(float('-inf'), float('-inf'))

    for entity in modelspace:
        start = Vec2(*entity.dxf.start)
        end = Vec2(*entity.dxf.end)

        min_x = min(start.x, end.x, min_point.x)
        min_y = min(start.y, end.y, min_point.y)
        max_x = max(start.x, end.x, max_point.x)
        max_y = max(start.y, end.y, max_point.y)

        min_point = Vec2(min_x, min_y)
        max_point = Vec2(max_x, max_y)

        lines.append(Line(start, end))

    centre = min_point.midpoint(max_point)

    for line in lines:
        line.start = line.start - centre
        line.end = line.end - centre

    return lines
