from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash
from functools import wraps
from flask_jwt_extended import jwt_required
from bson import ObjectId
from datetime import datetime
from bson import ObjectId
from bson.errors import InvalidId
import os
from urllib.parse import urlparse


admin_bp = Blueprint('admin', __name__)

# ------------------------ Login, Register and Get details of user------------------------#

# Register user


def extract_filename_from_url(url):
    # Parse the URL
    parsed_url = urlparse(url)
    # Extract the path
    path = parsed_url.path
    # Get the filename from the path
    filename = os.path.basename(path)
    return filename


def initialize_admin_routes(mongo):
    @admin_bp.route('/admin/register', methods=['POST'])
    def register():
        data = request.json
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        isAdmin = data.get('isAdmin', False)

        if not username or not email or not password:
            return jsonify({'error': 'Missing required fields'}), 400

        existing_user = mongo.db.users.find_one({'username': username})
        if existing_user:
            return jsonify({'error': 'Username already exists'}), 400

        existing_email = mongo.db.users.find_one({'email': email})
        if existing_email:
            return jsonify({'error': 'Email already exists'}), 400

        createdDate = datetime.utcnow()

        new_user = {
            'username': username,
            'email': email,
            'password_hash': generate_password_hash(password),
            'isAdmin': isAdmin,
            'createdDate': createdDate
        }
        mongo.db.users.insert_one(new_user)

        return jsonify({'message': 'User created successfully'}), 201

    # -----------------------------Add, Delete, Update and List Model------------------------------------- #
    @admin_bp.route('/admin/modal/<modal_id>', methods=['GET'])
    @jwt_required()
    def get_modal_by_id(modal_id):
        try:
            # Convert modal_id from string to ObjectId
            modal_id = ObjectId(modal_id)
        except (InvalidId, TypeError):
            return jsonify({'error': 'Invalid modal ID format'}), 400

        # Find the modal by ID
        modal = mongo.db.modal.find_one({'_id': modal_id})

        if modal:
            # Convert ObjectId to string for JSON serialization
            modal['_id'] = str(modal['_id'])
            return jsonify(modal), 200
        else:
            return jsonify({'error': 'Modal not found'}), 404
    # Add a modal

    @admin_bp.route('/admin/modal', methods=['POST'])
    @jwt_required()
    def add_modal():
        data = request.json
        modal_type = data.get('type')
        accuracy = data.get('accuracy')
        version = data.get('version')
        isActive = data.get('isActive')
        createdDate = datetime.utcnow()
        updatedDate = createdDate

        if not modal_type or not accuracy:
            return jsonify({'error': 'Missing required fields'}), 400

        # Check if modal_type already exists
        existing_modal = mongo.db.modal.find_one({'type': modal_type})
        if existing_modal:
            return jsonify({'error': 'Modal type already exists'}), 400

        new_modal = {
            'type': modal_type,
            'accuracy': accuracy,
            'version': version,
            'isActive': isActive,
            'url': "",
            'createdDate': createdDate,
            'updatedDate': updatedDate
        }

        result = mongo.db.modal.insert_one(new_modal)

        if result:
            response = {
                'id': str(result.inserted_id),  # Access inserted_id attribute
                'message': "Modal added successfully",
            }
            return jsonify(response), 201
        else:
            return jsonify({'message': 'Modal details not found'}), 404

    # Update model

    @admin_bp.route('/admin/modal/<modal_id>', methods=['PUT'])
    @jwt_required()
    def update_modal(modal_id):
        data = request.json
        modal_type = data.get('type')
        accuracy = data.get('accuracy')
        version = data.get('version')
        isActive = data.get('isActive')
        modal_url = data.get('url')
        updatedDate = datetime.utcnow()

        existing_modal = mongo.db.modal.find_one({'_id': ObjectId(modal_id)})
        if not existing_modal:
            return jsonify({'error': 'Modal not found'}), 404

        updated_modal = {
            'updatedDate': updatedDate
        }

        if modal_type is not None:
            updated_modal['type'] = modal_type
        if accuracy is not None:
            updated_modal['accuracy'] = accuracy
        if version is not None:
            updated_modal['version'] = version
        if isActive is not None:
            updated_modal['isActive'] = isActive
        if modal_url is not None:
            updated_modal['url'] = modal_url

        # Update the modal in the database
        mongo.db.modal.update_one({'_id': ObjectId(modal_id)}, {
            '$set': {**updated_modal}})

        return jsonify({'message': 'Modal updated successfully'}), 200

    # Delete a modal

    @admin_bp.route('/admin/modal/<modal_id>', methods=['DELETE'])
    @jwt_required()
    def delete_modal(modal_id):
        existing_modal = mongo.db.modal.find_one({'_id': ObjectId(modal_id)})
        if not existing_modal:
            return jsonify({'error': 'Modal not found'}), 404

        filename = extract_filename_from_url(
            existing_modal['url'])

        file_path = os.path.join(
            "files", "modal", filename)
        if os.path.exists(file_path):
            os.remove(file_path)

        mongo.db.modal.delete_one({'_id': ObjectId(modal_id)})
        return jsonify({'message': 'Modal deleted successfully'}), 200

    # List all modals

    @admin_bp.route('/admin/list-modal', methods=['GET'])
    @jwt_required()
    def list_modals():
        # Exclude _id field from the response
        modals = list(mongo.db.modal.find({}, {'_id': 1, 'type': 1,
                                               'accuracy': 1, 'version': 1, 'isActive': 1, 'url': 1, 'createdDate': 1, 'updatedDate': 1}))

        if not modals:
            return jsonify({'message': 'No modals found'}), 404

        formatted_modals = []
        for modal in modals:
            modal['_id'] = str(modal['_id'])  # Convert ObjectId to string

            formatted_modals.append(modal)

        return jsonify({'modals': formatted_modals}), 200

