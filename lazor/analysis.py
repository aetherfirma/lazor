import math
from functools import reduce

from lazor.datastructures import Line, LineSet, Vec2


def join_lines(lines, unify_distance=0.01):
    edges = set()
    verts_set = []

    for line in lines:
        start_v = None
        end_v = None
        for v, vert_set in enumerate(verts_set):
            if start_v is not None and end_v is not None:
                break

            for vert in vert_set:
                if start_v is None and line.start.distance(vert) < unify_distance:
                    start_v = v
                if end_v is None and line.end.distance(vert) < unify_distance:
                    end_v = v

        if start_v is None:
            start_v = len(verts_set)
            verts_set.append({line.start})
        else:
            verts_set[start_v].add(line.start)
        if end_v is None:
            end_v = len(verts_set)
            verts_set.append({line.end})
        else:
            verts_set[end_v].add(line.end)

        edge = frozenset((start_v, end_v))
        if len(edge) != 2:
            continue
        edges.add(edge)

    verts = []
    for vert_set in verts_set:
        verts.append(reduce(lambda a, b: a.midpoint(b), vert_set))

    new_lines = []
    for start_v, end_v in edges:
        start = verts[start_v]
        end = verts[end_v]

        if start.distance(end) < unify_distance:
            continue

        new_lines.append(Line(start, end))

    return new_lines


def collate_lines(lines):
    line_sets = []

    for line in lines:
        disconnected = []
        connected = []
        for line_set in line_sets:
            if line_set.connected(line):
                connected.append(line_set)
            else:
                disconnected.append(line_set)

        if not connected:
            line_sets.append(LineSet(line))
        else:
            new_set = LineSet(line)
            for other in connected:
                new_set.merge(other)
            line_sets = disconnected + [new_set]

    return line_sets


def minimum_laser_distance(lines):
    return sum(line.length() for line in lines)


def ideal_laser_distance(layer):
    """
    Calculates the ideal transit distance for a given set of lines. It is 
    assumed that the laser head begins on at the start of the first line and 
    that execution ends as soon as the laser head reaches the end of the last 
    line.
    """

    travel = 0
    current_cord = layer[0].start

    for line in layer:
        travel += current_cord.distance(line.start)
        travel += line.length()

        current_cord = line.end

    return travel


def optimise_line_set_ordering(layer):
    line_sets = layer
    ordered_lines = []

    min_x, min_y = float("inf"), float("inf")
    for line in line_sets:
        for x, y in line:
            min_x = min(min_x, x)
            min_y = min(min_y, y)

    last_point = Vec2(min_x, min_y)

    while line_sets:
        candidates = line_sets
        line_sets = []
        candidate_line = None
        candidate_distance = float("inf")

        for line in candidates:
            if last_point.distance(line.start) < candidate_distance:
                if candidate_line:
                    line_sets.append(candidate_line)
                candidate_line = Line(line.start, line.end)
                candidate_distance = last_point.distance(line.start)
            elif last_point.distance(line.end) < candidate_distance:
                if candidate_line:
                    line_sets.append(candidate_line)
                candidate_line = Line(line.end, line.start)
                candidate_distance = last_point.distance(line.end)
            else:
                line_sets.append(line)

        if last_point.distance(candidate_line.start) < last_point.distance(candidate_line.end):
            ordered_lines.append(Line(candidate_line.start, candidate_line.end))
            last_point = candidate_line.end
        else:
            ordered_lines.append(Line(candidate_line.end, candidate_line.start))
            last_point = candidate_line.start

    return ordered_lines
