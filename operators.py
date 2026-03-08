"""ArborTools — Blender operators."""

import os
import tempfile
import threading
from types import SimpleNamespace

import bpy

from .processor import process_video
from .blender_importer import import_ply_to_blender
from .flow_video import generate_flow_video


# Shared state for the background thread (accessible by both generate and preview)
_state = {
    "thread": None,
    "cancel_event": None,
    "progress": {},
    "timer": None,
}


def _make_temp_ply():
    fd, path = tempfile.mkstemp(suffix=".ply")
    os.close(fd)
    return path


def _build_params_full(props):
    """Build processing parameters from the PropertyGroup."""
    return SimpleNamespace(
        video=bpy.path.abspath(props.video_file),
        output=bpy.path.abspath(props.output_ply)
        if props.output_ply
        else _make_temp_ply(),
        method=props.method.lower(),
        start_frame=props.start_frame,
        end_frame=props.end_frame,
        skip_frames=props.skip_frames,
        skip_pixels=props.skip_pixels,
        flow_threshold=props.flow_threshold,
        max_speed_clip=props.max_speed_clip,
        brightness_min=props.brightness_min,
        brightness_max=props.brightness_max,
        diff_threshold=props.diff_threshold,
        algorithm=props.algorithm.lower(),
        pyr_scale=props.pyr_scale,
        levels=props.levels,
        winsize=props.winsize,
        iterations=props.iterations,
        poly_n=int(props.poly_n),
        poly_sigma=props.poly_sigma,
        resize_percent=props.resize_percent,
        max_points=props.max_points,
        point_distance=props.point_distance,
        layer_distance=props.layer_distance,
    )


def _build_params_preview(props):
    """Build preview parameters (aggressive sampling, DIS for optical flow)."""
    params = _build_params_full(props)
    params.skip_frames = props.skip_frames * 10
    params.skip_pixels = props.skip_pixels * 5
    params.output = _make_temp_ply()
    if params.method == "optical_flow":
        params.algorithm = "dis"
        params.resize_percent = 50
    return params


def _run_in_thread(params):
    """Run process_video in background thread."""
    progress = _state["progress"]
    cancel = _state["cancel_event"]

    def callback(current, total, message):
        progress["current"] = current
        progress["total"] = total
        progress["message"] = message

    try:
        result = process_video(params, progress_callback=callback, cancel_event=cancel)
        progress["output_path"] = result
    except Exception as e:
        progress["error"] = str(e)
    finally:
        progress["done"] = True


def _start_processing(operator, context, params):
    """Common logic to start background processing and modal timer."""
    props = context.scene.optflow

    _state["cancel_event"] = threading.Event()
    _state["progress"] = {
        "done": False,
        "error": None,
        "message": "Starting...",
        "current": 0,
        "total": 0,
        "output_path": None,
    }

    props.is_processing = True
    props.progress_text = "Starting..."

    _state["thread"] = threading.Thread(
        target=_run_in_thread,
        args=(params,),
        daemon=True,
    )
    _state["thread"].start()

    wm = context.window_manager
    _state["timer"] = wm.event_timer_add(0.1, window=context.window)
    wm.modal_handler_add(operator)
    return {"RUNNING_MODAL"}


def _modal_handler(operator, context, event):
    """Common modal logic for generate/preview operators."""
    if event.type != "TIMER":
        return {"PASS_THROUGH"}

    progress = _state["progress"]
    props = context.scene.optflow

    props.progress_text = progress.get("message", "")

    for area in context.screen.areas:
        if area.type == "VIEW_3D":
            area.tag_redraw()

    if not progress["done"]:
        return {"PASS_THROUGH"}

    # Processing finished — clean up
    wm = context.window_manager
    wm.event_timer_remove(_state["timer"])
    _state["timer"] = None
    props.is_processing = False

    if progress["error"]:
        props.progress_text = f"Error: {progress['error']}"
        operator.report({"ERROR"}, progress["error"])
        return {"CANCELLED"}

    output_path = progress.get("output_path")
    if output_path is None:
        props.progress_text = "Cancelled or no points generated."
        operator.report({"WARNING"}, "No output generated")
        return {"CANCELLED"}

    try:
        obj = import_ply_to_blender(output_path)
        props.progress_text = f"Done — {obj.name} imported."
        operator.report({"INFO"}, f"Point cloud imported: {obj.name}")
    except Exception as e:
        props.progress_text = f"Import error: {e}"
        operator.report({"ERROR"}, f"PLY import failed: {e}")
        return {"CANCELLED"}

    return {"FINISHED"}


