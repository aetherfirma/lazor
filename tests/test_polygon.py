from lazor.datastructures import Vec2, Polygon


def test_point_outside_polygon():
    square = Polygon([Vec2(0, 0), Vec2(0, 1), Vec2(1, 1), Vec2(1, 0)])
    assert not square.inside(Vec2(0.5, 1.5))


def test_point_in_polygon():
    square = Polygon([Vec2(0, 0), Vec2(0, 1), Vec2(1, 1), Vec2(1, 0)])
    assert square.inside(Vec2(0.5, 0.5))


def test_point_in_polygon_with_a_hole():
    square = Polygon([Vec2(-1, -1), Vec2(-1, 2), Vec2(2, 2), Vec2(2, -1)], [Vec2(0, 0), Vec2(0, 1), Vec2(1, 1), Vec2(1, 0)])
    assert not square.inside(Vec2(0.5, 0.5))



