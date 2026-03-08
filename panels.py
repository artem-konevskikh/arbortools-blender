"""ArborTools — Blender UI panels."""

import bpy


class ARBORTOOLS_PT_main_panel(bpy.types.Panel):
    """Main ArborTools panel"""

    bl_label = "ArborTools"
    bl_idname = "ARBORTOOLS_PT_main_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "ArborTools"

    def draw(self, context):
        layout = self.layout
        props = context.scene.optflow

        is_flow_video = props.method == "OPTICAL_FLOW_VIDEO"

        # --- Input (always open) ---
        box = layout.box()
        box.label(text="Input")
        row = box.row(align=True)
        row.prop(props, "video_file", text="Video")
        row.operator("arbortools.browse_video", icon="FILE_FOLDER", text="")
        if props.total_frames > 0:
            box.label(text=f"Total frames: {props.total_frames}")
        if is_flow_video:
            row = box.row(align=True)
            row.prop(props, "output_video", text="Output Video")
            row.operator("arbortools.browse_output_video", icon="FILE_FOLDER", text="")
        else:
            row = box.row(align=True)
            row.prop(props, "output_ply", text="Output PLY")
            row.operator("arbortools.browse_output", icon="FILE_FOLDER", text="")

        # --- Method ---
        layout.prop(props, "method")

        # --- Frame Range ---
        box = layout.box()
        row = box.row()
        row.prop(
            props,
            "show_frame_range",
            icon="TRIA_DOWN" if props.show_frame_range else "TRIA_RIGHT",
            emboss=False,
        )
        if props.show_frame_range:
            row = box.row(align=True)
            row.prop(props, "start_frame")
            row.prop(props, "end_frame")

        # --- Sampling ---
        box = layout.box()
        row = box.row()
        row.prop(
            props,
            "show_sampling",
            icon="TRIA_DOWN" if props.show_sampling else "TRIA_RIGHT",
            emboss=False,
        )
        if props.show_sampling:
            box.prop(props, "skip_frames")
            if not is_flow_video:
                box.prop(props, "skip_pixels")

        # --- Filtering ---
        box = layout.box()
        row = box.row()
        row.prop(
            props,
            "show_filtering",
            icon="TRIA_DOWN" if props.show_filtering else "TRIA_RIGHT",
            emboss=False,
        )
        if props.show_filtering:
            if props.method in ("OPTICAL_FLOW", "OPTICAL_FLOW_VIDEO"):
                if not is_flow_video:
                    box.prop(props, "flow_threshold")
                box.prop(props, "max_speed_clip")
            elif props.method == "FRAME_DIFFERENCE":
                box.prop(props, "diff_threshold")
            if not is_flow_video:
                row = box.row(align=True)
                row.prop(props, "brightness_min")
                row.prop(props, "brightness_max")

        # --- Optical Flow ---
        if props.method in ("OPTICAL_FLOW", "OPTICAL_FLOW_VIDEO"):
            box = layout.box()
            row = box.row()
            row.prop(
                props,
                "show_optical_flow",
                icon="TRIA_DOWN" if props.show_optical_flow else "TRIA_RIGHT",
                emboss=False,
            )
            if props.show_optical_flow:
                box.prop(props, "algorithm")
                if props.algorithm == "FARNEBACK":
                    col = box.column(align=True)
                    col.prop(props, "pyr_scale")
                    col.prop(props, "levels")
                    col.prop(props, "winsize")
                    col.prop(props, "iterations")
                    col.prop(props, "poly_n")
                    col.prop(props, "poly_sigma")

        # --- Processing ---
        box = layout.box()
        row = box.row()
        row.prop(
            props,
            "show_processing",
            icon="TRIA_DOWN" if props.show_processing else "TRIA_RIGHT",
            emboss=False,
        )
        if props.show_processing:
            if props.method in ("OPTICAL_FLOW", "OPTICAL_FLOW_VIDEO"):
                box.prop(props, "resize_percent")
            if not is_flow_video:
                box.prop(props, "max_points")

        # --- Scale (not for flow video) ---
        if not is_flow_video:
            box = layout.box()
            row = box.row()
            row.prop(
                props,
                "show_scale",
                icon="TRIA_DOWN" if props.show_scale else "TRIA_RIGHT",
                emboss=False,
            )
            if props.show_scale:
                box.prop(props, "point_distance")
                box.prop(props, "layer_distance")

        # --- Flow Video settings ---
        if is_flow_video:
            box = layout.box()
            row = box.row()
            row.prop(
                props,
                "show_flow_video",
                icon="TRIA_DOWN" if props.show_flow_video else "TRIA_RIGHT",
                emboss=False,
            )
            if props.show_flow_video:
                box.prop(props, "export_grid")
                if props.export_grid:
                    box.prop(props, "grid_size")
                    box.prop(props, "grid_numbers")

        # --- Buttons ---
        layout.separator()
        if props.is_processing:
            layout.operator("arbortools.cancel", icon="CANCEL")
            layout.label(text=props.progress_text)
        elif is_flow_video:
            layout.operator("arbortools.generate_flow_video", icon="RENDER_ANIMATION")
        else:
            row = layout.row(align=True)
            row.operator("arbortools.preview", icon="PLAY")
            row.operator("arbortools.generate", icon="RENDER_ANIMATION")


class ARBORTOOLS_PT_deps_panel(bpy.types.Panel):
    """Panel shown when OpenCV is not installed"""

    bl_label = "ArborTools"
    bl_idname = "ARBORTOOLS_PT_deps_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "ArborTools"

    def draw(self, context):
        layout = self.layout
        layout.label(text="OpenCV not found", icon="ERROR")
        layout.label(text="Required for point cloud generation.")
        layout.separator()
        layout.operator("arbortools.install_deps", icon="IMPORT")
        layout.label(text="Restart Blender after installing.")


classes_main = (ARBORTOOLS_PT_main_panel,)

classes_deps = (ARBORTOOLS_PT_deps_panel,)


def register_main():
    for cls in classes_main:
        bpy.utils.register_class(cls)


def unregister_main():
    for cls in reversed(classes_main):
        bpy.utils.unregister_class(cls)


def register_deps():
    for cls in classes_deps:
        bpy.utils.register_class(cls)


def unregister_deps():
    for cls in reversed(classes_deps):
        bpy.utils.unregister_class(cls)