def _cancel_handler(context):
    """Common cancel logic."""
    if _state["timer"] is not None:
        context.window_manager.event_timer_remove(_state["timer"])
        _state["timer"] = None
    if _state["cancel_event"] is not None:
        _state["cancel_event"].set()
    context.scene.optflow.is_processing = False


def _run_flow_video_in_thread(params):
    """Run generate_flow_video in background thread."""
    progress = _state["progress"]
    cancel = _state["cancel_event"]

    def callback(current, total, message):
        progress["current"] = current
        progress["total"] = total
        progress["message"] = message

    try:
        result = generate_flow_video(
            params, progress_callback=callback, cancel_event=cancel
        )
        progress["output_path"] = result
    except Exception as e:
        progress["error"] = str(e)
    finally:
        progress["done"] = True


def _start_flow_video_processing(operator, context, params):
    """Start background flow video processing with modal timer."""
    props = context.scene.optflow

    _state["cancel_event"] = threading.Event()
    _state["progress"] = {
        "done": False,
        "error": None,
        "message": "Starting...",
        "current": 0,
        "total": 0,
        "output_path": None,
    }

    props.is_processing = True
    props.progress_text = "Starting..."

    _state["thread"] = threading.Thread(
        target=_run_flow_video_in_thread,
        args=(params,),
        daemon=True,
    )
    _state["thread"].start()

    wm = context.window_manager
    _state["timer"] = wm.event_timer_add(0.1, window=context.window)
    wm.modal_handler_add(operator)
    return {"RUNNING_MODAL"}


def _flow_video_modal_handler(operator, context, event):
    """Modal logic for flow video operator (no PLY import)."""
    if event.type != "TIMER":
        return {"PASS_THROUGH"}

    progress = _state["progress"]
    props = context.scene.optflow

    props.progress_text = progress.get("message", "")

    for area in context.screen.areas:
        if area.type == "VIEW_3D":
            area.tag_redraw()

    if not progress["done"]:
        return {"PASS_THROUGH"}

    # Processing finished — clean up
    wm = context.window_manager
    wm.event_timer_remove(_state["timer"])
    _state["timer"] = None
    props.is_processing = False

    if progress["error"]:
        props.progress_text = f"Error: {progress['error']}"
        operator.report({"ERROR"}, progress["error"])
        return {"CANCELLED"}

    output_path = progress.get("output_path")
    if output_path is None:
        props.progress_text = "Cancelled."
        operator.report({"WARNING"}, "Cancelled")
        return {"CANCELLED"}

    props.progress_text = f"Done — {output_path}"
    operator.report({"INFO"}, f"Flow video saved: {output_path}")
    return {"FINISHED"}


class ARBORTOOLS_OT_generate(bpy.types.Operator):
    """Generate a point cloud from video using optical flow"""

    bl_idname = "arbortools.generate"
    bl_label = "Generate Full"
    bl_options = {"REGISTER"}

    def invoke(self, context, event):
        return self.execute(context)

    def execute(self, context):
        props = context.scene.optflow

        if not props.video_file:
            self.report({"ERROR"}, "No video file selected")
            return {"CANCELLED"}

        video_path = bpy.path.abspath(props.video_file)
        if not video_path:
            self.report({"ERROR"}, "Invalid video file path")
            return {"CANCELLED"}

        try:
            params = _build_params_full(props)
        except Exception as e:
            self.report({"ERROR"}, f"Parameter error: {e}")
            return {"CANCELLED"}

        return _start_processing(self, context, params)

    def modal(self, context, event):
        return _modal_handler(self, context, event)

    def cancel(self, context):
        _cancel_handler(context)


