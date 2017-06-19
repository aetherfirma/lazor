import math
from hypothesis.strategies import floats, integers
from hypothesis import given
import pytest

from lazor.datastructures import Vec2, Line

f = floats(min_value=-1200, max_value=1200)


@given(f, f, f, f)
def test_adding_one_tab(xa, ya, xb, yb):
    a = Vec2(xa, ya)
    b = Vec2(xb, yb)

    line = Line(a, b)

    _, lines = line.add_tab(line.length()/2, 1)

    if line.length() < 1:
        return

    assert len(lines) == 2

    for l in lines:
        assert abs(l.length() - (line.length() / 2 - 0.5)) < 0.001


@pytest.mark.skip()
@given(f, f, f, f, floats(min_value=1, max_value=1000))
def test_adding_n_tab(xa, ya, xb, yb, tab_distance):
    a = Vec2(xa, ya)
    b = Vec2(xb, yb)

    line = Line(a, b)

    if line.length() < 0.001:
        return

    _, lines = line.add_tab(tab_distance)

    if line.length() < tab_distance:
        return

    segments = math.ceil(line.length() / tab_distance)
    segment_length = (line.length() / segments - 0.5)
    assert len(lines) == segments

    if segments == 1:
        assert lines[0] == line
        return

    lines_segments = sum(l.length() for l in lines) + 1 * segments
    assert lines_segments == line.length()

    first, *middle, last = lines
    assert abs(first.length() - segment_length) < 0.001
    assert abs(last.length() - segment_length) < 0.001
    for l in middle:
        assert abs(l.length() - segment_length - 0.5) < 0.001


