import argparse
import time
import calibration
import cv2
import dt_apriltags
import itertools
import numpy as np
import vehctl
import camera
import tempfile


def project_floor(lower, upper):
    # Distance between points - 1.75"
    # Distance from lower to floor - 5.5"
    scale = 5.5 / 1.75

    # Note lower has the larger y value.
    # Cheating here a bit by not projecting through the vertical distance exactly,
    # but the assumption is that the x values will be nearly identical
    return [
        lower[0] + scale * (lower[0] - upper[0]),
        lower[1] + scale * (lower[1] - upper[1]),
    ]


def estimate_transform(vehicle_points, world_points):

    # a 2D port of https://github.com/nghiaho12/rigid_transform_3D/blob/master/rigid_transform_3D.py

    # the caller will slice, because we don't need the trailing 1's
    # and we'd rather not have them distract us in this tricky operation
    assert (
        world_points.shape[1] == 2
    ), "Expected data like [ [X,Y], [X,Y], ... ]. Please trim off a unit third dimension."
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
        Vt[1, :] *= -1
        R = Vt.T @ U.T

    t = -R @ centroid_A + centroid_B

    transform = np.concatenate(
        (np.concatenate((R, np.zeros((1, 2)))), np.concatenate((t, np.ones((1, 1))))),
        axis=1,
    )
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


def render_tag_points(tag2points):

    page_height = 792
    page_width = 612
    margin = 36
    padding = 36
    content_height = page_height - (margin + padding) * 2
    content_width = page_width - (margin + padding) * 2

    import xml.etree.ElementTree as ET

    doc = ET.Element(
        "svg",
        width=f"{page_width - margin * 2}px",
        height=f"{page_height - margin * 2}px",
        xmlns="http://www.w3.org/2000/svg",
    )

    all_points = list(itertools.chain(*tag2points.values()))
    minX = min(p[0] for p in all_points)
    maxX = max(p[0] for p in all_points)
    minY = min(p[1] for p in all_points)
    maxY = max(p[1] for p in all_points)

    scale = min(content_height / (maxY - minY), content_width / (maxX - minX))

    for tag_id, point_pair in tag2points.items():

        p1 = (
            padding + (point_pair[0][0] - minX) * scale,
            padding + content_height - (point_pair[0][1] - minY) * scale,
        )
        p2 = (
            padding + (point_pair[1][0] - minX) * scale,
            padding + content_height - (point_pair[1][1] - minY) * scale,
        )

        for (p, color) in ((p1, "red"), (p2, "blue")):
            doc.append(
                ET.Element("circle", cx=f"{p[0]}", cy=f"{p[1]}", r="5", fill="blue")
            )
        doc.append(
            ET.Element(
                "line",
                x1=f"{p1[0]}",
                y1=f"{p1[1]}",
                x2=f"{p2[0]}",
                y2=f"{p2[1]}",
                stroke="blue",
                attrib={"stroke-width": "2"},
            )
        )
        text_elt = ET.Element("text", x=f"{(p1[0]+p2[0])/2}", y=f"{(p1[1]+p2[1])/2}")
        text_elt.text = f"{tag_id:05}"
        doc.append(text_elt)

    return ET.tostring(doc, encoding="unicode")


