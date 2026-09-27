"""Default parameter values shared by the add-on UI and the CLIs (no bpy imports)."""

DEFAULTS = {
    # Sampling
    "skip_frames": 5,
    "skip_pixels": 2,
    # Filtering
    "flow_threshold": 0.01,
    "max_speed_clip": 50.0,
    "brightness_min": 0,
    "brightness_max": 127,
    "diff_threshold": 10.0,
    # Optical flow
    "algorithm": "farneback",
    "pyr_scale": 0.5,
    "levels": 3,
    "winsize": 15,
    "iterations": 3,
    "poly_n": 5,
    "poly_sigma": 1.2,
    # Processing
    "resize_percent": 50,
    "max_points": 15_000_000,
    # Scale
    "point_distance": 0.01,
    "layer_distance": 0.01,
}