# -----------------------------Add, Delete, Update and List Audio Files------------------------------------- #
    @admin_bp.route('/admin/audio-files', methods=['GET'])
    @jwt_required()
    def userAudioFiles():

        audiofiles = list(mongo.db.audioFiles.find(
            {}, {'_id': 1, 'filename': 1, 'file_url': 1, 'isPredicted': 1,  'activitySessionId': 1, 'createdDate': 1, 'updatedDate': 1}))

        if not audiofiles:
            return jsonify({'message': 'No Audio files found'}), 404

        formatted_audiofiles = []
        for file in audiofiles:
            file['_id'] = str(file['_id'])  # Convert ObjectId to string
            formatted_audiofiles.append(file)

        # Convert to JSON using dumps from bson.json_util
        return jsonify({'audiofiles': formatted_audiofiles}), 200

    # -----------------------------Add, Delete, Update and List classification------------------------------------- #

    @admin_bp.route('/admin/classification', methods=['POST'])
    @jwt_required()
    def add_classification():
        data = request.json
        title = data.get('title')
        createdDate = datetime.utcnow()
        updatedDate = createdDate

        if not title:
            return jsonify({'error': 'Missing required fields'}), 400

        new_modal = {
            'title': title,
            'createdDate': createdDate,
            'updatedDate': updatedDate
        }
        mongo.db.classifications.insert_one(new_modal)

        return jsonify({'message': 'Classification added successfully'}), 201

    @admin_bp.route('/admin/classification/<classification_id>', methods=['PUT'])
    @jwt_required()
    def update_classification(classification_id):
        data = request.json
        title = data.get('title')
        updatedDate = datetime.utcnow()

        existing_classifications = mongo.db.classifications.find_one(
            {'_id': ObjectId(classification_id)})
        if not existing_classifications:
            return jsonify({'error': 'Classification not found'}), 404

        updated_existing_classification = {
            'updatedDate': updatedDate
        }

        if title is not None:
            updated_existing_classification['title'] = title

        # Update the modal in the database
        mongo.db.classifications.update_one({'_id': ObjectId(classification_id)}, {
            '$set': {**updated_existing_classification}})

        return jsonify({'message': 'Classifications updated successfully'}), 200

    @admin_bp.route('/admin/classification/<classification_id>', methods=['DELETE'])
    @jwt_required()
    def delete_classification(classification_id):
        existing_classification = mongo.db.classifications.find_one(
            {'_id': ObjectId(classification_id)})
        if not existing_classification:
            return jsonify({'error': 'Classification not found'}), 404

        mongo.db.classifications.delete_one(
            {'_id': ObjectId(classification_id)})
        return jsonify({'message': 'Classification deleted successfully'}), 200

    @admin_bp.route('/admin/list-classifications', methods=['GET'])
    @jwt_required()
    def list_classifications():
        # Exclude _id field from the response
        classifications = list(mongo.db.classifications.find(
            {}, {'_id': 1, 'title': 1, 'createdDate': 1, 'updatedDate': 1}))

        if not classifications:
            return jsonify({'message': 'No classifications found'}), 404

        formatted_classifications = []
        for classification in classifications:
            # Convert ObjectId to string
            classification['_id'] = str(classification['_id'])
            classification['title'] = str(classification['title'])
            classification['createdDate'] = str(classification['createdDate'])
            classification['updatedDate'] = str(classification['updatedDate'])
            formatted_classifications.append(classification)

        return jsonify({'classifications': formatted_classifications}), 200

    @admin_bp.route('/admin/prediction', methods=['GET'])
    @jwt_required()
    def getPrediction():

        predictions = list(mongo.db.predictions.find({}, {
            '_id': 1, 'user_id': 1, 'audioFileId': 1, 'modalId': 1, 'totalFiles': 1,
            'fluency': 1, 'disfluency': 1, 'naturalPause': 1, 'interjection': 1,
            'noSpeech': 1, 'music': 1, 'createdDate': 1, 'updatedDate': 1
        }))

        if not predictions:
            return jsonify({'message': 'No Prediction found'}), 404

        formatted_predictions = []
        for pred in predictions:
            # Fetch the audio file object
            audio_file = mongo.db.audioFiles.find_one(
                {'_id': ObjectId(pred['audioFileId'])})
            if audio_file:
                audio_file['_id'] = str(audio_file['_id'])

            # Fetch the modal object
            modal = mongo.db.modal.find_one(
                {'_id': ObjectId(pred['modalId'])})
            if modal:
                modal['_id'] = str(modal['_id'])

            # Prepare the formatted prediction
            formatted_prediction = {
                '_id': str(pred['_id']),
                'audioFile': audio_file,
                'modal': modal,
                'totalFiles': pred.get('totalFiles'),
                'fluency': pred.get('fluency'),
                'disfluency': pred.get('disfluency'),
                'naturalPause': pred.get('naturalPause'),
                'interjection': pred.get('interjection'),
                'noSpeech': pred.get('noSpeech'),
                'music': pred.get('music'),
                'createdDate': pred.get('createdDate'),
                'updatedDate': pred.get('updatedDate')
            }

            formatted_predictions.append(formatted_prediction)

        return jsonify({'predictions': formatted_predictions}), 200

    @admin_bp.route('/admin/count', methods=['GET'])
    @jwt_required()
    def getCount():
        modal_count = mongo.db.modal.count_documents({})
        users_count = mongo.db.users.count_documents({})
        classifications_count = mongo.db.classifications.count_documents({})
        predictions_count = mongo.db.predictions.count_documents({})
        audioFiles_count = mongo.db.audioFiles.count_documents({})

        return jsonify({
            'modal_count': modal_count,
            'users_count': users_count,
            'classifications_count': classifications_count,
            'predictions_count': predictions_count,
            'audioFiles_count': audioFiles_count
        }), 200

    @admin_bp.route('/admin/activity', methods=['POST'])
    @jwt_required()
    def addActivity():
        data = request.json
        title = data.get('title')
        endpoint = data.get('endpoint')
        createdDate = datetime.utcnow()
        updatedDate = createdDate

        if not title:
            return jsonify({'error': 'Missing required fields'}), 400

        new_modal = {
            'title': title,
            'endpoint': endpoint,
            'createdDate': createdDate,
            'updatedDate': updatedDate
        }
        mongo.db.activity.insert_one(new_modal)

        return jsonify({'message': 'Activity added successfully'}), 201

    @admin_bp.route('/admin/activity/<activity_id>', methods=['DELETE'])
    @jwt_required()
    def delete_activity(activity_id):
        existing_activity = mongo.db.activity.find_one(
            {'_id': ObjectId(activity_id)})
        if not existing_activity:
            return jsonify({'error': 'Activity not found'}), 404

        mongo.db.activity.delete_one(
            {'_id': ObjectId(activity_id)})
        return jsonify({'message': 'Activity deleted successfully'}), 200

    @admin_bp.route('/admin/activity/<activity_id>', methods=['PUT'])
    @jwt_required()
    def update_activity(activity_id):
        data = request.json
        title = data.get('title')
        endpoint = data.get('endpoint')
        updatedDate = datetime.utcnow()

        existing_activity = mongo.db.activity.find_one(
            {'_id': ObjectId(activity_id)})
        if not existing_activity:
            return jsonify({'error': 'Classification not found'}), 404

        updated_existing_activity = {
            'updatedDate': updatedDate
        }

        if title is not None:
            updated_existing_activity['title'] = title

        if endpoint is not None:
            updated_existing_activity['endpoint'] = endpoint

        # Update the modal in the database
        mongo.db.activity.update_one({'_id': ObjectId(activity_id)}, {
            '$set': {**updated_existing_activity}})

        return jsonify({'message': 'Activity updated successfully'}), 200
