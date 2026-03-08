"""CLI tool: compute optical flow from a video and save as a flow-visualized video."""

import argparse
import os
import sys

import cv2
import numpy as np


def compute_flow(prev_gray, curr_gray, algorithm, fb_params):
    """Compute optical flow between two grayscale frames."""
    if algorithm == "farneback":
        return cv2.calcOpticalFlowFarneback(  # ty: ignore[no-matching-overload]
            prev_gray,
            curr_gray,
            None,
            fb_params["pyr_scale"],
            fb_params["levels"],
            fb_params["winsize"],
            fb_params["iterations"],
            fb_params["poly_n"],
            fb_params["poly_sigma"],
            0,
        )
    else:
        dis = cv2.DISOpticalFlow.create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
        return dis.calc(prev_gray, curr_gray, None)  # ty: ignore[no-matching-overload]


def build_grid(
    frames, frame_numbers, cell_w, cell_h, cols=10, rows=10, show_numbers=False
):
    """Assemble frames into a grid image.

    If there are more than cols*rows frames, pick equally spaced ones.
    If fewer, pad the remaining cells with black.
    """
    total_cells = cols * rows

    if len(frames) > total_cells:
        indices = np.linspace(0, len(frames) - 1, total_cells, dtype=int)
        selected = [frames[i] for i in indices]
        selected_numbers = [frame_numbers[i] for i in indices]
    else:
        selected = list(frames)
        selected_numbers = list(frame_numbers)

    max_num = max(selected_numbers) if selected_numbers else 0
    num_digits = max(len(str(max_num)), 1)

    grid = np.zeros((rows * cell_h, cols * cell_w, 3), dtype=np.uint8)
    for idx, frame in enumerate(selected):
        r, c = divmod(idx, cols)
        resized = cv2.resize(frame, (cell_w, cell_h))
        if show_numbers:
            label = str(selected_numbers[idx]).zfill(num_digits)
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = cell_h / 650
            thickness = max(1, int(cell_h / 650))
            (tw, th), _ = cv2.getTextSize(label, font, font_scale, thickness)
            margin = max(4, int(cell_h / 100))
            x = cell_w - tw - margin
            y = cell_h - margin
            cv2.putText(
                resized,
                label,
                (x, y),
                font,
                font_scale,
                (255, 255, 255),
                thickness,
                cv2.LINE_AA,
            )
        grid[r * cell_h : (r + 1) * cell_h, c * cell_w : (c + 1) * cell_w] = resized

    return grid


def flow_to_hsv(flow, max_speed_clip):
    """Convert optical flow to an HSV image (hue=direction, value=magnitude)."""
    mag, ang = cv2.cartToPolar(flow[..., 0], flow[..., 1])
    mag = np.clip(mag, 0, max_speed_clip)

    hsv = np.zeros((*flow.shape[:2], 3), dtype=np.uint8)
    hsv[..., 0] = (ang * 180 / np.pi / 2).astype(np.uint8)  # hue: 0-179
    hsv[..., 1] = 255  # full saturation
    hsv[..., 2] = cv2.normalize(mag, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)  # ty: ignore[no-matching-overload]
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)


