# user_routes.py

from flask import Blueprint, jsonify
from functools import wraps
from flask_jwt_extended import jwt_required, get_jwt_identity


user_bp = Blueprint('user', __name__)


# -----------------------------Add, Delete, Update and List AudioFiles------------------------------------- #
def initialize_user_routes(mongo):
    @user_bp.route('/user/audio-files', methods=['GET'])
    @jwt_required()
    def userAudioFiles():
        current_user = get_jwt_identity()

        if not current_user:
            return jsonify({'error': 'username not provided'}), 400

        user = mongo.db.users.find_one({'username': current_user})

        if not user:
            return jsonify({'error': 'user does not exist'}), 404

        audiofiles = list(mongo.db.audioFiles.find({'user_id': str(user['_id'])}, {'_id': 1, 'filename': 1,
                                                                                   'file_url': 1, 'createdDate': 1, 'updatedDate': 1}))

        if not audiofiles:
            return jsonify({'message': 'No Audio files found'}), 404

        formatted_audiofiles = []
        for file in audiofiles:
            file['_id'] = str(file['_id'])  # Convert ObjectId to string
            file['filename'] = str(file['filename'])
            file['file_url'] = str(file['file_url'])
            file['createdDate'] = str(file['createdDate'])
            file['updatedDate'] = str(file['updatedDate'])
            formatted_audiofiles.append(file)

        # Convert to JSON using dumps from bson.json_util
        return jsonify({'audiofiles': formatted_audiofiles}), 200
