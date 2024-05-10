from flask import Blueprint, request, jsonify, current_app as app, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from app import mongo
import jwt
from functools import wraps
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from bson import ObjectId
import os
from werkzeug.utils import secure_filename
from datetime import datetime
from bson import ObjectId

bp = Blueprint('main', __name__)

# ----------------------------------------------------------------------------------------#


# ------------------------ Login, Register and Get details of user------------------------#

# Register user
@bp.route('/register', methods=['POST'])
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


# Login
@bp.route('/login', methods=['POST'])
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
@bp.route('/user-details', methods=['GET'])
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


# --------------------------------------------------------------------------------------------------------------#


# ------------------------------------------ Upload File -------------------------------------------------------#


# Upload file
@bp.route('/upload-file', methods=['POST'])
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


# ---------------------------------------------------------------------------------------------------- #


# -----------------------------Add, Delete, Update and List Model------------------------------------- #


# Add a modal
@bp.route('/modal', methods=['POST'])
@jwt_required()
def add_modal():
    data = request.json
    modal_type = data.get('type')
    accuracy = data.get('accuracy')
    createdDate = datetime.utcnow()
    updatedDate = createdDate

    if not modal_type or not accuracy:
        return jsonify({'error': 'Missing required fields'}), 400

    new_modal = {
        'type': modal_type,
        'accuracy': accuracy,
        'createdDate': createdDate,
        'updatedDate': updatedDate
    }
    mongo.db.modal.insert_one(new_modal)

    return jsonify({'message': 'Modal added successfully'}), 201


# Update model

@bp.route('/modal/<modal_id>', methods=['PUT'])
@jwt_required()
def update_modal(modal_id):
    data = request.json
    modal_type = data.get('type')
    accuracy = data.get('accuracy')
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
    if modal_url is not None:
        updated_modal['url'] = modal_url

    # Update the modal in the database
    mongo.db.modal.update_one({'_id': ObjectId(modal_id)}, {
                              '$set': {**updated_modal}})

    return jsonify({'message': 'Modal updated successfully'}), 200


# Delete a modal
@bp.route('/modal/<modal_id>', methods=['DELETE'])
@jwt_required()
def delete_modal(modal_id):
    existing_modal = mongo.db.modal.find_one({'_id': ObjectId(modal_id)})
    if not existing_modal:
        return jsonify({'error': 'Modal not found'}), 404

    mongo.db.modal.delete_one({'_id': ObjectId(modal_id)})
    return jsonify({'message': 'Modal deleted successfully'}), 200


# List all modals
@bp.route('/list-modal', methods=['GET'])
@jwt_required()
def list_modals():
    # Exclude _id field from the response
    modals = list(mongo.db.modal.find({}, {'_id': 1, 'type': 1,
                  'accuracy': 1, 'createdDate': 1, 'updatedDate': 1}))

    if not modals:
        return jsonify({'message': 'No modals found'}), 404

    formatted_modals = []
    for modal in modals:
        modal['_id'] = str(modal['_id'])  # Convert ObjectId to string
        modal['type'] = str(modal['type'])
        modal['accuracy'] = str(modal['accuracy'])
        modal['createdDate'] = str(modal['createdDate'])
        modal['updatedDate'] = str(modal['updatedDate'])
        formatted_modals.append(modal)

    return jsonify({'modals': formatted_modals}), 200
