import os
import sys
import json
import subprocess

from sys import exit
from urllib.request import urlopen

find_error = "Couldn't find the video segments"
usage_error = "Usage: python3 cutter.py aeSwQ-rn3D4"


def get_video_url():
    if len(sys.argv) != 2:
        raise Exception(usage_error)

    return sys.argv[-1]


def get_video_id(video_url):
    proc = subprocess.Popen([
        "youtube-dl", "-f bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4",
        video_url, "--no-warnings", "--get-id"
    ],
                            stdout=subprocess.PIPE)

    video_id = proc.stdout.read().decode("ascii").strip()
    return video_id


def get_video_duration(video_url):
    proc = subprocess.Popen(["youtube-dl", "--get-duration", video_url],
                            stdout=subprocess.PIPE)

    duration_string = proc.stdout.read().decode("ascii")
    duration = 0
    for i in duration_string.split(':'):
        duration *= 60
        duration += int(i)

        return duration


def get_video_segments(video_id):
    url = "http://sponsor.ajay.app/api/skipSegments?videoID=" + video_id

    with urlopen(url) as response:
        data = json.load(response)

        if len(data) == 0:
            raise Exception("No segments listed")

        segments = list(
            map(lambda record: [record["segment"][0], record["segment"][1]],
                data))

        return segments


def get_needed_segments(video_segments, video_duration):
    needed_segments = [[0]]

    skip_last = len(video_segments) - 1
    for index in range(skip_last):
        needed_segments[index].append(video_segments[index][0])
        needed_segments.append([])
        needed_segments[index + 1].append(video_segments[index][1])
    needed_segments[skip_last].append(video_duration)

    return needed_segments


def get_ffmpeg_arguments(needed_segments, video_file, video_output):
    input_parts = ""
    output_parts = ""
    segments_count = len(needed_segments)
    for index in range(segments_count):
        start, end = needed_segments[index]
        input_parts += "[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS,format=yuv420p[{index}v];[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[{index}a];".format(
            start=start, end=end, index=index, input_parts=input_parts)
        output_parts += "[{index}v][{index}a]".format(
            index=index)

    ffmpeg_arguments = [
        "ffmpeg", "-i", video_file, "-filter_complex",
        "{input_parts}{output_parts}concat=n={segments_count}:v=1:a=1[outv][outa]"
        .format(input_parts=input_parts,
                output_parts=output_parts,
                segments_count=segments_count), "-map", "[outv]", "-map",
        "[outa]", video_output
    ]

    return ffmpeg_arguments


def download_video(video_url, video_file):
    proc = subprocess.Popen([
        "youtube-dl", "-f bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4",
        video_url, "--output", video_file, "--no-warnings"
    ])
    proc.wait()


def run_ffmpeg_with(ffmpeg_arguments):
    proc = subprocess.Popen(ffmpeg_arguments)
    proc.wait()


##################
### Main logic ###
##################
try:
    video_file = "cutter_temp.mp4"
    video_url = get_video_url()
    video_id = get_video_id(video_url)
    video_output = video_id + ".mp4"
    video_duration = get_video_duration(video_url)
    video_segments = get_video_segments(video_id)
    needed_segments = get_needed_segments(video_segments, video_duration)
    ffmpeg_arguments = get_ffmpeg_arguments(needed_segments, video_file,
        video_output)
    download_video(video_url, video_file)
    run_ffmpeg_with(ffmpeg_arguments)

    os.remove(video_file)
    print('Done!')
except Exception as error:
    print(error)
