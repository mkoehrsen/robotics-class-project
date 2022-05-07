import argparse
import calibration
import cv2
import dt_apriltags
import itertools
import numpy as np
import vehctl
import tempfile

def project_floor(lower, upper):
    # Distance between points - 1.75"
    # Distance from lower to floor - 5.5"
    scale = 5.5/1.75

    # Note lower has the larger y value.
    # Cheating here a bit by not projecting through the vertical distance exactly,
    # but the assumption is that the x values will be nearly identical
    return [lower[0] + scale*(lower[0] - upper[0]), lower[1] + scale*(lower[1] - upper[1])]


def estimate_transform(vehicle_points, world_points):
    
    # a 2D port of https://github.com/nghiaho12/rigid_transform_3D/blob/master/rigid_transform_3D.py

    # the caller will slice, because we don't need the trailing 1's
    # and we'd rather not have them distract us in this tricky operation
    assert world_points.shape[1] == 2, "Expected data like [ [X,Y], [X,Y], ... ]. Please trim off a unit third dimension."
    assert vehicle_points.shape[1] == 2
    
    # organize the data like the method expects
    A = vehicle_points.T
    B = world_points.T

    centroid_A = np.mean(A, axis=1).reshape(-1, 1)
    centroid_B = np.mean(B, axis=1).reshape(-1, 1)

    Am = A - centroid_A
    Bm = B - centroid_B

    H = Am @ np.transpose(Bm)

    U, S, Vt = np.linalg.svd(H)
    R = Vt.T @ U.T

    if np.linalg.det(R) < 0:
        # print("correcting for reflection")
        Vt[1,:] *= -1
        R = Vt.T @ U.T

    t = -R @ centroid_A + centroid_B
    
    transform = np.concatenate((
        np.concatenate((R, np.zeros((1,2)))),
        np.concatenate((t, np.ones((1,1))))
    ), axis=1)
    return transform

def vehicle2world(v2w_matrix, points):
    points = np.array(points)
    points = np.concatenate([points, np.ones((points.shape[0], 1))], axis=1)
    pred = (v2w_matrix @ points.T).T
    return np.split(pred, [2], axis=1)[0]

def print_tag_points(msg, tag2points):
    print(msg)
    for (tag_id, points) in tag2points.items():
        print(tag_id, points)

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--orientation", type=int, default=0) # TODO -- should be vehicle config
    args = parser.parse_args()

    # Map from tag_id to ((x1, y1), (x2, y2)) in world coordinates
    # Two points correspond to a tag based on projecting down to floor.
    tag_world_points = {}

    veh = vehctl.Vehicle()
    veh_hmat, _, _ = calibration.read_calibration()

    # pseudocode:
    # until stop:
    #   take an image, look for tags
    #   for each tag, project points down to floor
    #   map points to vehicle coordinates
    #   if first time (i.e. no tags yet):
    #       store coordinates as world coordinates
    #   else if known tags are visible:
    #       estimate new transform from known tags
    #       use new transform to map new tags to world coordinates
    #       store world coordinates
    #   else:
    #       panic?

    tmpdir = tempfile.mkdtemp()
    at_detector = dt_apriltags.Detector(
            searchpath=["apriltags"],
            families="tagStandard41h12",
            nthreads=1,
            quad_decimate=1.0,
            quad_sigma=0.0,
            refine_edges=1,
            decode_sharpening=0.25,
            debug=0,
        )

    
    for _ in range(3):
        img = cv2.cvtColor(calibration.capture_image(tmpdir, args.orientation), cv2.COLOR_RGB2GRAY)
        tags = at_detector.detect(img)

        # Mapping from tag id to points in vehicle coordinates
        tag_veh_points = {
            t.tag_id: calibration.apply_homography(veh_hmat, [
                project_floor(t.corners[0], t.corners[3]),
                project_floor(t.corners[1], t.corners[2])
            ])
            for t in tags
        }

        print_tag_points("Current points in vehicle coordinates", tag_veh_points)

        if len(tag_world_points) > 0:
            # For detected tags, partition into known and unknown
            # for consistent ordering.
            known_tags = list(set(tag_veh_points.keys()).intersection(tag_world_points.keys()))
            new_tags = list(set(tag_veh_points.keys()).difference(tag_world_points.keys()))

            # Construct parallel arrays of vehicle points and 
            # world points from known tags
            known_veh_points = list(itertools.chain(*[tag_veh_points[tag_id] for tag_id in known_tags]))
            known_world_points = list(itertools.chain(*[tag_world_points[tag_id] for tag_id in known_tags]))

            assert len(known_world_points) > 0, "No common points"        

            v2w_matrix = estimate_transform(
                np.array(known_veh_points), np.array(known_world_points)
            )

            new_veh_points = list(itertools.chain(*[tag_veh_points[tag_id] for tag_id in new_tags]))
            new_world_points = [(p[0], p[1]) for p in vehicle2world(v2w_matrix, new_veh_points)]

            # Gather new world points into pairs and associate with tag ids:
            for (i, tag_id) in enumerate(new_tags):
                tag_world_points[tag_id] = [new_world_points[i*2], new_world_points[i*2+1]]

        else:
            # First time through, use current coordinate frame as world frame
            tag_world_points.update(tag_veh_points)
        
        print_tag_points("All known points in world coordinates: ", tag_world_points)
        veh.perform_action(4, 3) # Right 45 degrees TODO fix


if __name__=='__main__':
    main()