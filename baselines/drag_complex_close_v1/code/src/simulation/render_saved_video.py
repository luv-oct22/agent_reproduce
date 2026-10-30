"""Render a saved benchmark scene in resumable batches, then encode an MP4.

Executed by Blender, using the .blend and sim_history.json produced by render_scene.
Frames are sampled in simulation time; the source animation's FPS is preserved.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_record import scene_settings, write_record


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['frames', 'encode'], required=True)
    parser.add_argument('--history', required=True)
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--fps', type=int, default=24)
    parser.add_argument('--resolution', nargs=2, type=int, default=[960, 640])
    parser.add_argument('--samples', type=int, default=24)
    parser.add_argument('--start', type=int, default=0, help='First output frame index, inclusive')
    parser.add_argument('--end', type=int, help='Last output frame index, exclusive')
    parser.add_argument('--hold', type=float, default=1.0, help='Seconds to hold at each end')
    parser.add_argument('--duration', type=float, help='Total encoded duration, including holds; retime cached frames without changing physics')
    parser.add_argument('--video-name', default='simulation.mp4', help='Output video filename within the output directory')
    parser.add_argument('--overwrite', action='store_true')
    argv = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    args = parser.parse_args(argv)
    if min(args.fps, args.samples, *args.resolution) <= 0 or args.hold < 0:
        parser.error('FPS, samples and resolution must be positive; hold must be nonnegative')
    if args.duration is not None and (not math.isfinite(args.duration) or
            round(args.duration*args.fps) < 2*round(args.hold*args.fps)+2):
        parser.error('Duration must leave at least two motion frames between the holds')
    if Path(args.video_name).name != args.video_name or not args.video_name.endswith('.mp4'):
        parser.error('--video-name must be an MP4 filename without directories')
    return args


def frame_path(directory, index):
    return directory / 'frames' / f'frame_{index:06d}.png'


def render_frames(args, directory, duration, count):
    scene = bpy.context.scene
    source_fps = scene.render.fps / scene.render.fps_base
    source_start = scene.frame_start
    # Reuse the same renderer setup and GPU discovery as the main render CLI.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from blender_render import setup_render
    setup_render(argparse.Namespace(samples=args.samples, resolution=args.resolution,
                                   fps=round(source_fps), still=True,
                                   output=str(directory / 'unused.png')))
    scene.render.resolution_percentage = 100
    scene.cycles.use_animated_seed = False
    scene.render.image_settings.color_mode = 'RGB'
    end = min(count, args.end if args.end is not None else count)
    if not 0 <= args.start < end:
        raise ValueError(f'Invalid batch [{args.start}, {end}); frame count is {count}')
    for index in range(args.start, end):
        path = frame_path(directory, index)
        if path.is_file() and not args.overwrite:
            print(f'SKIP completed frame {index}/{count-1}', flush=True)
            continue
        time = min(index / args.fps, duration)
        frame = source_start + time * source_fps
        scene.frame_set(math.floor(frame), subframe=frame-math.floor(frame))
        scene.render.filepath = str(path)
        print(f'RENDER frame {index}/{count-1}, simulation t={time:.4f}s', flush=True)
        bpy.ops.render.render(write_still=True)
    print(f'BATCH_COMPLETE {args.start}:{end}', flush=True)


def encode(args, directory, count):
    paths = [frame_path(directory, index) for index in range(count)]
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f'{len(missing)} frames missing; first: {missing[0]}')
    # The image frames already contain the photographic view transform.
    # Standard/sRGB output avoids applying Filmic a second time in the sequencer.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.resolution_x, scene.render.resolution_y = args.resolution
    scene.render.resolution_percentage = 100
    scene.render.fps = args.fps
    scene.render.fps_base = 1
    scene.render.use_sequencer = True
    scene.render.use_compositing = False
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1
    scene.sequencer_colorspace_settings.name = 'sRGB'
    editor = scene.sequence_editor_create()
    hold = round(args.hold * args.fps)
    motion_count = count if args.duration is None else round(args.duration*args.fps)-2*hold
    cursor = 1
    if hold:
        strip = editor.sequences.new_image('Opening hold', str(paths[0]), channel=1, frame_start=cursor)
        strip.frame_final_duration = hold
        cursor += hold
    strip = editor.sequences.new_image('Physics simulation', str(paths[0]), channel=1, frame_start=cursor)
    # Repeat source frames to slow the actual motion, retaining both endpoints.
    # Reuse original pixels rather than synthesizing intermediate object poses.
    for index in range(1, motion_count):
        source = round(index*(count-1)/(motion_count-1))
        strip.elements.append(paths[source].name)
    strip.frame_final_duration = motion_count
    cursor += motion_count
    if hold:
        strip = editor.sequences.new_image('Closing hold', str(paths[-1]), channel=1, frame_start=cursor)
        strip.frame_final_duration = hold
        cursor += hold
    scene.frame_start, scene.frame_end = 1, cursor-1
    scene.render.image_settings.file_format = 'FFMPEG'
    scene.render.ffmpeg.format = 'MPEG4'
    scene.render.ffmpeg.codec = 'H264'
    scene.render.ffmpeg.constant_rate_factor = 'HIGH'
    scene.render.ffmpeg.audio_codec = 'NONE'
    scene.render.filepath = str(directory / args.video_name)
    bpy.ops.render.render(animation=True)
    print(f'VIDEO_COMPLETE {scene.render.filepath} ({scene.frame_end / args.fps:.3f}s)', flush=True)


def main():
    args = arguments()
    directory = Path(args.output_dir).resolve()
    (directory / 'frames').mkdir(parents=True, exist_ok=True)
    with open(args.history) as stream:
        data = json.load(stream)
        history = data['history']
    if not history or history[0]['time'] != 0:
        raise ValueError('Expected a simulation history beginning at time zero')
    duration = data.get('animation', {}).get('duration', history[-1]['time'])
    count = math.ceil(duration * args.fps) + 1
    manifest = dict(fps=args.fps, resolution=args.resolution, samples=args.samples,
                    duration=duration, frames=count, source=str(Path(args.history).resolve()),
                    history_sha256=hashlib.sha256(Path(args.history).read_bytes()).hexdigest(),
                    scene_sha256=hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest())
    manifest_path = directory / 'render_settings.json'
    if manifest_path.is_file():
        previous = json.loads(manifest_path.read_text())
        if previous != manifest:
            raise ValueError('Settings differ from cached frames. Choose a new output directory.')
    else:
        manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    if args.mode == 'frames':
        render_frames(args, directory, duration, count)
        settings = scene_settings(bpy.context.scene)
        settings.update({'Mode': 'Frame batch', 'Video FPS': args.fps,
                         'Total source frames': count, 'Batch start': args.start,
                         'Batch end (exclusive)': min(count, args.end if args.end is not None else count)})
        artifact = f'frames_{args.start:06d}_{settings["Batch end (exclusive)"]:06d}'
    else:
        settings = scene_settings(bpy.context.scene)
        encode(args, directory, count)
        hold = round(args.hold*args.fps)
        frames = count+2*hold if args.duration is None else round(args.duration*args.fps)
        settings.update({'Mode': 'Video encode', 'Resolution': args.resolution,
                         'Samples': args.samples, 'Video FPS': args.fps, 'Encoded frames': frames,
                         'Video duration (s)': frames/args.fps,
                         'Opening hold (s)': hold/args.fps, 'Closing hold (s)': hold/args.fps,
                         'Motion playback duration (s)': (frames-2*hold)/args.fps,
                         'Source animation duration (s)': duration,
                         'Total source frames': count, 'Codec': 'H.264',
                         'Playback method': 'Repeated cached frames' if args.duration is not None else 'Original frame sequence'})
        artifact = args.video_name
    settings.update({'Blender version': bpy.app.version_string, 'History source': str(Path(args.history).resolve()),
                     'History SHA-256': manifest['history_sha256'], 'Scene SHA-256': manifest['scene_sha256']})
    path = write_record(directory, data, settings, artifact)
    print(f'PARAMETERS_RECORDED {path}', flush=True)


if __name__ == '__main__':
    main()
