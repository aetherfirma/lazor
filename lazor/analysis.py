from functools import reduce

from lazor.datastructures import Line, LineSet


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