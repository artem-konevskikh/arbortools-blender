# ArborTools — Blender Add-on

A set of tools used to produce 3D point clouds for [Arbor](https://arbor.art).

Generate a 3D point cloud from a video file using one of three methods:
**Optical Flow**, **Frame Stacking**, or **Frame Difference** — or render an
**Optical Flow Video** that visualizes motion as color.
Each layer of the cloud corresponds to a frame (or frame pair); each point carries
3D coordinates, color, and per-vertex attributes.
All attributes are available in Geometry Nodes via the **Named Attribute** node.

> **Minimum Blender version: 3.5**

## Installation

1. Download or clone this repository.
2. In Blender: **Edit → Preferences → Add-ons → Install from Disk…**
3. Select a `.zip` of the repository folder (the add-on's root contains `__init__.py`).
4. Enable **ArborTools** in the add-ons list.
5. If OpenCV is not installed, the add-on will show an **Install Dependencies** button in the N-panel — click it and restart Blender.

## Usage

1. Open the **N-panel** in the 3D Viewport (`N` key).
2. Switch to the **ArborTools** tab.
3. Set a **Video File** (`.mp4`, `.mov`, `.avi`).
4. Optionally set an **Output PLY** path (a temp file is used if left empty).
   For **Optical Flow Video**, an **Output Video** path is required.
5. Choose a **Method** (Optical Flow, Frame Stacking, or Frame Difference).
6. Adjust parameters as needed (see below).
7. Click **Preview** for a quick evaluation or **Generate Full** for final output
   (**Generate Flow Video** for the Optical Flow Video method).
8. The resulting point cloud is automatically imported into the scene.

## Methods

### Optical Flow

Generates points from motion between consecutive frames. Each point carries
normalized speed, direction angle, and raw flow displacement. Color is averaged
from the frame pair. Only pixels between `Brightness Min` and `Brightness Max`
are kept (or see [Density Mode](#density-mode)).

### Frame Stacking

Each sampled frame becomes a flat layer of colored points. Only pixels between
`Brightness Min` and `Brightness Max` are kept (or see
[Density Mode](#density-mode)). Color is taken directly from the frame.

### Frame Difference

Points are generated where consecutive frames differ. The absolute difference
magnitude is used as per-pixel Z-depth within each layer — stronger differences
sit higher. Only pixels with difference above `Diff Threshold` are kept. Color
is taken from the second frame.

### Density Mode

An option for all three point cloud methods above. Instead of a hard brightness
cut, each pixel becomes a point with a chance based on how dark it is: pixels at
or below `Brightness Min` always become points, pixels at or above `Brightness
Max` never do, and the chance falls linearly in between (with Min 0 and Max 255:
black = every pixel, 50% gray = about half, white = none). `Density Gamma` bends
the ramp: above 1 thins the mid-grays, below 1 fills them in. The random pick
uses a fixed seed, so the same input always gives the same cloud. Set
`Skip Pixels` to 1 for the full effect.

`Jitter` (works with or without Density Mode) shifts each point by up to half a
pixel in X and Y to hide the pixel grid. Z is not jittered.

### Optical Flow Video

Generates an HSV-visualized flow video from optical flow computation between
consecutive frames. Hue encodes motion direction; brightness encodes speed on a
fixed scale (`0` → black, `Max Speed Clip` and above → full brightness), so
brightness is comparable across frames. Uses the Optical Flow algorithm
settings, Frame Range, Skip Frames and Resize for Flow. Optionally saves a PNG
grid of flow frames next to the video (see **Flow Video** below).

## Parameters

### Input

| Parameter | Description |
| --- | --- |
| Video File | Path to the input video |
| Output PLY | Path for the output `.ply` file (optional; point cloud methods) |
| Output Video | Path for the output `.mp4` (required; Optical Flow Video only) |

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
| Skip Pixels | 2 | Sample every N-th pixel (point cloud methods) |

### Filtering

Parameters shown depend on the selected method.

| Parameter | Default | Methods | Description |
| --- | --- | --- | --- |
| Flow Threshold | 0.01 | Optical Flow | Minimum normalized speed to keep a point (0.0–1.0) |
| Max Speed Clip | 50.0 | Optical Flow, Flow Video | Upper bound for speed normalization (px/frame) |
| Diff Threshold | 10.0 | Frame Difference | Minimum pixel difference magnitude (0–255) |
| Brightness Min | 0 | Point cloud methods | Minimum pixel brightness (0–255) |
| Brightness Max | 127 | Point cloud methods | Binary threshold — pixels above this value are discarded |
| Density Mode | off | Point cloud methods | Replaces the hard brightness cut with a ramp: pixels at/below Brightness Min always become points, at/above Brightness Max never, in between with chance proportional to darkness (random, fixed seed). Use Skip Pixels 1 and Brightness Max 255 for the full effect |
| Density Gamma | 1.0 | Density Mode | Bends the ramp: >1 thins midtones, <1 fills them |
| Jitter | off | Point cloud methods | Random sub-pixel XY offset to hide the pixel grid |

### Optical Flow (only visible for Optical Flow and Optical Flow Video)

| Parameter | Default | Description |
| --- | --- | --- |
| Algorithm | Farneback | `Farneback` (quality) or `DIS` (fast preview) |
| Pyramid Scale | 0.5 | Farneback pyramid scale (0.1–0.9) |
| Levels | 3 | Farneback pyramid levels (1–8) |
| Window Size | 15 | Farneback window size (5–50) |
| Iterations | 3 | Farneback iterations (1–10) |
| Poly N | 5 | Farneback polynomial size (5 or 7) |
| Poly Sigma | 1.2 | Farneback polynomial sigma (1.0–2.0) |

### Processing

| Parameter | Default | Methods | Description |
| --- | --- | --- | --- |
| Resize for Flow | 50% | Optical Flow, Flow Video | Downscale factor before computing optical flow |
| Max Points | 15,000,000 | Point cloud methods | Hard limit on total point count |

### Scale

| Parameter | Default | Description |
| --- | --- | --- |
| Point Distance | 0.01 | Distance between points within a layer (XY scale) |
| Layer Distance | 0.01 | Distance between layers along the Z axis |

### Flow Video (only visible for Optical Flow Video)

| Parameter | Default | Description |
| --- | --- | --- |
| Export Grid | Off | Also save a PNG grid of flow frames (same name as the video) |
| Grid Size | 10x10 | Grid dimensions as `COLSxROWS`; frames are picked evenly if there are more than cells |
| Show Frame Numbers | Off | Draw the source frame number in each grid cell |

## Buttons

| Button | Description |
| --- | --- |
| **Preview** | Quick preview with aggressive sampling (Skip Frames x10, Skip Pixels x5; DIS + Resize 50% for Optical Flow) |
| **Generate Full** | Full processing with the selected method and all parameters |
| **Generate Flow Video** | Render the flow video (Optical Flow Video method) |
| **Cancel** | Stop the background thread (partial point cloud results are not saved) |

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

`processor.py` (with `ply_writer.py`) and `flow_video.py` run outside Blender for
batch processing (requires `opencv-python` and `numpy`). CLI defaults match the add-on.

```bash
# Optical Flow (default)
python processor.py --video input.mp4 --output output.ply --skip-frames 5 --skip-pixels 3

# Frame Stacking
python processor.py --video input.mp4 --output output.ply --method frame_stacking --skip-frames 5 --skip-pixels 3

# Frame Difference
python processor.py --video input.mp4 --output output.ply --method frame_difference --skip-frames 5 --skip-pixels 3 --diff-threshold 10

# Frame Stacking with darkness-driven density
python processor.py --video input.mp4 --output output.ply --method frame_stacking --skip-pixels 1 --brightness-max 255 --density-mode --density-gamma 1.5 --jitter

# Optical Flow Video (+ optional 10x10 PNG grid with frame numbers)
python flow_video.py --video input.mp4 --output flow.mp4 --export-grid 10x10 --num
```

Run `python processor.py --help` or `python flow_video.py --help` for all available options.

## File Structure

```bash
arbortools-blender/
├── __init__.py          # bl_info, registration, dependency check
├── operators.py         # Generate, Preview, Flow Video, Cancel, file browsers
├── panels.py            # N-panel UI (main panel + dependency panel)
├── properties.py        # PropertyGroup with all parameters
├── defaults.py          # Default values shared by add-on and CLIs (no bpy)
├── processor.py         # Video processing pipeline (no bpy)
├── ply_writer.py        # Binary PLY writer (no bpy)
├── flow_video.py        # Optical flow visualization video (no bpy)
└── blender_importer.py  # PLY import into Blender scene
```

## Performance Tips

- **4K video**: set Resize for Flow to 25-50% for significant speedup with negligible quality loss.
- **Dense videos**: increase Skip Pixels to 3-5 to reduce point count by 9-25x.
- **Quick iteration**: use Preview to evaluate parameters before running a full generation.
- **Frame Stacking / Frame Difference**: these methods are much faster than Optical Flow since they skip flow computation entirely.
- Blender is stable up to ~20M points with 16+ GB RAM.
