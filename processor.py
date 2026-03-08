"""Standalone video → point-cloud processor (no bpy imports)."""

import argparse
import sys
import os

import cv2
import numpy as np

# Allow running as both `python -m optflow_pointcloud.processor` and `python processor.py`
try:
    from .ply_writer import write_ply
except ImportError:
    sys.path.insert(0, os.path.dirname(__file__))
    from ply_writer import write_ply


class VideoOpenError(Exception):
    """Raised when the video file cannot be opened."""


def _process_optical_flow_pair(prev_frame, frame, params, scale):
    """Compute optical flow between two frames and collect points.

    Returns (points, colors, attrs, frame_indices) or None.
    """
    # 1. Resize for flow computation
    small_prev = cv2.resize(prev_frame, (0, 0), fx=scale, fy=scale)
    small_curr = cv2.resize(frame, (0, 0), fx=scale, fy=scale)

    # 2. Optical flow
    prev_gray = cv2.cvtColor(small_prev, cv2.COLOR_BGR2GRAY)
    curr_gray = cv2.cvtColor(small_curr, cv2.COLOR_BGR2GRAY)

    if params.algorithm == "farneback":
        flow = cv2.calcOpticalFlowFarneback(  # ty: ignore[no-matching-overload]
            prev_gray,
            curr_gray,
            None,
            params.pyr_scale,
            params.levels,
            params.winsize,
            params.iterations,
            params.poly_n,
            params.poly_sigma,
            0,
        )
    else:  # dis
        dis = cv2.DISOpticalFlow.create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
        flow = dis.calc(prev_gray, curr_gray, None)  # ty: ignore[no-matching-overload]

    # 3. Scale flow back to original resolution
    h, w = frame.shape[:2]
    flow = cv2.resize(flow, (w, h)) / scale

    # 4. Speed and angle
    flow_x = flow[..., 0]
    flow_y = flow[..., 1]
    speed_raw = np.sqrt(flow_x**2 + flow_y**2)
    speed_norm = np.clip(speed_raw / params.max_speed_clip, 0.0, 1.0)
    angle_deg = (np.degrees(np.arctan2(flow_y, flow_x)) + 360) % 360

    # 5. Averaged color
    avg_color = ((prev_frame.astype(np.float32) + frame.astype(np.float32)) / 2).astype(
        np.uint8
    )

    # 6. Build mask — binary threshold discards bright pixels (same as stacking/diff)
    gray = cv2.cvtColor(avg_color, cv2.COLOR_BGR2GRAY)
    _, th = cv2.threshold(gray, params.brightness_max, 255, cv2.THRESH_BINARY)
    bright_mask = th == 0  # pixels below brightness_max pass
    mask = (
        (speed_norm >= params.flow_threshold)
        & bright_mask
        & (gray >= params.brightness_min)
    )
    pixel_mask = np.zeros(frame.shape[:2], dtype=bool)
    pixel_mask[:: params.skip_pixels, :: params.skip_pixels] = True
    mask = mask & pixel_mask

    # 7. Collect points
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return None

    colors = avg_color[ys, xs][:, ::-1]  # BGR → RGB
    attrs = np.column_stack(
        [
            speed_norm[ys, xs],
            angle_deg[ys, xs],
            flow_x[ys, xs],
            flow_y[ys, xs],
        ]
    ).astype(np.float32)

    return xs, ys, colors, attrs


