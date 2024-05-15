from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash
from functools import wraps
from flask_jwt_extended import jwt_required
from bson import ObjectId
from datetime import datetime
from bson import ObjectId

admin_bp = Blueprint('admin', __name__)

# ------------------------ Login, Register and Get details of user------------------------#

# Register user


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
    # Add a modal

    @admin_bp.route('/admin/modal', methods=['POST'])
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

    @admin_bp.route('/admin/modal/<modal_id>', methods=['PUT'])
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

    @admin_bp.route('/admin/modal/<modal_id>', methods=['DELETE'])
    @jwt_required()
    def delete_modal(modal_id):
        existing_modal = mongo.db.modal.find_one({'_id': ObjectId(modal_id)})
        if not existing_modal:
            return jsonify({'error': 'Modal not found'}), 404

        mongo.db.modal.delete_one({'_id': ObjectId(modal_id)})
        return jsonify({'message': 'Modal deleted successfully'}), 200

    # List all modals

    @admin_bp.route('/admin/list-modal', methods=['GET'])
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
