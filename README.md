# ArborTools — Blender Add-on

A set of tools used to produce 3D point clouds for [Arbor](https://arbor.art).

Generate a 3D point cloud from a video file using one of three methods:
**Optical Flow**, **Frame Stacking**, or **Frame Difference**.
Each layer of the cloud corresponds to a frame (or frame pair); each point carries
3D coordinates, color, and per-vertex attributes.
All attributes are available in Geometry Nodes via the **Named Attribute** node.

> **Minimum Blender version: 3.5**

## Installation

1. Download or clone this repository.
2. In Blender: **Edit → Preferences → Add-ons → Install from Disk…**
3. Select the `optflow_pointcloud/` folder (or a `.zip` of it).
4. Enable **ArborTools** in the add-ons list.
5. If OpenCV is not installed, the add-on will show an **Install Dependencies** button in the N-panel — click it and restart Blender.

## Usage

1. Open the **N-panel** in the 3D Viewport (`N` key).
2. Switch to the **ArborTools** tab.
3. Set a **Video File** (`.mp4`, `.mov`, `.avi`).
4. Optionally set an **Output PLY** path (a temp file is used if left empty).
5. Choose a **Method** (Optical Flow, Frame Stacking, or Frame Difference).
6. Adjust parameters as needed (see below).
7. Click **Preview** for a quick evaluation or **Generate Full** for final output.
8. The resulting point cloud is automatically imported into the scene.

## Methods

### Optical Flow

Generates points from motion between consecutive frames. Each point carries
normalized speed, direction angle, and raw flow displacement. Color is averaged
from the frame pair. Pixels above `Brightness Max` are discarded via binary
threshold; `Brightness Min` sets the lower bound.

### Frame Stacking

Each sampled frame becomes a flat layer of colored points. A binary brightness
threshold (`Brightness Max`) discards bright pixels; dark pixels that pass get a
per-pixel Z offset within the layer (`depth = 1 - threshold_result / 255`).
Color is taken directly from the frame.

### Frame Difference

Points are generated where consecutive frames differ. The absolute difference
magnitude is used as per-pixel Z-depth within each layer — stronger differences
sit higher. Only pixels with difference above `Diff Threshold` are kept. Color
is taken from the second frame.

### Optical Flow Video

Generates an HSV-visualized flow video from optical flow computation between
consecutive frames. Creates a video output where motion is visualized using
color (hue) for direction and intensity (value) for magnitude.

## Parameters

### Input

| Parameter | Description |
| --- | --- |
| Video File | Path to the input video |
| Output PLY | Path for the output `.ply` file (optional) |

### Method

| Value | Description |
| --- | --- |
| Optical Flow | Points from motion between frames (default) |
| Frame Stacking | Each frame becomes a layer of colored points |
| Frame Difference | Points where consecutive frames differ |
| Optical Flow Video | HSV-visualized flow video output |

### Frame Range

| Parameter | Default | Description |
| --- | --- | --- |
| Start Frame | 0 | First frame to process (0 = beginning) |
| End Frame | 0 | Last frame to process (0 = end of video) |

### Sampling

| Parameter | Default | Description |
| --- | --- | --- |
| Skip Frames | 5 | Process every N-th frame |
| Skip Pixels | 2 | Sample every N-th pixel |

### Filtering

Parameters shown depend on the selected method.

| Parameter | Default | Methods | Description |
| --- | --- | --- | --- |
| Flow Threshold | 0.01 | Optical Flow | Minimum normalized speed to keep a point (0.0–1.0) |
| Max Speed Clip | 50.0 | Optical Flow | Upper bound for speed normalization (px/frame) |
| Diff Threshold | 10.0 | Frame Difference | Minimum pixel difference magnitude (0–255) |
| Brightness Min | 0 | All | Minimum pixel brightness (0–255) |
| Brightness Max | 255 | All | Binary threshold — pixels above this value are discarded |

### Optical Flow (only visible when method is Optical Flow)

| Parameter | Default | Description |
| --- | --- | --- |
| Algorithm | Farneback | `Farneback` (quality) or `DIS` (fast preview) |
| Pyramid Scale | 0.5 | Farneback pyramid scale (0.1–0.9) |
| Levels | 3 | Farneback pyramid levels (1–8) |
| Winsize | 15 | Farneback window size (5–50) |
| Iterations | 3 | Farneback iterations (1–10) |
| Poly N | 5 | Farneback polynomial size (5 or 7) |
| Poly Sigma | 1.2 | Farneback polynomial sigma (1.0–2.0) |

### Processing

| Parameter | Default | Methods | Description |
| --- | --- | --- | --- |
| Resize for Flow | 50% | Optical Flow | Downscale factor before computing optical flow |
| Max Points | 15,000,000 | All | Hard limit on total point count |

### Scale

| Parameter | Default | Description |
| --- | --- | --- |
| Point Distance | 1.0 | Distance between points within a layer (XY scale) |
| Layer Distance | 1.0 | Distance between layers along the Z axis |

## Buttons

| Button | Description |
| --- | --- |
| **Preview** | Quick preview with aggressive sampling (Skip Frames x10, Skip Pixels x5; DIS + Resize 50% for Optical Flow) |
| **Generate Full** | Full processing with the selected method and all parameters |
| **Cancel** | Stop the background thread (partial results are not saved) |

## Named Attributes in Geometry Nodes

After import, the point cloud object exposes these attributes:

| Attribute | Type | Description |
| --- | --- | --- |
| `speed` | Float | Optical Flow: normalized motion magnitude. Frame Difference: normalized diff magnitude. Frame Stacking: 0. |
| `angle` | Float | Motion direction in degrees (Optical Flow only, 0 otherwise) |
| `flow_x` | Float | Raw optical flow X displacement (Optical Flow only, 0 otherwise) |
| `flow_y` | Float | Raw optical flow Y displacement (Optical Flow only, 0 otherwise) |
| `frame_index` | Integer | Source frame index — filter layers, animate visibility over time |
| `Color` | Byte Color | Point color (auto-imported from PLY) |

## Standalone CLI

`processor.py` and `ply_writer.py` can run outside Blender for batch processing:

```bash
# Optical Flow (default)
python processor.py --video input.mp4 --output output.ply --skip-frames 5 --skip-pixels 3

# Frame Stacking
python processor.py --video input.mp4 --output output.ply --method frame_stacking --skip-frames 5 --skip-pixels 3

# Frame Difference
python processor.py --video input.mp4 --output output.ply --method frame_difference --skip-frames 5 --skip-pixels 3 --diff-threshold 10
```

Run `python processor.py --help` for all available options.

## File Structure

```bash
optflow_pointcloud/
├── __init__.py          # bl_info, registration, dependency check
├── operators.py         # Generate, Preview, Cancel, Install Dependencies
├── panels.py            # N-panel UI (main panel + dependency panel)
├── properties.py        # PropertyGroup with all parameters
├── processor.py         # Video processing pipeline (no bpy)
├── ply_writer.py        # Binary PLY writer (no bpy)
└── blender_importer.py  # PLY import into Blender scene
```

## Performance Tips

- **4K video**: set Resize for Flow to 25-50% for significant speedup with negligible quality loss.
- **Dense videos**: increase Skip Pixels to 3-5 to reduce point count by 9-25x.
- **Quick iteration**: use Preview to evaluate parameters before running a full generation.
- **Frame Stacking / Frame Difference**: these methods are much faster than Optical Flow since they skip flow computation entirely.
- Blender is stable up to ~20M points with 16+ GB RAM.