class ARBORTOOLS_OT_preview(bpy.types.Operator):
    """Quick preview with DIS algorithm and aggressive sampling"""

    bl_idname = "arbortools.preview"
    bl_label = "Preview"
    bl_options = {"REGISTER"}

    def invoke(self, context, event):
        return self.execute(context)

    def execute(self, context):
        props = context.scene.optflow

        if not props.video_file:
            self.report({"ERROR"}, "No video file selected")
            return {"CANCELLED"}

        video_path = bpy.path.abspath(props.video_file)
        if not video_path:
            self.report({"ERROR"}, "Invalid video file path")
            return {"CANCELLED"}

        try:
            params = _build_params_preview(props)
        except Exception as e:
            self.report({"ERROR"}, f"Parameter error: {e}")
            return {"CANCELLED"}

        return _start_processing(self, context, params)

    def modal(self, context, event):
        return _modal_handler(self, context, event)

    def cancel(self, context):
        _cancel_handler(context)


class ARBORTOOLS_OT_browse_video(bpy.types.Operator):
    """Browse for a video file"""

    bl_idname = "arbortools.browse_video"
    bl_label = "Browse Video"

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(
        default="*.mp4;*.mov;*.avi;*.mkv;*.webm;*.flv;*.wmv",
        options={"HIDDEN"},
    )

    def execute(self, context):
        context.scene.optflow.video_file = self.filepath
        return {"FINISHED"}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}


class ARBORTOOLS_OT_browse_output(bpy.types.Operator):
    """Browse for output PLY file"""

    bl_idname = "arbortools.browse_output"
    bl_label = "Browse Output"

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(
        default="*.ply",
        options={"HIDDEN"},
    )

    def execute(self, context):
        context.scene.optflow.output_ply = self.filepath
        return {"FINISHED"}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}


class ARBORTOOLS_OT_generate_flow_video(bpy.types.Operator):
    """Generate an optical flow visualization video"""

    bl_idname = "arbortools.generate_flow_video"
    bl_label = "Generate Flow Video"
    bl_options = {"REGISTER"}

    def invoke(self, context, event):
        return self.execute(context)

    def execute(self, context):
        props = context.scene.optflow

        if not props.video_file:
            self.report({"ERROR"}, "No video file selected")
            return {"CANCELLED"}

        video_path = bpy.path.abspath(props.video_file)
        if not video_path:
            self.report({"ERROR"}, "Invalid video file path")
            return {"CANCELLED"}

        output = bpy.path.abspath(props.output_video) if props.output_video else ""
        if not output:
            self.report({"ERROR"}, "No output video path specified")
            return {"CANCELLED"}

        export_grid = props.grid_size if props.export_grid else None

        params = SimpleNamespace(
            video=video_path,
            output=output,
            algorithm=props.algorithm.lower(),
            resize_percent=props.resize_percent,
            max_speed_clip=props.max_speed_clip,
            start_frame=props.start_frame,
            end_frame=props.end_frame,
            skip_frames=props.skip_frames,
            export_grid=export_grid,
            grid_numbers=props.grid_numbers,
            pyr_scale=props.pyr_scale,
            levels=props.levels,
            winsize=props.winsize,
            iterations=props.iterations,
            poly_n=int(props.poly_n),
            poly_sigma=props.poly_sigma,
        )

        return _start_flow_video_processing(self, context, params)

    def modal(self, context, event):
        return _flow_video_modal_handler(self, context, event)

    def cancel(self, context):
        _cancel_handler(context)


class ARBORTOOLS_OT_browse_output_video(bpy.types.Operator):
    """Browse for output video file"""

    bl_idname = "arbortools.browse_output_video"
    bl_label = "Browse Output Video"

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(
        default="*.mp4;*.mov;*.avi",
        options={"HIDDEN"},
    )

    def execute(self, context):
        context.scene.optflow.output_video = self.filepath
        return {"FINISHED"}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}


class ARBORTOOLS_OT_cancel(bpy.types.Operator):
    """Cancel the running point cloud generation"""

    bl_idname = "arbortools.cancel"
    bl_label = "Cancel"

    def execute(self, context):
        if _state["cancel_event"] is not None:
            _state["cancel_event"].set()
        self.report({"INFO"}, "Cancelling...")
        return {"FINISHED"}


classes = (
    ARBORTOOLS_OT_generate,
    ARBORTOOLS_OT_preview,
    ARBORTOOLS_OT_generate_flow_video,
    ARBORTOOLS_OT_cancel,
    ARBORTOOLS_OT_browse_video,
    ARBORTOOLS_OT_browse_output,
    ARBORTOOLS_OT_browse_output_video,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
