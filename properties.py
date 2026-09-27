"""ArborTools — Blender property definitions."""

import bpy

from .defaults import DEFAULTS


def _update_video_file(self, context):
    """Read frame count when video file changes and set end_frame."""
    path = bpy.path.abspath(self.video_file)
    if not path:
        self["total_frames"] = 0
        return
    try:
        import cv2

        cap = cv2.VideoCapture(path)
        if cap.isOpened():
            count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self["total_frames"] = count
            self["end_frame"] = count
            cap.release()
        else:
            self["total_frames"] = 0
    except Exception:
        self["total_frames"] = 0


class ArborToolsProperties(bpy.types.PropertyGroup):
    # --- Method ---
    method: bpy.props.EnumProperty(
        name="Method",
        items=[
            (
                "OPTICAL_FLOW",
                "Optical Flow",
                "Generate points from motion between frames",
            ),
            (
                "FRAME_STACKING",
                "Frame Stacking",
                "Each frame becomes a layer of colored points",
            ),
            (
                "FRAME_DIFFERENCE",
                "Frame Difference",
                "Points where consecutive frames differ",
            ),
            (
                "OPTICAL_FLOW_VIDEO",
                "Optical Flow Video",
                "Generate HSV-visualized flow video",
            ),
        ],
        default="OPTICAL_FLOW",
    )

    # --- Input ---
    video_file: bpy.props.StringProperty(
        name="Video File",
        update=_update_video_file,
    )
    output_ply: bpy.props.StringProperty(
        name="Output PLY",
    )
    output_video: bpy.props.StringProperty(
        name="Output Video",
    )

    # --- Frame Range ---
    start_frame: bpy.props.IntProperty(
        name="Start Frame",
        default=0,
        min=0,
    )
    end_frame: bpy.props.IntProperty(
        name="End Frame",
        default=0,
        min=0,
        description="Last frame to process (0 = end of video)",
    )
    total_frames: bpy.props.IntProperty(
        name="Total Frames",
        default=0,
        description="Total frames in the video (read-only)",
    )

    # --- Sampling ---
    skip_frames: bpy.props.IntProperty(
        name="Skip Frames",
        default=DEFAULTS["skip_frames"],
        min=1,
        description="Process every N-th frame",
    )
    skip_pixels: bpy.props.IntProperty(
        name="Skip Pixels",
        default=DEFAULTS["skip_pixels"],
        min=1,
        description="Sample every N-th pixel",
    )

    # --- Filtering ---
    flow_threshold: bpy.props.FloatProperty(
        name="Flow Threshold",
        default=DEFAULTS["flow_threshold"],
        min=0.0,
        max=1.0,
        description="Minimum normalized speed to include a point",
    )
    max_speed_clip: bpy.props.FloatProperty(
        name="Max Speed Clip",
        default=DEFAULTS["max_speed_clip"],
        min=1.0,
        description="Upper bound for speed normalization (px/frame)",
    )
    brightness_min: bpy.props.IntProperty(
        name="Brightness Min",
        default=DEFAULTS["brightness_min"],
        min=0,
        max=255,
        description="Minimum pixel brightness to include (0 = no limit)",
    )
    brightness_max: bpy.props.IntProperty(
        name="Brightness Max",
        default=DEFAULTS["brightness_max"],
        min=0,
        max=255,
        description="Maximum pixel brightness to include (255 = no limit)",
    )
    density_mode: bpy.props.BoolProperty(
        name="Density Mode",
        default=DEFAULTS["density_mode"],
        description="Darker pixels get denser points (Brightness Min = all, Max = none)",
    )
    density_gamma: bpy.props.FloatProperty(
        name="Density Gamma",
        default=DEFAULTS["density_gamma"],
        min=0.1,
        max=10.0,
        description="Shapes the density ramp: >1 thins midtones, <1 fills them",
    )
    jitter: bpy.props.BoolProperty(
        name="Jitter",
        default=DEFAULTS["jitter"],
        description="Random sub-pixel XY offset to hide the pixel grid",
    )
    diff_threshold: bpy.props.FloatProperty(
        name="Diff Threshold",
        default=DEFAULTS["diff_threshold"],
        min=0.0,
        max=255.0,
        description="Minimum pixel difference magnitude to include a point",
    )

    # --- Optical Flow ---
    algorithm: bpy.props.EnumProperty(
        name="Algorithm",
        items=[
            ("FARNEBACK", "Farneback", "High quality, slower"),
            ("DIS", "DIS", "Fast preview quality"),
        ],
        default=DEFAULTS["algorithm"].upper(),
    )
    pyr_scale: bpy.props.FloatProperty(
        name="Pyramid Scale",
        default=DEFAULTS["pyr_scale"],
        min=0.1,
        max=0.9,
        description=(
            "How much each analysis layer is shrunk. "
            "Lower values detect larger movements but take longer"
        ),
    )
    levels: bpy.props.IntProperty(
        name="Levels",
        default=DEFAULTS["levels"],
        min=1,
        max=8,
        description=(
            "Number of analysis layers. "
            "More levels capture bigger movements but increase processing time"
        ),
    )
    winsize: bpy.props.IntProperty(
        name="Window Size",
        default=DEFAULTS["winsize"],
        min=5,
        max=50,
        description=(
            "Size of the area examined around each pixel. "
            "Larger values produce smoother flow but lose fine detail"
        ),
    )
    iterations: bpy.props.IntProperty(
        name="Iterations",
        default=DEFAULTS["iterations"],
        min=1,
        max=10,
        description=(
            "How many times the algorithm refines the result. "
            "More iterations give better accuracy but take longer"
        ),
    )
    poly_n: bpy.props.EnumProperty(
        name="Poly N",
        items=[
            ("5", "5", "Faster, works well for most videos"),
            ("7", "7", "Smoother results, better for complex motion"),
        ],
        default=str(DEFAULTS["poly_n"]),
        description=(
            "Size of the pixel neighborhood used to estimate motion. "
            "5 is faster, 7 is smoother"
        ),
    )
    poly_sigma: bpy.props.FloatProperty(
        name="Poly Sigma",
        default=DEFAULTS["poly_sigma"],
        min=1.0,
        max=2.0,
        description=(
            "How much to blur the neighborhood before estimating motion. "
            "Higher values smooth out noise but may lose sharp edges"
        ),
    )

    # --- Processing ---
    resize_percent: bpy.props.IntProperty(
        name="Resize for Flow (%)",
        default=DEFAULTS["resize_percent"],
        min=25,
        max=100,
        description="Downscale frames before computing optical flow",
    )
    max_points: bpy.props.IntProperty(
        name="Max Points",
        default=DEFAULTS["max_points"],
        min=1000,
        description="Hard limit on total point count",
    )

    # --- Scale ---
    point_distance: bpy.props.FloatProperty(
        name="Point Distance",
        default=DEFAULTS["point_distance"],
        min=0.001,
        soft_min=0.01,
        soft_max=10.0,
        description="Distance between points within the same layer (XY scale)",
    )
    layer_distance: bpy.props.FloatProperty(
        name="Layer Distance",
        default=DEFAULTS["layer_distance"],
        min=0.001,
        soft_min=0.01,
        soft_max=10.0,
        description="Distance between layers along the Z axis",
    )

    # --- UI state ---
    is_processing: bpy.props.BoolProperty(
        name="Is Processing",
        default=False,
    )
    progress_text: bpy.props.StringProperty(
        name="Progress",
        default="",
    )

    # --- Flow Video ---
    export_grid: bpy.props.BoolProperty(
        name="Export Grid",
        default=False,
        description="Save a grid of flow frames as PNG alongside the video",
    )
    grid_size: bpy.props.StringProperty(
        name="Grid Size",
        default="10x10",
        description="Grid dimensions as COLSxROWS (e.g. 10x10, 5x8)",
    )
    grid_numbers: bpy.props.BoolProperty(
        name="Show Frame Numbers",
        default=False,
        description="Show frame numbers in the bottom-right corner of each grid cell",
    )

    # --- Section folds ---
    show_frame_range: bpy.props.BoolProperty(name="Frame Range", default=False)
    show_sampling: bpy.props.BoolProperty(name="Sampling", default=False)
    show_filtering: bpy.props.BoolProperty(name="Filtering", default=False)
    show_optical_flow: bpy.props.BoolProperty(name="Optical Flow", default=False)
    show_processing: bpy.props.BoolProperty(name="Processing", default=False)
    show_scale: bpy.props.BoolProperty(name="Scale", default=False)
    show_flow_video: bpy.props.BoolProperty(name="Flow Video", default=False)


def register():
    bpy.utils.register_class(ArborToolsProperties)
    bpy.types.Scene.optflow = bpy.props.PointerProperty(type=ArborToolsProperties)


def unregister():
    del bpy.types.Scene.optflow
    bpy.utils.unregister_class(ArborToolsProperties)
