
from flask import Blueprint, send_from_directory, Flask, request, render_template, send_file
import os
import requests
from pydub import AudioSegment
import noisereduce as nr
import numpy as np
import io

static_bp = Blueprint('static', __name__)


def process_audio(audio):
    # Convert to numpy array
    samples = np.array(audio.get_array_of_samples())

    # Perform noise reduction
    reduced_noise = nr.reduce_noise(y=samples, sr=audio.frame_rate)

    # Increase volume by 10 dB
    audio_processed = AudioSegment(
        reduced_noise.tobytes(),
        frame_rate=audio.frame_rate,
        sample_width=audio.sample_width,
        channels=audio.channels
    )
    audio_processed += 10  # Increase volume by 10 dB

    return audio_processed


@static_bp.route('/files/<path:subfolder>/<path:filename>', methods=['GET'])
def serve_static(subfolder, filename):
    audio_files_dir = os.path.join(os.getcwd(), "files", subfolder)
    return send_from_directory(audio_files_dir, filename)


@static_bp.route('/test', methods=['GET'])
def process_audio_url():
    audio_url = request.args.get('url')
    if not audio_url:
        return 'No URL provided', 400

    # Fetch audio file from URL
    response = requests.get(audio_url)
    if response.status_code != 200:
        return 'Failed to fetch audio from URL', 400

    # Load audio file into AudioSegment
    audio = AudioSegment.from_file(io.BytesIO(response.content))

    # Process the audio file
    processed_audio = process_audio(audio)

    # Save to a BytesIO object
    buf = io.BytesIO()
    processed_audio.export(buf, format="wav")
    buf.seek(0)

    return send_file(buf, as_attachment=True, download_name='processed_audio.wav', mimetype='audio/wav')


# @app.route('/api/download/<folder_name>/<subfolder_name>/<file_name>', methods=['GET'])
# def download_file(folder_name, subfolder_name, file_name):
#     if folder_name == "final-data":
#         directory = f'{folder_name}/{subfolder_name}'
#     else:
#         directory = f'classification-files/{folder_name}/{subfolder_name}'

#     return send_from_directory(directory, file_name)
