import math
from pose import Pose2D, pose_from_wheel_distances, reduce_angle


def approx_equal(v1, v2, tol=0.001):
    return abs(v1 - v2) <= tol


def angles_approx_equal(v1, v2, tol=0.001):
    # Assume both angles are reduced but if they're both
    # close to math.pi then one can be negative and one positive
    return (
        approx_equal(v1, v2, tol)
        or approx_equal(v1 + 2 * math.pi, v2, tol)
        or approx_equal(v1, v2 + 2 * math.pi, tol)
    )


def assert_equal_pose(p1, p2, tol=0.001):
    assert (
        approx_equal(p1.x, p2.x, tol)
        and approx_equal(p1.y, p2.y, tol)
        and angles_approx_equal(p1.theta, p2.theta, tol)
    ), f"{p1} != {p2}"


def test_reduce_angle():

    assert approx_equal(reduce_angle(0.5 * math.pi), 0.5 * math.pi)
    assert approx_equal(reduce_angle(2.5 * math.pi), 0.5 * math.pi)
    assert approx_equal(reduce_angle(1000.5 * math.pi), 0.5 * math.pi)

    assert approx_equal(reduce_angle(1.5 * math.pi), -0.5 * math.pi)
    assert approx_equal(reduce_angle(3.5 * math.pi), -0.5 * math.pi)
    assert approx_equal(reduce_angle(1001.5 * math.pi), -0.5 * math.pi)

    assert approx_equal(reduce_angle(-0.5 * math.pi), -0.5 * math.pi)
    assert approx_equal(reduce_angle(-2.5 * math.pi), -0.5 * math.pi)
    assert approx_equal(reduce_angle(-1000.5 * math.pi), -0.5 * math.pi)

    assert approx_equal(reduce_angle(-1.5 * math.pi), 0.5 * math.pi)
    assert approx_equal(reduce_angle(-3.5 * math.pi), 0.5 * math.pi)
    assert approx_equal(reduce_angle(-1001.5 * math.pi), 0.5 * math.pi)

    assert approx_equal(reduce_angle(2 * math.pi), 0.0)
    assert approx_equal(reduce_angle(1000 * math.pi), 0.0)
    assert approx_equal(reduce_angle(-2 * math.pi), 0.0)
    assert approx_equal(reduce_angle(-1000 * math.pi), 0.0)

    assert angles_approx_equal(reduce_angle(math.pi), math.pi)
    assert angles_approx_equal(reduce_angle(3 * math.pi), math.pi)
    assert angles_approx_equal(reduce_angle(1001 * math.pi), math.pi)
    assert angles_approx_equal(reduce_angle(-math.pi), math.pi)
    assert angles_approx_equal(reduce_angle(-3 * math.pi), math.pi)
    assert angles_approx_equal(reduce_angle(-1001 * math.pi), math.pi)


def test_pose_addition():
    assert_equal_pose(
        Pose2D(0.0, 0.0, 0.0) + Pose2D(0.0, 0.0, 0.0), Pose2D(0.0, 0.0, 0.0)
    )

    assert_equal_pose(
        Pose2D(0.0, 0.0, 0.0) + Pose2D(1.0, 2.0, 0.0), Pose2D(1.0, 2.0, 0.0)
    )

    assert_equal_pose(
        Pose2D(1.0, 2.0, 0.0) + Pose2D(3.0, 4.0, 0.0), Pose2D(4.0, 6.0, 0.0)
    )

    assert_equal_pose(
        Pose2D(0.0, 0.0, math.pi / 2) + Pose2D(0.0, 0.0, math.pi / 4),
        Pose2D(0.0, 0.0, 3 * math.pi / 4),
    )

    assert_equal_pose(
        Pose2D(1.0, 0.0, math.pi / 2) + Pose2D(1.0, 0.0, math.pi / 4),
        Pose2D(1.0, 1.0, 3 * math.pi / 4),
    )

    assert_equal_pose(
        Pose2D(1.0, 0.0, math.pi / 4) + Pose2D(1.0, 0.0, math.pi / 4),
        Pose2D(1.0 + 1 / math.sqrt(2), 1 / math.sqrt(2), math.pi / 2),
    )

    assert_equal_pose(
        Pose2D(1.0, 0.0, -math.pi / 4) + Pose2D(1.0, 0.0, math.pi / 4),
        Pose2D(1.0 + 1 / math.sqrt(2), -1 / math.sqrt(2), 0.0),
    )


def test_pose_from_dist_zero_pose():
    assert_equal_pose(pose_from_wheel_distances(0.0, 0.0, 1.0), Pose2D(0.0, 0.0, 0.0))


def test_pose_from_dist_straight_ahead():
    # Straight ahead
    assert_equal_pose(pose_from_wheel_distances(1.0, 1.0, 1.0), Pose2D(1.0, 0.0, 0.0))


