import math
from enum import Enum

from typing import Set, Tuple, List


class Vec2:
    x: float
    y: float

    def __init__(self, x, y, *extra_dimensions):
        self.x = float(x)
        self.y = float(y)

    def __add__(self, other):
        assert isinstance(other, Vec2)
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        assert isinstance(other, Vec2)
        return Vec2(self.x - other.x, self.y - other.y)

    def normalized(self):
        if self.length() == 0:
            return Vec2(0, 0)
        return Vec2(self.x / self.length(), self.y / self.length())

    def __mul__(self, other):
        assert isinstance(other, (int, float))
        return Vec2(self.x * other, self.y * other)

    def __truediv__(self, other):
        assert isinstance(other, (int, float))
        return Vec2(self.x / other, self.y / other)

    def length(self):
        return math.sqrt(self.x ** 2 + self.y ** 2)

    def distance(self, other):
        assert isinstance(other, Vec2)
        line = self - other
        return line.length()

    def __iter__(self):
        return iter((self.x, self.y))

    def __getitem__(self, item):
        if item == 0:
            return self.x
        elif item == 1:
            return self.y
        else:
            raise IndexError()

    def __setitem__(self, item, value):
        if item == 0:
            self.x = value
        elif item == 1:
            self.y = value
        else:
            raise IndexError()

    def midpoint(self, other):
        return Vec2((self.x + other.x) / 2, (self.y + other.y) / 2)

    def __hash__(self):
        return hash((self.x, self.y))

    def cross(self, other):
        return self.x * other.y - self.y * other.x

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

    def __repr__(self):
        return "<Vec2 ({}, {})>".format(self.x, self.y)

    def dot(self, other):
        return self.x * other.x + self.y * other.y


class Line:
    start: Vec2
    end: Vec2
    line: Vec2

    def __init__(self, start: Vec2, end: Vec2):
        self.start = start
        self.end = end
        self.line = end - start

    def length(self):
        return self.line.length()

    def normalized(self):
        return self.line.normalized()

    def midpoint(self):
        return Vec2((self.start.x + self.end.x) / 2, (self.start.y + self.end.y) / 2)

    def intersect(self, other):
        def on_segment(p, q, r):
            if q.x <= max(p.x, r.x) and q.x >= min(p.x, r.x) and q.y <= max(p.y, r.y) and q.y >= min(p.y, r.y):
                return True
            return False

        class Orientation(Enum):
            COLINEAR = 0
            CLOCKWISE = 1
            COUNTERCLOCKWISE = 2

        def orientation(p, q, r) -> Orientation:
            val = (q.y - p.y) * (r.x - q.x) - (q.x - p.x) * (r.y - q.y)
            if val == 0:
                return Orientation.COLINEAR

            return Orientation.CLOCKWISE if val > 0 else Orientation.COUNTERCLOCKWISE

        p1 = self.start
        q1 = self.end
        p2 = other.start
        q2 = other.end

        o1 = orientation(p1, q1, p2)
        o2 = orientation(p1, q1, q2)
        o3 = orientation(p2, q2, p1)
        o4 = orientation(p2, q2, q1)

        if o1 != o2 and o3 != o4:
            return True

        if o1 == 0 and on_segment(p1, p2, q1):
            return True
        if o2 == 0 and on_segment(p1, q2, q1):
            return True
        if o3 == 0 and on_segment(p2, p1, q2):
            return True
        if o4 == 0 and on_segment(p2, q1, q2):
            return True

        return False

    def __repr__(self):
        return "<Line ({}, {})>".format(self.start, self.end)

    def __iter__(self):
        return iter((self.start, self.end))

    def __eq__(self, other):
        ts, te = self
        os, oe = other
        return (ts == os and te == oe) or (ts == oe and te == os)

    def __hash__(self):
        return hash(frozenset(self))

    def split(self, n):
        verts = [self.start]
        segment = self.line / (n - 1)
        for _ in range(n - 1):
            verts.append(verts[0] + segment)
        verts.append(self.end)

        lines = []

        for i in range(n - 1):
            lines.append(Line(verts[i], verts[i+1]))

        return lines

    def shrink(self, length, from_start=False):
        if from_start:
            return Line(self.start + self.normalized() * length, self.end)
        return Line(self.start, self.start + self.normalized() * (self.length() - length))

    def add_tab(self, after, tab_length=1):
        if self.length() < after or self.length() < tab_length:
            return after - self.length(), [self]

        start, end = self
        midpoint = (self.normalized() * after) + start

        part_a = Line(start, midpoint).shrink(tab_length / 2)
        part_b = Line(midpoint, end).shrink(tab_length / 2, from_start=True)

        if part_b.length() <= after:
            return after - part_b.length(), [part_a, part_b]

        remaining, parts = part_b.add_tab(after, tab_length)
        return remaining, [part_a] + parts


class Rect:
    min: Vec2
    max: Vec2

    def __init__(self, min, max):
        self.min = min
        self.max = max

    def inside(self, point: Vec2):
        return self.min.x <= point.x <= self.max.x and self.min.y <= point.y <= self.max.y


class Polygon:
    loops: Set[Tuple[Vec2]]
    points: Set[Vec2]
    lines: Set[Line]

    def __init__(self, *loops):
        self.loops = {tuple(loop) for loop in loops}
        self.points = set()
        self.lines = set()
        for loop in loops:
            for n in range(len(loop)):
                start = loop[n]
                self.points.add(start)
                end = loop[(n + 1) % len(loop)]
                self.lines.add(Line(start, end))

    def bounding_box(self):
        return Rect(Vec2(min([p.x for p in self.points]), min([p.y for p in self.points])),
                    Vec2(max([p.x for p in self.points]), max([p.y for p in self.points])))

    def inside(self, point: Vec2):
        box = self.bounding_box()
        if not box.inside(point):
            return False

        crossings = 0
        check_line = Line(Vec2(box.min.x - 1, point.y), Vec2(point.x, point.y))

        for line in self.lines:
            if line.intersect(check_line):
                crossings += 1

        return crossings > 0 and crossings % 2 == 1


class LineSet:
    lines: List[Line]
    verts: Set[Vec2]
    loop: bool

    def __init__(self, start):
        self.lines = [start]
        self.verts = set(start)
        self.loop = False

    def add(self, line):
        if line in self.lines:
            raise ValueError("Line already in Lineset")

        self.lines.append(line)

        loop = line.start in self.verts and line.end in self.verts
        self.verts.add(line.start)
        self.verts.add(line.end)

        self.loop = self.loop or loop
        return self.loop

    def connected(self, line):
        start, end = line
        return (start in self.verts) or (end in self.verts)

    def __iter__(self):
        return iter(self.lines)

    def __getitem__(self, n):
        return self.lines[n]

    def merge(self, other):
        for line in other:
            self.add(line)

    def __len__(self):
        return len(self.lines)
