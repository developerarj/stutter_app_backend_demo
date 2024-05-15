from flask import Blueprint, request, jsonify
from werkzeug.security import check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from bson import ObjectId
import os
from werkzeug.utils import secure_filename
from datetime import datetime
from bson import ObjectId
from utils.audio_utils import convert_mp3_to_wav_segments
from utils.predict import make_prediction
import shutil

common_bp = Blueprint('common', __name__)

# login


def initialize_common_routes(mongo):
    @common_bp.route('/common/login', methods=['POST'])
    def login():
        data = request.json
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({'error': 'Missing required fields'}), 400

        user = mongo.db.users.find_one({'username': username})

        if not user or not check_password_hash(user['password_hash'], password):
            return jsonify({'error': 'Invalid username or password'}), 401

        mongo.db.users.update_one({'_id': user['_id']}, {
            '$set': {'updatedDate': datetime.utcnow()}})

        token = create_access_token(identity=username)

        return jsonify({'message': 'Login successful', 'token': token}), 200

    # Get user details

    @common_bp.route('/common/user-details', methods=['GET'])
    @jwt_required()
    def user_details():
        current_user = get_jwt_identity()
        user = mongo.db.users.find_one({'username': current_user})

        if user:
            response = {
                'id': str(user['_id']),  # Convert ObjectId to string
                'username': user['username'],
                'email': user['email'],
                # Include isAdmin field, defaulting to False if not present
                'isAdmin': user.get('isAdmin', False),
                'createdDate': user.get('createdDate', None)
            }
            return jsonify(response), 200
        else:
            return jsonify({'message': 'User details not found'}), 404

    # ------------------------------------------ Upload File -------------------------------------------------------#
    # Upload file

    @common_bp.route('/common/upload-file', methods=['POST'])
    @jwt_required()
    def upload_file():
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400

        file = request.files['file']
        filetype = request.form.get('filetype')
        modal_type = request.form.get('modalType')
        user_id = get_jwt_identity()

        if not user_id:
            return jsonify({'error': 'User ID not provided'}), 400

        if not filetype:
            return jsonify({'error': 'Filetype not provided'}), 400

        if filetype not in ['modal', 'audio']:
            return jsonify({'error': 'Invalid filetype'}), 400

        if filetype == 'modal':
            if not modal_type:
                return jsonify({'error': 'Modal type not provided'}), 400

            # Set the folder based on filetype and modal type
            upload_folder = os.path.join("files", "modal")
            collection_name = "modal"
        else:
            # Set the folder based on filetype
            upload_folder = os.path.join("files", "audioFiles")
            collection_name = "audioFiles"

            # Fetch userID from users collection using username
            user = mongo.db.users.find_one({'username': user_id})

            if not user:
                return jsonify({'error': 'User not found'}), 404
            user_id = str(user['_id'])

        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        # Ensure filename is properly sanitized
        filename = secure_filename(file.filename)

        # Construct the destination folder path
        file_path = os.path.join(upload_folder, filename)

        # Save the file to the destination folder
        file.save(file_path)

        # Construct the file URL
        file_url = f"{request.url_root}files/{collection_name}/{filename}"
        file_url = file_url.replace("\\", "/")

        # Update the database based on filetype
        if filetype == 'modal':
            # Update the modal collection with the file URL and timestamps
            now = datetime.utcnow()
            # Update or insert depending on whether the modal already exists
            mongo.db[collection_name].update_one({'type': modal_type}, {'$set': {'url': file_url, 'updatedDate': now},
                                                                        '$setOnInsert': {'createdDate': now}}, upsert=True)
        else:
            # Insert details into the AudioFiles collection with timestamps
            now = datetime.utcnow()
            new_audio_file = {
                'filename': filename,
                'file_url': file_url,
                'user_id': user_id,
                'createdDate': now,
                'updatedDate': now
            }
            mongo.db[collection_name].insert_one(new_audio_file)

        return jsonify({'message': 'File uploaded successfully'}), 200

    @common_bp.route('/common/prediction/<path:audioFileIdId>', methods=['GET'])
    @jwt_required()
    def prediction(audioFileIdId):
        current_user = get_jwt_identity()

        audioFile = mongo.db.audioFiles.find_one(
            {'_id': ObjectId(audioFileIdId)})
        classifications = list(mongo.db.classifications.find({}, {'title': 1}))
        modals = list(mongo.db.modal.find({}, {'type': 1, 'url': 1}))

        url = audioFile['file_url']

        if not url:
            return jsonify({'error': 'audio file does not exist'}), 404

        if not audioFile:
            return jsonify({'error': 'audio file does not exist'}), 404

        if not modals:
            return jsonify({'error': 'modals file does not exist'}), 404

        if not current_user:
            return jsonify({'error': 'username not provided'}), 400

        user = mongo.db.users.find_one({'username': current_user})

        if not user:
            return jsonify({'error': 'user not found'}), 404

        user_audio_files_dir = os.path.join(
            "files", "user", '@user_' + str(user['_id']), 'seg_aud_' + str(audioFile['_id']))

        if not os.path.exists(user_audio_files_dir):
            os.makedirs(user_audio_files_dir)

        num_files_before_prediction = {}

        # Convert MP3 to WAV for each classification
        for modal in modals:
            modal_type = modal['type']
            modal_url = modal['url']
            modal_folder = os.path.join(user_audio_files_dir, modal_type)

            for classification in classifications:
                classification_folder = os.path.join(
                    modal_folder, classification['title'])

                if not os.path.exists(classification_folder):
                    os.makedirs(classification_folder)

                convert_mp3_to_wav_segments(
                    url, classification_folder, str(audioFile['_id']))

                # Count number of files in each classification before prediction
                if modal_type not in num_files_before_prediction:
                    num_files_before_prediction[modal_type] = {}

                num_files_before_prediction[modal_type][classification['title']] = len(
                    os.listdir(classification_folder))

        # Make prediction for each modal
        for modal in modals:
            modal_type = modal['type']
            modal_url = modal['url']
            modal_folder = os.path.join(user_audio_files_dir, modal_type)

            make_prediction(modal_url, modal_folder)

        # Count number of files in each modal and classification after prediction
        num_files_after_prediction = {}
        for modal in modals:
            modal_type = modal['type']
            modal_folder = os.path.join(user_audio_files_dir, modal_type)
            num_files_after_prediction[modal_type] = {}
            for classification in classifications:
                classification_folder = os.path.join(
                    modal_folder, classification['title'])
                num_files_after_prediction[modal_type][classification['title']] = len(
                    os.listdir(classification_folder))

        result = {'data': url, 'num_files_before_prediction': num_files_before_prediction,
                  'num_files_after_prediction': num_files_after_prediction}

        shutil.rmtree(user_audio_files_dir)

        return jsonify(result), 200