def test_pose_from_dist_one_wheel():
    # One wheel stationary, the other moving. Had a divide-by-zero
    # bug for this case so this is a regression test.
    assert_equal_pose(
        pose_from_wheel_distances(0.0, math.pi, 2.0), Pose2D(1.0, 1.0, math.pi / 2)
    )

    assert_equal_pose(
        pose_from_wheel_distances(0.0, -math.pi, 2.0), Pose2D(-1.0, 1.0, -math.pi / 2)
    )

    assert_equal_pose(
        pose_from_wheel_distances(math.pi, 0.0, 2.0), Pose2D(1.0, -1.0, -math.pi / 2)
    )

    assert_equal_pose(
        pose_from_wheel_distances(-math.pi, 0.0, 2.0), Pose2D(-1.0, -1.0, math.pi / 2)
    )


def test_pose_from_dist_turn_in_place():
    # Rotate full-turn in place to right
    assert_equal_pose(
        pose_from_wheel_distances(-2 * math.pi, 2 * math.pi, 2.0), Pose2D(0.0, 0.0, 0.0)
    )

    # Rotate half-turn in place to right
    assert_equal_pose(
        pose_from_wheel_distances(-math.pi, math.pi, 2.0), Pose2D(0.0, 0.0, math.pi)
    )

    # Rotate full-turn in place to left
    assert_equal_pose(
        pose_from_wheel_distances(2 * math.pi, -2 * math.pi, 2.0), Pose2D(0.0, 0.0, 0.0)
    )

    # Rotate half-turn in place to left
    assert_equal_pose(
        pose_from_wheel_distances(math.pi, -math.pi, 2.0), Pose2D(0.0, 0.0, math.pi)
    )


def test_pose_from_dist_outer_arcs():
    # 1/4 of a forward rotation about a circle centered one wheel-base to the left
    # of the left wheel, wheel-base = 1.0
    assert_equal_pose(
        pose_from_wheel_distances(math.pi / 2, math.pi, 1.0),
        Pose2D(1.5, 1.5, 0.5 * math.pi),
    )

    # 1/4 of a forward rotation about a circle centered one wheel-base to the left
    # of the left wheel, wheel-base = 2.0
    assert_equal_pose(
        pose_from_wheel_distances(math.pi, 2 * math.pi, 2.0),
        Pose2D(3.0, 3.0, 0.5 * math.pi),
    )

    # 1/4 of a reverse rotation about a circle centered one wheel-base to the left
    # of the left wheel, wheel-base = 1.0
    assert_equal_pose(
        pose_from_wheel_distances(-math.pi / 2, -math.pi, 1.0),
        Pose2D(-1.5, 1.5, -0.5 * math.pi),
    )

    # 1/4 of a reverse rotation about a circle centered one wheel-base to the left
    # of the left wheel, wheel-base = 2.0
    assert_equal_pose(
        pose_from_wheel_distances(-math.pi, -2 * math.pi, 2.0),
        Pose2D(-3.0, 3.0, -0.5 * math.pi),
    )

    # 1/4 of a forward rotation about a circle centered one wheel-base to the right
    # of the right wheel, wheel-base = 1.0
    assert_equal_pose(
        pose_from_wheel_distances(math.pi, math.pi / 2, 1.0),
        Pose2D(1.5, -1.5, -0.5 * math.pi),
    )

    # 1/4 of a forward rotation about a circle centered one wheel-base to the right
    # of the right wheel, wheel-base = 2.0
    assert_equal_pose(
        pose_from_wheel_distances(2 * math.pi, math.pi, 2.0),
        Pose2D(3.0, -3.0, -0.5 * math.pi),
    )

    # 1/4 of a reverse rotation about a circle centered one wheel-base to the right
    # of the right wheel, wheel-base = 1.0
    assert_equal_pose(
        pose_from_wheel_distances(-math.pi, -math.pi / 2, 1.0),
        Pose2D(-1.5, -1.5, 0.5 * math.pi),
    )

    # 1/4 of a reverse rotation about a circle centered one wheel-base to the right
    # of the right wheel, wheel-base = 2.0
    assert_equal_pose(
        pose_from_wheel_distances(-2 * math.pi, -math.pi, 2.0),
        Pose2D(-3.0, -3.0, 0.5 * math.pi),
    )


def test_pose_from_dist_inner_arcs():
    # 1/4 of a forward rotation about a circle centered 1/3 wheel-base to the right
    # of the left wheel, wheel-base = 3.0
    assert_equal_pose(
        pose_from_wheel_distances(-math.pi / 2, math.pi, 3.0),
        Pose2D(0.5, 0.5, 0.5 * math.pi),
    )

    # 1/4 of a reverse rotation about a circle centered 1/3 wheel-base to the right
    # of the left wheel, wheel-base = 3.0
    assert_equal_pose(
        pose_from_wheel_distances(math.pi / 2, -math.pi, 3.0),
        Pose2D(-0.5, 0.5, -0.5 * math.pi),
    )

    # 1/4 of a forward rotation about a circle centered 1/3 wheel-base to the left
    # of the right wheel, wheel-base = 3.0
    assert_equal_pose(
        pose_from_wheel_distances(math.pi, -math.pi / 2, 3.0),
        Pose2D(0.5, -0.5, -0.5 * math.pi),
    )

    # 1/4 of a reverse rotation about a circle centered 1/3 wheel-base to the left
    # of the right wheel, wheel-base = 3.0
    assert_equal_pose(
        pose_from_wheel_distances(-math.pi, math.pi / 2, 3.0),
        Pose2D(-0.5, -0.5, 0.5 * math.pi),
    )
