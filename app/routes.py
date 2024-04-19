from flask import Blueprint, request, jsonify, current_app as app,send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from app import mongo
import jwt
from functools import wraps
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from bson import ObjectId
import os
from werkzeug.utils import secure_filename


bp = Blueprint('main', __name__)

# Register user
@bp.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
        return jsonify({'error': 'Missing required fields'}), 400

    existing_user = mongo.db.users.find_one({'username': username})
    if existing_user:
        return jsonify({'error': 'Username already exists'}), 400

    new_user = {
        'username': username,
        'email': email,
        'password_hash': generate_password_hash(password)
    }
    mongo.db.users.insert_one(new_user)

    return jsonify({'message': 'User created successfully'}), 201

# User login
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

    token = create_access_token(identity=username)

    return jsonify({'message': 'Login successful', 'token': token}), 200

# Get user details
@bp.route('/user-details', methods=['GET'])
@jwt_required()
def user_details():
    current_user = get_jwt_identity()
    user = mongo.db.users.find_one({'username': current_user})
    
    if user:
        response = {'username': user['username'], 'email': user['email']}
        return jsonify(response), 200
    else:
        return jsonify({'message': 'User details not found'}), 404

# Add a model
@bp.route('/stutter-class-model', methods=['POST'])
def add_model():
    data = request.json
    model_name = data.get('model_name')
    model_url = data.get('model_url')

    if not model_name or not model_url:
        return jsonify({'error': 'Missing required fields'}), 400
    
    existing_model = mongo.db.stutter_class_model.find_one({'model_name': model_name})
    if existing_model:
        return jsonify({'message': 'You have already added this model.'}), 400

    new_model = {'model_name': model_name, 'model_url': model_url}
    mongo.db.stutter_class_model.insert_one(new_model)

    return jsonify({'message': 'Model added successfully'}), 201

# Edit a model
@bp.route('/stutter-class-model/<model_id>', methods=['PUT'])
def edit_model(model_id):
    data = request.json
    model_name = data.get('model_name')
    model_url = data.get('model_url')

    if not model_name or not model_url:
        return jsonify({'error': 'Missing required fields'}), 400

    existing_model = mongo.db.stutter_class_model.find_one({'_id': ObjectId(model_id)})
    if not existing_model:
        return jsonify({'error': 'Model not found'}), 404
    
    if existing_model['model_name'] == model_name and existing_model['model_url'] == model_url:
        return jsonify({'message': 'You have already updated this model.'}), 400

    mongo.db.stutter_class_model.update_one({'_id': ObjectId(model_id)}, {'$set': {'model_name': model_name, 'model_url': model_url}})
    return jsonify({'message': 'Model updated successfully'}), 200

# Delete a model
@bp.route('/stutter-class-model/<model_id>', methods=['DELETE'])
def delete_model(model_id):
    existing_model = mongo.db.stutter_class_model.find_one({'_id': ObjectId(model_id)})
    if not existing_model:
        return jsonify({'error': 'Model not found'}), 404

    mongo.db.stutter_class_model.delete_one({'_id': ObjectId(model_id)})
    return jsonify({'message': 'Model deleted successfully'}), 200


#Upload model.
import os
from flask import request, jsonify
from werkzeug.utils import secure_filename
from flask_jwt_extended import jwt_required, get_jwt_identity

@bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    username = get_jwt_identity()

    if not username:
        return jsonify({'error': 'Username not provided'}), 400

    user_folder = "files/model"

    type_field = request.form.get('type')  # Assuming 'type' field is sent as form data

    if type_field == 'model':
        upload_folder = os.path.join(user_folder, "model")
    else:
        upload_folder = user_folder

    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # Ensure filename is properly sanitized
    filename = secure_filename(file.filename)

    # Check if the file has .h5 extension
    if not filename.endswith('.h5'):
        return jsonify({'error': 'Invalid file format. Only .h5 files are allowed'}), 400

    # Construct the destination folder path
    file_path = os.path.join(upload_folder, filename)

    # Save the file to the destination folder
    file.save(file_path)

    # Construct the file URL
    file_url = f"{request.url_root}files/model/{filename}" if type_field == 'model' else f"{request.url_root}files/{filename}"

    return jsonify({'message': 'File uploaded successfully', 'filename': filename, 'file_url': file_url}), 201
