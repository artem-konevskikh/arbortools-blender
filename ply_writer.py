"""Write binary little-endian PLY files with optical-flow attributes."""

import struct
import numpy as np


def write_ply(filepath, points, colors, attrs, frame_indices):
    """Write a PLY file with the ArborTools schema.

    Parameters
    ----------
    filepath : str
        Output .ply path.
    points : ndarray (N, 3) float32
        x, y, z coordinates.
    colors : ndarray (N, 3) uint8
        R, G, B per vertex.
    attrs : ndarray (N, 4) float32
        speed, angle, flow_x, flow_y per vertex.
    frame_indices : ndarray (N,) int32
        Frame pair index per vertex.
    """
    n = len(points)

    header = (
        "ply\n"
        "format binary_little_endian 1.0\n"
        f"element vertex {n}\n"
        "property float x\n"
        "property float y\n"
        "property float z\n"
        "property uchar red\n"
        "property uchar green\n"
        "property uchar blue\n"
        "property float speed\n"
        "property float angle\n"
        "property float flow_x\n"
        "property float flow_y\n"
        "property int frame_index\n"
        "end_header\n"
    )

    # Ensure correct dtypes
    points = np.ascontiguousarray(points, dtype=np.float32)
    colors = np.ascontiguousarray(colors, dtype=np.uint8)
    attrs = np.ascontiguousarray(attrs, dtype=np.float32)
    frame_indices = np.ascontiguousarray(frame_indices, dtype=np.int32)

    with open(filepath, "wb") as f:
        f.write(header.encode("ascii"))

        # Pack vertex data: 3f + 3B + 4f + 1i = 35 bytes per vertex
        for i in range(n):
            f.write(
                struct.pack(
                    "<3f3B4fi",
                    points[i, 0],
                    points[i, 1],
                    points[i, 2],
                    colors[i, 0],
                    colors[i, 1],
                    colors[i, 2],
                    attrs[i, 0],
                    attrs[i, 1],
                    attrs[i, 2],
                    attrs[i, 3],
                    frame_indices[i],
                )
            )
