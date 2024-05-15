import os
import requests
from pydub import AudioSegment
from io import BytesIO  # Import BytesIO from the io module


def convert_mp3_to_wav_segments(mp3_url, output_folder, filename):
    # Download the MP3 file from the URL
    response = requests.get(mp3_url)
    if response.status_code != 200:
        raise ValueError("Failed to download MP3 file from the provided URL")

    # Create an AudioSegment from the downloaded MP3 data
    audio = AudioSegment.from_file(BytesIO(response.content), format="mp3")

    segment_length_ms = 3 * 1000  # 3 seconds in milliseconds

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    for i, start in enumerate(range(0, len(audio), segment_length_ms)):
        segment = audio[start:start + segment_length_ms]
        segment.export(f'{output_folder}/{filename}_{i + 1}.wav', format='wav')
