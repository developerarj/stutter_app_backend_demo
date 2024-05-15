
from flask import Blueprint, send_from_directory
import os

static_bp = Blueprint('static', __name__)


@static_bp.route('/files/<path:subfolder>/<path:filename>', methods=['GET'])
def serve_static(subfolder, filename):
    audio_files_dir = os.path.join(os.getcwd(), "files", subfolder)
    return send_from_directory(audio_files_dir, filename)

# @app.route('/api/download/<folder_name>/<subfolder_name>/<file_name>', methods=['GET'])
# def download_file(folder_name, subfolder_name, file_name):
#     if folder_name == "final-data":
#         directory = f'{folder_name}/{subfolder_name}'
#     else:
#         directory = f'classification-files/{folder_name}/{subfolder_name}'

#     return send_from_directory(directory, file_name)