def generate_flow_video(params, progress_callback=None, cancel_event=None):
    """Generate an optical flow visualization video.

    Parameters
    ----------
    params : namespace
        Processing parameters with attributes: video, output, algorithm,
        resize_percent, max_speed_clip, start_frame, end_frame, skip_frames,
        export_grid (str or None, e.g. "10x10"), grid_numbers (bool),
        pyr_scale, levels, winsize, iterations, poly_n, poly_sigma.
    progress_callback : callable, optional
        Called as progress_callback(current, total, message).
    cancel_event : threading.Event, optional
        If set, processing stops at the next iteration.

    Returns
    -------
    str or None
        Output video path on success, None if cancelled.
    """

    def _report(current, total, msg):
        if progress_callback is not None:
            progress_callback(current, total, msg)
        else:
            print(msg)

    cap = cv2.VideoCapture(params.video)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video '{params.video}'")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    start = params.start_frame if params.start_frame > 0 else 0
    end = params.end_frame if params.end_frame > 0 else total_frames

    scale = params.resize_percent / 100.0
    out_w = int(w * scale)
    out_h = int(h * scale)

    out_fps = fps / params.skip_frames

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(params.output, fourcc, out_fps, (out_w, out_h))
    if not writer.isOpened():
        raise RuntimeError(f"Cannot create output video '{params.output}'")

    fb_params = {
        "pyr_scale": params.pyr_scale,
        "levels": params.levels,
        "winsize": params.winsize,
        "iterations": params.iterations,
        "poly_n": params.poly_n,
        "poly_sigma": params.poly_sigma,
    }

    # Parse grid dimensions
    export_grid = getattr(params, "export_grid", None)
    grid_numbers = getattr(params, "grid_numbers", False)
    grid_cols, grid_rows = 0, 0
    if export_grid:
        try:
            parts = export_grid.lower().split("x")
            grid_cols, grid_rows = int(parts[0]), int(parts[1])
        except (ValueError, IndexError):
            raise RuntimeError(
                f"Invalid grid format '{export_grid}', expected COLSxROWS (e.g. 10x10)"
            )
    all_vis_frames = [] if export_grid else None
    all_frame_numbers = [] if export_grid else None

    algorithm = params.algorithm

    _report(
        0,
        total_frames,
        f"Video: {params.video} ({w}x{h}, {total_frames} frames, {fps:.1f} fps)",
    )
    _report(
        0,
        total_frames,
        f"Processing range [{start}, {end}), skip={params.skip_frames}, resize={params.resize_percent}%",
    )
    _report(0, total_frames, f"Algorithm: {algorithm}")
    _report(
        0, total_frames, f"Output: {params.output} ({out_w}x{out_h}, {out_fps:.1f} fps)"
    )

    cap.set(cv2.CAP_PROP_POS_FRAMES, start)
    prev_gray = None
    written = 0
    frames_range = end - start

    for i in range(start, end):
        if cancel_event is not None and cancel_event.is_set():
            cap.release()
            writer.release()
            return None

        ret, frame = cap.read()
        if not ret:
            break
        if (i - start) % params.skip_frames != 0:
            continue

        if scale != 1.0:
            frame = cv2.resize(frame, (out_w, out_h))

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        if prev_gray is None:
            prev_gray = gray
            continue

        flow = compute_flow(prev_gray, gray, algorithm, fb_params)
        vis = flow_to_hsv(flow, params.max_speed_clip)
        writer.write(vis)
        if all_vis_frames is not None:
            all_vis_frames.append(vis)
            all_frame_numbers.append(i)
        written += 1
        prev_gray = gray

        if written % 50 == 0 or written == 1:
            pct = int(((i - start) / max(frames_range - 1, 1)) * 100)
            _report(
                i - start,
                frames_range,
                f"Frame {i}/{end} ({pct}%) — {written} frames written",
            )

    cap.release()
    writer.release()
    _report(
        frames_range, frames_range, f"Done. Wrote {written} frames to {params.output}"
    )

    grid_path = None
    if all_vis_frames is not None and all_vis_frames:
        grid_path = os.path.splitext(params.output)[0] + ".png"
        grid = build_grid(
            all_vis_frames,
            all_frame_numbers,
            out_w,
            out_h,
            cols=grid_cols,
            rows=grid_rows,
            show_numbers=grid_numbers,
        )
        cv2.imwrite(grid_path, grid)
        _report(
            frames_range,
            frames_range,
            f"Grid saved to {grid_path} ({grid.shape[1]}x{grid.shape[0]})",
        )

    return params.output


def main():
    parser = argparse.ArgumentParser(
        description="Compute optical flow from a video and save as a visualized video"
    )
    parser.add_argument("--video", required=True, help="Input video path")
    parser.add_argument("--output", required=True, help="Output video path (.mp4)")
    parser.add_argument(
        "--algorithm",
        choices=["farneback", "dis"],
        default="farneback",
        help="Optical flow algorithm (default: farneback)",
    )
    parser.add_argument(
        "--resize-percent",
        type=int,
        default=100,
        help="Downscale frames before computing flow (default: 100)",
    )
    parser.add_argument(
        "--max-speed-clip",
        type=float,
        default=50.0,
        help="Upper bound for magnitude normalization (default: 50.0)",
    )
    parser.add_argument("--start-frame", type=int, default=0)
    parser.add_argument(
        "--end-frame",
        type=int,
        default=0,
        help="Last frame to process (0 = end of video)",
    )
    parser.add_argument(
        "--skip-frames",
        type=int,
        default=1,
        help="Process every N-th frame (default: 1)",
    )
    parser.add_argument(
        "--export-grid",
        type=str,
        default=None,
        metavar="COLSxROWS",
        help="Save a grid of flow frames as PNG, e.g. '10x10' or '5x8' (same name as output)",
    )
    parser.add_argument(
        "--num",
        action="store_true",
        help="Show frame numbers in the bottom-right corner of each grid cell",
    )

    # Farneback parameters
    parser.add_argument("--pyr-scale", type=float, default=0.5)
    parser.add_argument("--levels", type=int, default=3)
    parser.add_argument("--winsize", type=int, default=15)
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--poly-n", type=int, default=5)
    parser.add_argument("--poly-sigma", type=float, default=1.2)

    args = parser.parse_args()

    from types import SimpleNamespace

    params = SimpleNamespace(
        video=args.video,
        output=args.output,
        algorithm=args.algorithm,
        resize_percent=args.resize_percent,
        max_speed_clip=args.max_speed_clip,
        start_frame=args.start_frame,
        end_frame=args.end_frame,
        skip_frames=args.skip_frames,
        export_grid=args.export_grid,
        grid_numbers=args.num,
        pyr_scale=args.pyr_scale,
        levels=args.levels,
        winsize=args.winsize,
        iterations=args.iterations,
        poly_n=args.poly_n,
        poly_sigma=args.poly_sigma,
    )

    try:
        generate_flow_video(params)
    except RuntimeError as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
