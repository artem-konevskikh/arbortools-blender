"""ArborTools — Blender add-on for generating point clouds from video."""

import ensurepip
import os
import site
import subprocess
import sys

import bpy

bl_info = {
    "name": "ArborTools",
    "author": "Artem Konevskikh",
    "version": (1, 0, 0),
    "blender": (3, 5, 0),
    "location": "View3D > Sidebar > ArborTools",
    "description": "Generate point cloud from video using optical flow",
    "category": "Import-Export",
}

_registered_full = False


def _get_python_exe():
    """Return the path to Blender's bundled Python executable."""
    # sys.executable may point to the Blender binary in some versions;
    # try to find the actual Python binary next to it.
    exe = sys.executable
    if os.path.basename(exe).lower().startswith("blender"):
        # Look for python inside the Blender bundle
        d = os.path.dirname(exe)
        for candidate in (
            # macOS .app bundle
            os.path.join(d, "..", "Resources", "lib", "python*", "bin", "python*"),
            # Linux / Windows typical layout
            os.path.join(d, "python", "bin", "python3"),
            os.path.join(d, "python", "bin", "python"),
        ):
            import glob

            matches = sorted(glob.glob(candidate))
            if matches:
                return matches[-1]
    return exe


def _get_modules_path():
    """Return (and create) the Blender user modules directory."""
    path = bpy.utils.user_resource("SCRIPTS", path="modules", create=True)
    # Make sure Blender can import from this directory
    if path not in sys.path:
        sys.path.append(path)
        site.addsitedir(path)
    return path


class ARBORTOOLS_OT_install_deps(bpy.types.Operator):
    """Install OpenCV into Blender's Python environment"""

    bl_idname = "arbortools.install_deps"
    bl_label = "Install Dependencies"

    def execute(self, context):
        python = _get_python_exe()
        modules_path = _get_modules_path()

        # Ensure pip is available in Blender's Python
        try:
            subprocess.check_call(
                [python, "-m", "pip", "--version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.report({"INFO"}, "pip not found — bootstrapping with ensurepip...")
            try:
                ensurepip.bootstrap(upgrade=True)
            except Exception as e:
                self.report({"ERROR"}, f"ensurepip failed: {e}")
                return {"CANCELLED"}

        # Install into Blender's user modules directory
        cmd = [
            python,
            "-m",
            "pip",
            "install",
            "--upgrade",
            "--target",
            modules_path,
            "opencv-python",
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode != 0:
                err = result.stderr.strip() or result.stdout.strip()
                self.report({"ERROR"}, f"pip install failed:\n{err}")
                return {"CANCELLED"}
            self.report(
                {"INFO"}, "OpenCV installed successfully. Please restart Blender."
            )
        except FileNotFoundError:
            self.report(
                {"ERROR"},
                f"Python executable not found at: {python}",
            )
            return {"CANCELLED"}
        return {"FINISHED"}


def register():
    global _registered_full

    # Ensure the user modules directory is on sys.path so previously
    # installed packages (e.g. cv2) are found after restart.
    _get_modules_path()

    try:
        import cv2  # noqa: F401
    except ImportError:
        # cv2 not available — register only the dependency installer
        bpy.utils.register_class(ARBORTOOLS_OT_install_deps)

        from . import panels

        panels.register_deps()
        _registered_full = False
        return

    from . import operators, panels, properties

    properties.register()
    operators.register()
    panels.register_main()
    _registered_full = True


def unregister():
    global _registered_full

    if _registered_full:
        from . import operators, panels, properties

        panels.unregister_main()
        operators.unregister()
        properties.unregister()
    else:
        from . import panels

        panels.unregister_deps()
        bpy.utils.unregister_class(ARBORTOOLS_OT_install_deps)

    _registered_full = False
