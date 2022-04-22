from dataclasses import dataclass
import math

def reduce_angle(theta):
    """
    Given an angle in radians, returns an equivalent angle
    in the range [-pi, pi].
    """
    sign = -1 if theta < 0 else 1
    theta = abs(theta)
    return sign * (theta - round(theta/(2*math.pi))*2*math.pi)

@dataclass(frozen=True)
class Pose2D:
    x: float = 0.0
    y: float = 0.0
    theta: float = 0.0

    def __add__(self, other):
        """
        Construct a new instance by adding self to another Pose2D instance.
        The other instance is interpreted as being in a coordinate frame whose
        origin is the (x, y) coordinate of this instance, and whose orientation
        is given by the rotation (theta) of this instance. The resulting instance
        will be in the same coordinate frame as self. See tests for examples.
        """
        return Pose2D(self.x + other.x * math.cos(self.theta) - other.y * math.sin(self.theta), 
                      self.y + other.x * math.sin(self.theta) + other.y * math.cos(self.theta), 
                      reduce_angle(self.theta + other.theta))
    
    def mirrorX(self):
        """
        Return a pose that is the result of mirroring self about the X axis.
        """
        return Pose2D(self.x, -self.y, -self.theta)
    
    def to_json_obj(self):
        """
        Return a json-serializable representation of this object.
        """
        return dict(x=self.x, y=self.y, theta=self.theta)

def pose_from_wheel_distances(left, right, wheel_base, tol=.001):
    """
    Assuming a vehicle starts at Pose2D(0, 0, 0), compute the pose
    after the left and right wheels travel the specified distances.
    The pose is taken to be at the center point between the two wheels.
    We do this by assuming the left and right wheels travel on concentric
    circles whose radii are proportional to the distance traveled.

    The `tol` argument is a tolerance value for determining equality.
    Not sure if it's a real concern but I want to avoid weird numeric 
    problems due to differences being very close to zero.
    """
    if abs(left - right) <= tol:
        # Simple special case, we get division by zero otherwise
        return Pose2D(left, 0.0, 0.0)
    else:
        # With w == wheel_base, take wheels to have started at positions
        # leftpos = (0, w/2) and rightpos (0, -w/2), so the center point
        # started at (0, 0)
        # Find c such that the center of the circle of travel of the center
        # point is at (0, c).
        # This formula works for all cases except left==right which 
        # is covered above.
        c = wheel_base/2 + (left/(right-left))*wheel_base

        # Get rotation angle. The right wheel is at a radius of 
        # (c+(wheel_base/2)). This can be negative but that means
        # the car is turning towards the right which gives the
        # sign of theta correctly.
        # (Assuming right is positive -- if it's negative the signs
        # still work out).
        theta = right/(c+(wheel_base/2))

        # Reinterpret the center of the car as being at (0, -c),
        # rotate it through angle theta, then add (0, c) back:
        x = c*math.sin(theta)
        y = c - c*math.cos(theta)
        return Pose2D(x, y, reduce_angle(theta))


if __name__ == "__main__":
    import doctest
    doctest.testmod()
