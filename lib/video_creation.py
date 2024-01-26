import subprocess

def create_video(game_number):
    command = [
        "nohup",
        "ffmpeg",
        "-framerate",
        "8",
        "-i",
        "screens/screenshot_%d.png",
        "-c:v",
        "libx264",
        "-r",
        "60",
        "-pix_fmt",
        "yuv420p",
        f"game_{game_number}.mp4",
    ]

    with (
        open("logs/ffmpeg_output.log", "w") as output_log,
        open("logs/ffmpeg_error.log", "w") as error_log,
    ):
        subprocess.Popen(
            command,
            cwd=f"games_archive/game_{game_number}",
            stdout=output_log,
            stderr=error_log,
        )