def _process_frame_stacking(frame, params):
    """Convert a single frame into a point layer using brightness thresholding.

    Approach from the original img2points script: pixels below brightness_max
    are kept (binary threshold), and depth = 1 - th/255 gives per-pixel Z
    offset within the layer.

    Returns (xs, ys, colors, attrs, depth) or None.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    _, th = cv2.threshold(gray, params.brightness_max, 255, cv2.THRESH_BINARY)
    depth = 1.0 - th.astype(np.float32) / 255.0

    # Mask: valid depth (dark pixels pass) AND above brightness_min
    mask = (depth > 0) & (gray >= params.brightness_min)

    # Pixel sampling
    pixel_mask = np.zeros(frame.shape[:2], dtype=bool)
    pixel_mask[:: params.skip_pixels, :: params.skip_pixels] = True
    mask = mask & pixel_mask

    ys, xs = np.where(mask)
    if len(xs) == 0:
        return None

    colors = frame[ys, xs][:, ::-1]  # BGR → RGB
    point_depth = depth[ys, xs]
    attrs = np.zeros(
        (len(xs), 4), dtype=np.float32
    )  # speed=0, angle=0, flow_x=0, flow_y=0

    return xs, ys, colors, attrs, point_depth


def _process_frame_difference_pair(prev_frame, frame, params):
    """Compute absolute frame difference and collect points where change exceeds threshold.

    Uses diff magnitude as per-pixel Z-depth within each layer (approach from
    the original diff2points script): depth = 1 - inverted_diff / 255, so
    stronger differences sit higher in Z.

    Returns (xs, ys, colors, attrs, depth) or None.
    """
    diff_threshold = getattr(params, "diff_threshold", 10.0)

    # Threshold both frames to grayscale, then compute diff (matches old img2th + absdiff)
    gray_prev = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    gray_curr = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    diff_bw = cv2.absdiff(gray_prev, gray_curr)

    # depth = 1 - bitwise_not(diff) / 255  ==  diff / 255
    depth = diff_bw.astype(np.float32) / 255.0

    # Build mask: difference above threshold
    mask = diff_bw >= diff_threshold

    # Brightness filter on grayscale of second frame (color source)
    _, th = cv2.threshold(gray_curr, params.brightness_max, 255, cv2.THRESH_BINARY)
    mask = mask & (th == 0) & (gray_curr >= params.brightness_min)

    # Pixel sampling
    pixel_mask = np.zeros(frame.shape[:2], dtype=bool)
    pixel_mask[:: params.skip_pixels, :: params.skip_pixels] = True
    mask = mask & pixel_mask

    ys, xs = np.where(mask)
    if len(xs) == 0:
        return None

    # Color from second frame (like the old script: color_points = img2)
    colors = frame[ys, xs][:, ::-1]  # BGR → RGB
    point_depth = depth[ys, xs]

    attrs = np.column_stack(
        [
            point_depth,  # normalized diff magnitude → speed attribute
            np.zeros(len(xs), dtype=np.float32),  # angle=0
            np.zeros(len(xs), dtype=np.float32),  # flow_x=0
            np.zeros(len(xs), dtype=np.float32),  # flow_y=0
        ]
    ).astype(np.float32)

    return xs, ys, colors, attrs, point_depth


def process_video(params, progress_callback=None, cancel_event=None):
    """Run the processing pipeline and write a PLY file.

    Parameters
    ----------
    params : namespace
        Processing parameters (video, output, method, etc.).
    progress_callback : callable, optional
        Called as progress_callback(current_frame, total_frames, message).
    cancel_event : threading.Event, optional
        If set, processing stops at the next iteration.

    Returns
    -------
    str or None
        Output path on success, None if cancelled or no points.
    """

    def _report(current, total, msg):
        if progress_callback is not None:
            progress_callback(current, total, msg)
        else:
            print(msg)

    method = getattr(params, "method", "optical_flow")

    cap = cv2.VideoCapture(params.video)
    if not cap.isOpened():
        raise VideoOpenError(f"Cannot open video '{params.video}'")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    start = params.start_frame if params.start_frame > 0 else 0
    end = params.end_frame if params.end_frame > 0 else total_frames
    cap.set(cv2.CAP_PROP_POS_FRAMES, start)

    _report(0, total_frames, f"Video: {params.video}")
    _report(
        0,
        total_frames,
        f"Total frames: {total_frames}, processing range [{start}, {end})",
    )
    _report(0, total_frames, f"Method: {method}")
    if method == "optical_flow":
        scale = params.resize_percent / 100.0
        _report(
            0,
            total_frames,
            f"Algorithm: {params.algorithm}, resize: {params.resize_percent}%",
        )
    else:
        scale = 1.0

    all_points = []
    all_colors = []
    all_attrs = []
    all_frames = []
    total_point_count = 0

    prev_frame = None
    layer_idx = 0

    frames_to_process = len(range(start, end, params.skip_frames))

    for i in range(start, end):
        if cancel_event is not None and cancel_event.is_set():
            cap.release()
            return None
        ret, frame = cap.read()
        if not ret:
            break
        if (i - start) % params.skip_frames != 0:
            continue

        result = None

        if method == "frame_stacking":
            # Every sampled frame becomes a layer — no prev_frame needed
            result = _process_frame_stacking(frame, params)
        else:
            # Both optical_flow and frame_difference need frame pairs
            if prev_frame is None:
                prev_frame = frame
                continue
            if method == "optical_flow":
                result = _process_optical_flow_pair(prev_frame, frame, params, scale)
            else:  # frame_difference
                result = _process_frame_difference_pair(prev_frame, frame, params)
            prev_frame = frame

        if result is None:
            layer_idx += 1
            continue

        # Frame stacking and frame difference return an extra depth array
        if method in ("frame_difference", "frame_stacking"):
            xs, ys, colors, attrs, depth = result
        else:
            xs, ys, colors, attrs = result
            depth = None

        point_dist = getattr(params, "point_distance", 1.0)
        layer_dist = getattr(params, "layer_distance", 1.0)
        base_z = float(layer_idx) * layer_dist
        if depth is not None:
            # Per-pixel Z offset from diff magnitude (old diff2points approach)
            z = (base_z + depth * layer_dist).astype(np.float32)
        else:
            z = np.full(len(xs), base_z, dtype=np.float32)
        points = np.column_stack([xs * point_dist, ys * point_dist, z]).astype(
            np.float32
        )
        frames_arr = np.full(len(xs), i, dtype=np.int32)

        all_points.append(points)
        all_colors.append(colors)
        all_attrs.append(attrs)
        all_frames.append(frames_arr)
        total_point_count += len(xs)

        layer_idx += 1

        # Progress
        progress_pct = int((layer_idx / max(frames_to_process - 1, 1)) * 100)
        _report(
            layer_idx,
            frames_to_process,
            f"Processing frame {i} / {end} ({progress_pct}%)",
        )

        # Check point limit
        if total_point_count >= params.max_points:
            _report(
                layer_idx,
                frames_to_process,
                f"Reached max points limit ({params.max_points}), stopping.",
            )
            break

    cap.release()

    if not all_points:
        _report(0, 0, "No points collected — try adjusting parameters.")
        return None

    pts = np.concatenate(all_points)
    cols = np.concatenate(all_colors)
    attr = np.concatenate(all_attrs)
    frs = np.concatenate(all_frames)

    # Trim to max_points
    if len(pts) > params.max_points:
        pts = pts[: params.max_points]
        cols = cols[: params.max_points]
        attr = attr[: params.max_points]
        frs = frs[: params.max_points]

    _report(
        frames_to_process,
        frames_to_process,
        f"Writing {len(pts)} points to {params.output}",
    )
    write_ply(params.output, pts, cols, attr, frs)
    _report(frames_to_process, frames_to_process, "Done.")
    return params.output


def main():
    parser = argparse.ArgumentParser(description="ArborTools — video to PLY processor")
    parser.add_argument("--video", required=True, help="Input video path")
    parser.add_argument("--output", required=True, help="Output PLY path")
    parser.add_argument(
        "--method",
        choices=["optical_flow", "frame_stacking", "frame_difference"],
        default="optical_flow",
    )
    parser.add_argument("--skip-frames", type=int, default=None)
    parser.add_argument("--skip-pixels", type=int, default=None)
    parser.add_argument("--flow-threshold", type=float, default=0.01)
    parser.add_argument("--max-speed-clip", type=float, default=50.0)
    parser.add_argument("--brightness-min", type=int, default=0)
    parser.add_argument("--brightness-max", type=int, default=127)
    parser.add_argument("--diff-threshold", type=float, default=10.0)
    parser.add_argument(
        "--algorithm", choices=["farneback", "dis"], default="farneback"
    )
    parser.add_argument("--resize-percent", type=int, default=None)
    parser.add_argument("--max-points", type=int, default=15_000_000)
    parser.add_argument("--start-frame", type=int, default=0)
    parser.add_argument("--end-frame", type=int, default=0)
    # Farneback parameters
    parser.add_argument("--pyr-scale", type=float, default=0.5)
    parser.add_argument("--levels", type=int, default=5)
    parser.add_argument("--winsize", type=int, default=21)
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--poly-n", type=int, default=7)
    parser.add_argument("--poly-sigma", type=float, default=1.5)
    parser.add_argument("--point-distance", type=float, default=0.01)
    parser.add_argument("--layer-distance", type=float, default=0.01)

    args = parser.parse_args()

    # Apply algorithm-specific defaults for params not explicitly provided
    if args.method == "optical_flow":
        if args.algorithm == "dis":
            if args.skip_frames is None:
                args.skip_frames = 10
            if args.skip_pixels is None:
                args.skip_pixels = 5
            if args.resize_percent is None:
                args.resize_percent = 25
        else:  # farneback
            if args.skip_frames is None:
                args.skip_frames = 5
            if args.skip_pixels is None:
                args.skip_pixels = 2
            if args.resize_percent is None:
                args.resize_percent = 75
    else:
        # frame_stacking / frame_difference — simpler defaults
        if args.skip_frames is None:
            args.skip_frames = 5
        if args.skip_pixels is None:
            args.skip_pixels = 2
        if args.resize_percent is None:
            args.resize_percent = 100

    try:
        process_video(args)
    except VideoOpenError as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
