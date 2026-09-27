"""Write binary little-endian PLY files with optical-flow attributes."""

import numpy as np

# Packed little-endian layout, 35 bytes per vertex (same as struct "<3f3B4fi")
VERTEX_DTYPE = np.dtype(
    [
        ("x", "<f4"),
        ("y", "<f4"),
        ("z", "<f4"),
        ("red", "u1"),
        ("green", "u1"),
        ("blue", "u1"),
        ("speed", "<f4"),
        ("angle", "<f4"),
        ("flow_x", "<f4"),
        ("flow_y", "<f4"),
        ("frame_index", "<i4"),
    ]
)
CHUNK = 1_000_000


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

    with open(filepath, "wb") as f:
        f.write(header.encode("ascii"))
        # Chunked so the packed copy adds ~35 MB peak, not 35 bytes * n
        for s in range(0, n, CHUNK):
            e = min(s + CHUNK, n)
            v = np.empty(e - s, dtype=VERTEX_DTYPE)
            v["x"], v["y"], v["z"] = points[s:e].T
            v["red"], v["green"], v["blue"] = colors[s:e].T
            v["speed"], v["angle"], v["flow_x"], v["flow_y"] = attrs[s:e].T
            v["frame_index"] = frame_indices[s:e]
            v.tofile(f)