def main():

    # Test data for rendering
    # tag_world_points = {
    #     18: [(0.38936018, 16.8079425), (2.3037887, 16.38510553)],
    #     19: [
    #         (3.9366813277302741, 15.838889235857884),
    #         (5.7602187644177416, 15.301671626938282),
    #     ],
    #     20: [
    #         (7.5551912861664823, 14.827861067095164),
    #         (9.3985415901691773, 14.243508646326813),
    #     ],
    #     21: [
    #         (12.298711920109973, 13.32563847590211),
    #         (14.042032819960561, 12.700948011602071),
    #     ],
    #     22: [
    #         (15.743587909422775, 12.216475580892704),
    #         (17.300643259026305, 11.454566086209782),
    #     ],
    #     23: [
    #         (19.020575631881105, 10.874312801286353),
    #         (20.853330582946654, 10.201428351967861),
    #     ],
    #     24: [
    #         (22.93847015380188, 9.0307398405251966),
    #         (24.726446503527541, 8.4391847541481617),
    #     ],
    #     25: [
    #         (26.513077737731553, 7.8239813125318971),
    #         (28.363586367320579, 6.8953166425646568),
    #     ],
    #     9: [
    #         (33.322556028032054, 5.562693738621336),
    #         (31.861675699473182, 3.6366842345437274),
    #     ],
    #     10: [
    #         (30.821939340094403, 1.9768623959794125),
    #         (29.840917786834545, 0.19485238577630692),
    #     ],
    #     11: [
    #         (28.837671866335576, -1.373819329316051),
    #         (27.88771972744231, -3.1498705838234118),
    #     ],
    #     12: [
    #         (26.773907850286736, -5.6696063551233511),
    #         (25.763101080239558, -7.4474932750420306),
    #     ],
    #     13: [
    #         (24.901046826186022, -9.0137155855634745),
    #         (24.06625113236213, -10.784002753634647),
    #     ],
    #     14: [
    #         (23.243635184528497, -12.390298893292812),
    #         (22.197161494646544, -14.010099695362918),
    #     ],
    #     15: [
    #         (20.47192823485425, -15.974737459503753),
    #         (19.382762030394851, -17.330167844535467),
    #     ],
    #     16: [
    #         (18.587693439112083, -18.72432987837221),
    #         (17.595034790625647, -20.325839959647141),
    #     ],
    #     3: [
    #         (16.882597154346641, -22.660578720073907),
    #         (15.204009475844121, -21.828607271878546),
    #     ],
    #     4: [
    #         (13.718769315320234, -21.099175277528879),
    #         (12.107495915108704, -20.306205602934128),
    #     ],
    #     0: [
    #         (7.8135910153422135, -17.391051697681995),
    #         (5.5342386860849082, -16.172658209291864),
    #     ],
    #     1: [
    #         (3.7871324286525798, -15.402064278129746),
    #         (1.8949495498438043, -14.540519154674449),
    #     ],
    #     5: [
    #         (10.967363617044159, -19.274560455591661),
    #         (9.3249248406029412, -18.310187550680844),
    #     ],
    # }
    # print(render_tag_points(tag_world_points))
    # return

    # parser = argparse.ArgumentParser()
    # args = parser.parse_args()

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

    frame_reader = camera.FrameSession(veh.config.vehicle.cameraOrientation, save="/tmp")

    num_steps = 10
    for step in range(num_steps):

        # allow some time for the vehicle to settle and give a crisp image
        for i in range(10):
            img = cv2.cvtColor(next(frame_reader), cv2.COLOR_RGB2GRAY)
            tags = at_detector.detect(img)
            if tags:
                break
            time.sleep(0.01)

        # Mapping from tag id to points in vehicle coordinates
        tag_veh_points = {
            t.tag_id: calibration.apply_homography(
                veh_hmat,
                [
                    project_floor(t.corners[0], t.corners[3]),
                    project_floor(t.corners[1], t.corners[2]),
                ],
            )
            for t in tags
        }

        print_tag_points("Current points in vehicle coordinates", tag_veh_points)

        if len(tag_world_points) > 0:
            # For detected tags, partition into known and unknown
            # for consistent ordering.
            known_tags = list(
                set(tag_veh_points.keys()).intersection(tag_world_points.keys())
            )
            new_tags = list(
                set(tag_veh_points.keys()).difference(tag_world_points.keys())
            )

            # Construct parallel arrays of vehicle points and
            # world points from known tags
            known_veh_points = list(
                itertools.chain(*[tag_veh_points[tag_id] for tag_id in known_tags])
            )
            known_world_points = list(
                itertools.chain(*[tag_world_points[tag_id] for tag_id in known_tags])
            )

            assert len(known_world_points) > 0, "No common points"

            v2w_matrix = estimate_transform(
                np.array(known_veh_points), np.array(known_world_points)
            )

            new_veh_points = list(
                itertools.chain(*[tag_veh_points[tag_id] for tag_id in new_tags])
            )
            if len(new_veh_points) == 0:
                print("No new points observed; continuing.")
                continue
            new_world_points = [
                (p[0], p[1]) for p in vehicle2world(v2w_matrix, new_veh_points)
            ]

            # Gather new world points into pairs and associate with tag ids:
            for (i, tag_id) in enumerate(new_tags):
                tag_world_points[tag_id] = [
                    new_world_points[i * 2],
                    new_world_points[i * 2 + 1],
                ]

        else:
            # First time through, use current coordinate frame as world frame
            tag_world_points.update(tag_veh_points)

        print_tag_points("All known points in world coordinates: ", tag_world_points)
        veh.perform_action(vehctl.Direction.RIGHT, 180 // num_steps)

        mapfile = f"map{step}.svg"
        with open(mapfile, "wt") as f:
            print(f"Writing current map to {mapfile}")
            f.write(render_tag_points(tag_world_points))

    frame_reader.close()

if __name__ == "__main__":
    main()
