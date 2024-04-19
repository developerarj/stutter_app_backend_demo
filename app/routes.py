from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from app import mongo, create_app
import jwt

from functools import wraps
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity

bp = Blueprint('main', __name__)


@bp.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
        return jsonify({'error': 'Missing required fields'}), 400

    # Check if the username already exists in the database
    existing_user = mongo.db.users.find_one({'username': username})
    if existing_user:
        return jsonify({'error': 'Username already exists'}), 400

    # Create a new user document
    new_user = {
        'username': username,
        'email': email,
        'password_hash': generate_password_hash(password)  # Hash the password before storing
    }

    # Insert the new user document into the 'users' collection
    mongo.db.users.insert_one(new_user)

    return jsonify({'message': 'User created successfully'}), 201


@bp.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Missing required fields'}), 400

    # Query the user from the MongoDB database
    user = mongo.db.users.find_one({'username': username})

    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({'error': 'Invalid username or password'}), 401

    # Generate token
    token = create_access_token(identity=username)

    return jsonify({'message': 'Login successful', 'token': token}), 200

    
@bp.route('/user-details', methods=['GET'])
@jwt_required()  # Requires a valid JWT token to access
def user_details():
    current_user = get_jwt_identity()  # Get the identity of the current user from the JWT token
    user = mongo.db.users.find_one({'username': current_user})  # Find user in the 'users' collection
    
    if user:
        response = {
            'username': user['username'],
            'email': user['email']
        }
        
        return jsonify(response), 200
    else:
        return jsonify({'message': 'User details not found'}), 404
    