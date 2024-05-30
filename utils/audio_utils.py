import os
import requests
from pydub import AudioSegment
from io import BytesIO  # Import BytesIO from the io module


def get_file_extension(url):
    return os.path.splitext(url)[1].lower()[1:]


def convert_mp3_to_wav_segments(url, output_folder, filename):
    # Download the file from the URL
    response = requests.get(url)
    if response.status_code != 200:
        raise ValueError("Failed to download file from the provided URL")

    # Determine the file extension from the URL
    file_extension = get_file_extension(url)
    if file_extension not in ['mp3', 'wav']:
        raise ValueError(
            "Unsupported file type. Only MP3 and WAV files are supported.")

    # Create an AudioSegment from the downloaded data
    audio = AudioSegment.from_file(
        BytesIO(response.content), format=file_extension)

    segment_length_ms = 3 * 1000  # 3 seconds in milliseconds

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    for i, start in enumerate(range(0, len(audio), segment_length_ms)):
        segment = audio[start:start + segment_length_ms]
        segment.export(f'{output_folder}/{filename}_{i + 1}.wav', format='wav')
