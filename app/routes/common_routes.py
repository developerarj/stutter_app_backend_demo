import openai
from flask import Blueprint, request, jsonify
from werkzeug.security import check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from bson import ObjectId
import os
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from bson import ObjectId
from utils.audio_utils import convert_mp3_to_wav_segments
from utils.predict import make_prediction
from utils.openAi.generate_feedback import generate_feedback
from utils.openAi.generate_improvement_tips import generate_improvement_tips
from utils.openAi.generate_practice_dialogue import generate_practice_dialogue
from utils.openAi.generate_progress_report import generate_progress_report
import shutil
from openai import OpenAI
from dotenv import load_dotenv
from pydub import AudioSegment
import noisereduce as nr
import numpy as np
import io
import uuid
import random

load_dotenv()


common_bp = Blueprint('common', __name__)

# login


def process_audio(audio, passes=1, prop_decrease=0.30):
    samples = np.array(audio.get_array_of_samples())

    for _ in range(passes):
        reduced_noise = nr.reduce_noise(
            y=samples, sr=audio.frame_rate, prop_decrease=prop_decrease
        )
        # Update samples for the next pass
        samples = reduced_noise

    reduced_audio_segment = AudioSegment(
        reduced_noise.tobytes(),
        frame_rate=audio.frame_rate,
        sample_width=audio.sample_width,
        channels=audio.channels
    )

    reduced_audio_segment = reduced_audio_segment.low_pass_filter(
        3400).high_pass_filter(300)

    # Increase volume by 10 dB
    reduced_audio_segment += 10  # Increase volume by 10 dB

    return reduced_audio_segment


def convert_object_ids(data):
    if isinstance(data, list):
        return [convert_object_ids(item) for item in data]
    elif isinstance(data, dict):
        return {key: convert_object_ids(value) for key, value in data.items()}
    elif isinstance(data, ObjectId):
        return str(data)
    else:
        return data


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

        return jsonify({'message': 'Login successful', 'token': token, 'isAdmin': user['isAdmin']}), 200

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

    @common_bp.route('/common/upload-audio-file', methods=['POST'])
    @jwt_required()
    def upload_audio_file():
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400

        file = request.files['file']
        user_id = get_jwt_identity()

        if not user_id:
            return jsonify({'error': 'User ID not provided'}), 400

        if not file.content_type.startswith('audio'):
            return jsonify({'error': 'File is not an audio file'}), 400

        # Fetch userID from users collection using username
        user = mongo.db.users.find_one({'username': user_id})
        if not user:
            return jsonify({'error': 'User not found'}), 404
        user_id = str(user['_id'])

        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        collection_name = "audioFiles"
        upload_folder = os.path.join("files", collection_name)
        os.makedirs(upload_folder, exist_ok=True)

        # Convert the audio blob to MP3 if it's not already in MP3 format
        if file.content_type != 'audio/mpeg':
            audio_blob = AudioSegment.from_file(io.BytesIO(file.read()))

            # Process the audio file
            processed_audio = process_audio(audio_blob)

            mp3_bytes = io.BytesIO()
            processed_audio.export(mp3_bytes, format="mp3")
            mp3_bytes.seek(0)

            # Generate a unique filename for the MP3 file
            filename = f"{uuid.uuid4().hex}.mp3"

            # Set the folder based on filetype
            file_path = os.path.join(upload_folder, filename)

            # Save the MP3 file to the destination folder
            with open(file_path, "wb") as mp3_file:
                mp3_file.write(mp3_bytes.read())

            # Construct the file URL
            file_url = f"{request.url_root}files/audioFiles/{filename}"
            file_url = file_url.replace("\\", "/")
        else:
            # File is already in MP3 format, read and process it
            audio_blob = AudioSegment.from_file(io.BytesIO(file.read()))

            # Process the audio file
            processed_audio = process_audio(audio_blob)

            # Save the processed audio file
            filename = secure_filename(file.filename)
            file_path = os.path.join(upload_folder, filename)
            processed_audio.export(file_path, format="mp3")

            # Construct the file URL
            file_url = f"{request.url_root}files/{collection_name}/{filename}"
            file_url = file_url.replace("\\", "/")

        # Update the database based on filetype
        now = datetime.utcnow()
        new_audio_file = {
            'filename': filename,
            'file_url': file_url,
            "isPredicted": False,
            'user_id': user_id,
            'createdDate': now,
            'updatedDate': now
        }
        mongo.db[collection_name].insert_one(new_audio_file)

        return jsonify({'message': 'File uploaded successfully'}), 200

    @common_bp.route('/common/upload-modal-file', methods=['POST'])
    @jwt_required()
    def upload_modal_file():
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400

        file = request.files['file']
        modal_type = request.form.get('modalType')
        user_id = get_jwt_identity()

        if not user_id:
            return jsonify({'error': 'User ID not provided'}), 400

        modal = mongo.db.modal.find_one({'type': modal_type})
        if not modal:
            return jsonify({'error': 'Modal type not found'}), 404
        version = modal.get('version', 'unknown')

        upload_folder = os.path.join("files", "modal")
        collection_name = "modal"

        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        filename = secure_filename(file.filename)

        name, ext = os.path.splitext(filename)
        filename = f"{name}_v{version}{ext}"

        file_path = os.path.join(upload_folder, filename)

        file.save(file_path)

        # Construct the file URL
        file_url = f"{request.url_root}files/{collection_name}/{filename}"
        file_url = file_url.replace("\\", "/")

        # Update the database based on filetype
        now = datetime.utcnow()

        mongo.db[collection_name].update_one(
            {'type': modal_type},
            {'$set': {'url': file_url, 'updatedDate': now},
             '$setOnInsert': {'createdDate': now}},
            upsert=True
        )

        return jsonify({'message': 'File uploaded successfully'}), 200

    @common_bp.route('/common/upload-activity-file', methods=['POST'])
    @jwt_required()
    def upload_activity_file():
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400

        file = request.files['file']
        text = request.form.get('text')
        activitySessionId = request.form.get('activitySessionId')
        user_id = get_jwt_identity()

        if not user_id:
            return jsonify({'error': 'User ID not provided'}), 400

        collection_name = "audioFiles"
        if file.content_type.startswith('audio'):
            # Convert the audio blob to MP3 if it's not already in MP3 format
            if file.content_type != 'audio/mpeg':

                audio_blob = AudioSegment.from_file(io.BytesIO(file.read()))

                processed_audio = process_audio(audio_blob)

                mp3_bytes = io.BytesIO()
                processed_audio.export(mp3_bytes, format="mp3")
                mp3_bytes.seek(0)

                # Generate a unique filename for the MP3 file
                filename = f"{uuid.uuid4().hex}.mp3"

                # Set the folder based on filetype
                upload_folder = os.path.join("files", "audioFiles")
                file_path = os.path.join(upload_folder, filename)

                # Save the MP3 file to the destination folder
                with open(file_path, "wb") as mp3_file:
                    mp3_file.write(mp3_bytes.read())

                # Construct the file URL
                file_url = f"{request.url_root}files/audioFiles/{filename}"
                file_url = file_url.replace("\\", "/")

        user = mongo.db.users.find_one({'username': user_id})
        if not user:
            return jsonify({'error': 'User not found'}), 404
        user_id = str(user['_id'])

        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        filename = secure_filename(file.filename)

        now = datetime.utcnow()
        new_audio_file = {
            'filename': filename,
            'file_url': file_url,
            "isPredicted": False,
            "activitySessionId": str(activitySessionId),
            "text": str(text),
            'user_id': user_id,
            'createdDate': now,
            'updatedDate': now
        }
        mongo.db[collection_name].insert_one(new_audio_file)

        return jsonify({'message': 'File uploaded successfully'}), 200

    # ------------------------------------------ prediction -------------------------------------------------------#
    # prediction
    @common_bp.route('/common/prediction/<path:audioFileIdId>', methods=['GET'])
    @jwt_required()
    def prediction(audioFileIdId):
        current_user = get_jwt_identity()

        audioFile = mongo.db.audioFiles.find_one(
            {'_id': ObjectId(audioFileIdId)})
        classifications = list(mongo.db.classifications.find({}, {'title': 1}))
        modals = list(mongo.db.modal.find(
            {'isActive': True, 'url': {'$ne': ''}}, {'type': 1, 'url': 1}))

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

        updated_audioFile = mongo.db.audioFiles.find_one({'_id': ObjectId(audioFileIdId)}, {
                                                         '_id': 1, 'filename': 1, 'file_url': 1, 'createdDate': 1, 'updatedDate': 1, 'isPredicted': 1})

        # Convert ObjectIds to strings
        updated_audioFile = convert_object_ids(updated_audioFile)

        modal_details = list(mongo.db.modal.find({'isActive': True, 'url': {'$ne': ''}}, {
                             '_id': 1, 'type': 1, 'url': 1, 'version': 1, 'createdDate': 1, 'updatedDate': 1}))

        modal_details = convert_object_ids(modal_details)

        result = {
            'url': url,
            'num_files_before_prediction': num_files_before_prediction,
            'num_files_after_prediction': num_files_after_prediction,
            'audioFile': updated_audioFile,
            'modalsUsed': modal_details
        }

        shutil.rmtree(user_audio_files_dir)

        updated_audioFile_data = {
            'isPredicted': True
        }

        mongo.db.audioFiles.update_one({'_id': ObjectId(audioFileIdId)}, {
            '$set': updated_audioFile_data})

        return jsonify(result), 200

    @common_bp.route('/common/prediction', methods=['POST'])
    @jwt_required()
    def save_prediction():
        current_user = get_jwt_identity()

        if not current_user:
            return jsonify({'error': 'username not provided'}), 400

        user = mongo.db.users.find_one({'username': current_user})

        if not user:
            return jsonify({'error': 'user does not exist'}), 404

        data = request.json
        userId = user['_id']
        audioFileId = data.get('audioFileId')
        activitySessionId = data.get('activitySessionId')
        modals = data.get('modalsUsed')
        num_files_after_prediction = data.get('num_files_after_prediction')
        num_files_before_prediction = data.get('num_files_before_prediction')
        createdDate = datetime.utcnow()
        updatedDate = createdDate

        predictions = []

        for modal in modals:
            modal_id = str(modal['_id'])
            modal_type = str(modal['type'])
            existing_prediction = mongo.db.predictions.find_one(
                {'user_id': str(userId), 'audioFileId': str(
                    audioFileId), 'modalId': modal_id}
            )
            if existing_prediction:
                modal['_id'] = modal_id
                predictions.append(existing_prediction)
            else:
                fluency = num_files_after_prediction.get(
                    modal_type, {}).get('Fluent', 0)
                disfluency = num_files_after_prediction.get(
                    modal_type, {}).get('Disfluent', 0)
                natural_pause = num_files_after_prediction.get(
                    modal_type, {}).get('NaturalPause', 0)
                interjection = num_files_after_prediction.get(
                    modal_type, {}).get('Interjection', 0)
                no_speech = num_files_after_prediction.get(
                    modal_type, {}).get('NoSpeech', 0)
                music = num_files_after_prediction.get(
                    modal_type, {}).get('Music', 0)
                total_files = num_files_before_prediction.get(
                    modal_type, {}).get('Disfluent', 0)

                new_predictions = {
                    'user_id': str(userId),
                    'audioFileId': str(audioFileId),
                    'modalId': str(modal_id),
                    'totalFiles': total_files,
                    'fluency': fluency,
                    'disfluency': disfluency,
                    'naturalPause': natural_pause,
                    'interjection': interjection,
                    'noSpeech': no_speech,
                    'music': music,
                    'activitySessionId': activitySessionId,
                    'createdDate': createdDate,
                    'updatedDate': updatedDate
                }

                result = mongo.db.predictions.insert_one(new_predictions)
                inserted_id = result.inserted_id
                inserted_prediction = mongo.db.predictions.find_one(
                    {'_id': inserted_id})
                predictions.append(inserted_prediction)

        response = {
            'message': "Prediction saved successfully",
            'predictions': convert_object_ids(predictions)
        }

        return jsonify(response), 201

    # ------------------------------------------ feedback -------------------------------------------------------#
    # feedback
    @common_bp.route('/common/feedback', methods=['POST'])
    @jwt_required()
    def feedback():
        current_user = get_jwt_identity()

        if not current_user:
            return jsonify({'error': 'username not provided'}), 400

        user = mongo.db.users.find_one({'username': current_user})

        if not user:
            return jsonify({'error': 'user does not exist'}), 404

        data = request.json
        userId = user['_id']
        predictionId = data.get('predictionId')
        disfluency = data.get('disfluency')
        fluency = data.get('fluency')
        interjection = data.get('interjection')
        naturalPause = data.get('naturalPause')
        activitySessionId = data.get('activitySessionId')
        createdDate = datetime.utcnow()
        updatedDate = createdDate

        result = {
            "disfluency": disfluency,
            "fluency": fluency,
            "interjection": interjection,
            "naturalPause": naturalPause,
        }

        feedback = mongo.db.feedback.find_one(
            {'predictionId': str(predictionId)})

        if not feedback:
            feedback = generate_feedback(result)

            new_feedback = {
                'user_id': str(userId),
                'predictionId': str(predictionId),
                'feedback': feedback,
                "disfluency": disfluency,
                "fluency": fluency,
                "interjection": interjection,
                "naturalPause": naturalPause,
                "activitySessionId": activitySessionId,
                'createdDate': createdDate,
                'updatedDate': updatedDate
            }

            result = mongo.db.feedback.insert_one(new_feedback)
            inserted_id = result.inserted_id

            return jsonify({'feedbackId': str(inserted_id), 'message': 'Feedback added successfully'}), 200
        else:
            return jsonify({'feedbackId': str(feedback['_id']), 'message': 'Feedback added successfully'}), 200

    @common_bp.route('/common/feedback/<feedbackId>', methods=['GET'])
    @jwt_required()
    def get_feedback(feedbackId):
        try:
            feedback = mongo.db.feedback.find_one(
                {'_id': ObjectId(feedbackId)})
        except:
            return jsonify({'error': 'Invalid feedback ID'}), 400

        if not feedback:
            return jsonify({'error': 'Feedback not found'}), 404

        # Convert ObjectId fields to strings for the response
        feedback['_id'] = str(feedback['_id'])
        feedback['user_id'] = str(feedback['user_id'])

        # Fetch the associated prediction object
        prediction = mongo.db.predictions.find_one(
            {'_id': ObjectId(feedback['predictionId'])})

        if prediction:
            prediction['_id'] = str(prediction['_id'])
            prediction['user_id'] = str(prediction['user_id'])

            # Fetch the associated modal object
            modal = mongo.db.modal.find_one(
                {'_id': ObjectId(prediction['modalId'])})
            if modal:
                modal['_id'] = str(modal['_id'])
                prediction['modal'] = modal
            else:
                prediction['modal'] = None

            # Fetch the associated audio file object
            audio_file = mongo.db.audioFiles.find_one(
                {'_id': ObjectId(prediction['audioFileId'])})
            if audio_file:
                audio_file['_id'] = str(audio_file['_id'])

                prediction['audioFile'] = audio_file
            else:
                prediction['audioFile'] = None

            # Remove the IDs that have been replaced with their objects
            del prediction['modalId']
            del prediction['audioFileId']
            del prediction['user_id']
            del audio_file['user_id']

            feedback['prediction'] = prediction
        else:
            feedback['prediction'] = None

        # Remove the predictionId from the feedback object
        del feedback['predictionId']
        del feedback['user_id']

        return jsonify(feedback), 200

    @common_bp.route('/common/progess-report', methods=['GET'])
    @jwt_required()
    def getProgress():
        current_user = get_jwt_identity()

        if not current_user:
            return jsonify({'error': 'username not provided'}), 400

        user = mongo.db.users.find_one({'username': current_user})

        if not user:
            return jsonify({'error': 'user does not exist'}), 404

        feedbacks = list(mongo.db.feedback.find({'user_id': str(user['_id'])}, {
            '_id': 1, 'feedback': 1, 'disfluency': 1, 'fluency': 1, 'interjection': 1, 'naturalPause': 1, 'createdDate': 1, 'updatedDate': 1}))

        if not feedbacks:
            return jsonify({'error': 'No feedback found for the user'}), 404

         # Format historical data
        historical_data = ""
        for feedback in feedbacks:
            feedback_date = feedback['createdDate'].strftime(
                "%Y-%m-%d %H:%M:%S")
            historical_data += f"Date: {feedback_date}\nDisfluency: {feedback['disfluency']}%\nFluency: {feedback['fluency']}%\nInterjection: {feedback['interjection']}%\nNatural Pause: {feedback['naturalPause']}%\n\n"

        # Generate progress report
        progress_report = generate_progress_report(
            str(user['_id']), historical_data)

        return jsonify({'progress_report': progress_report}), 200

    @common_bp.route('/common/open-ai-test', methods=['GET'])
    @jwt_required()
    def gptTest():

        result = {
            "disfluency": "12.63%",
            "fluency": "0.5%",
            "interjection": "6.57%",
            "naturalPause": "76.26%",
        }

        # feedback = generate_feedback(result)
        # feedback = generate_improvement_tips(result)
        feedback = generate_practice_dialogue("Rain")
        # feedback = generate_progress_report(user_id, historical_data)

        return jsonify({'message': feedback}), 200

    # ------------------------------------------ Activity -------------------------------------------------------#
    # Activity

    @common_bp.route('/common/list-activity', methods=['GET'])
    @jwt_required()
    def listActivity():
        # Exclude _id field from the response
        activities = list(mongo.db.activity.find(
            {}, {'_id': 1, 'title': 1, 'endpoint': 1, 'createdDate': 1, 'updatedDate': 1}))

        if not activities:
            return jsonify({'message': 'No classifications found'}), 404

        formatted_activities = []
        for activity in activities:
            # Convert ObjectId to string

            activityTheme = list(mongo.db.activityTheme.find(
                {'activity_id': str(activity['_id'])}, {'_id': 1, 'theme': 1, 'activity_id': 1, 'createdDate': 1, 'updatedDate': 1}))

            formatted_activityThemes = []
            for theme in activityTheme:
                theme['_id'] = str(theme['_id'])

                formatted_activityThemes.append(theme)

            formatted_activity = {
                '_id': str(activity['_id']),
                'title': activity['title'],
                'endpoint': activity['endpoint'],
                'theme': formatted_activityThemes,
                'createdDate': activity.get('createdDate'),
                'updatedDate': activity.get('updatedDate')
            }

            formatted_activities.append(formatted_activity)

        return jsonify({'activities': formatted_activities}), 200

    @common_bp.route('/common/list-activity-session', methods=['GET'])
    @jwt_required()
    def listActivitySession():
        current_user = get_jwt_identity()

        user = mongo.db.users.find_one({'username': current_user})

        if not user:
            return jsonify({'error': 'user not found'}), 404

        # Exclude _id field from the response
        activitySessions = list(mongo.db.activitySession.find(
            {'userId': str(user['_id'])},
            {'_id': 1, 'activity_id': 1, 'theme_id': 1, 'createdDate': 1, 'updatedDate': 1}))

        if not activitySessions:
            return jsonify({'message': 'No activities found'}), 404

        formatted_activitySessions = []
        for session in activitySessions:

            activity = mongo.db.activity.find_one(
                {'_id': ObjectId(session['activity_id'])})
            if activity:
                activity['_id'] = str(activity['_id'])

            theme = mongo.db.activityTheme.find_one(
                {'_id': ObjectId(session['theme_id'])})
            if theme:
                theme['_id'] = str(theme['_id'])

            # Convert ObjectId to string
            formatted_activitySession = {
                '_id': str(session['_id']),
                'activity': activity,
                'theme': theme,
                'createdDate': session.get('createdDate'),
                'updatedDate': session.get('updatedDate')
            }

            formatted_activitySessions.append(formatted_activitySession)

        return jsonify({'activities': formatted_activitySessions}), 200

    @common_bp.route('/common/activity-session', methods=['POST'])
    @jwt_required()
    def addActivitySession():
        current_user = get_jwt_identity()

        user = mongo.db.users.find_one({'username': current_user})

        if not user:
            return jsonify({'error': 'user not found'}), 404

        activity_id = request.json.get('activity_id')
        theme_id = request.json.get('theme_id')
        if not activity_id:
            return jsonify({'error': 'activity_id is required'}), 400

        if not theme_id:
            return jsonify({'error': 'activity_id is required'}), 400

        session_data = {
            'userId': str(user['_id']),
            'activity_id': str(activity_id),
            'theme_id': str(theme_id),
            'createdDate': datetime.utcnow(),
            'updatedDate': datetime.utcnow()
        }
        result = mongo.db.activitySession.insert_one(session_data)
        new_session = mongo.db.activitySession.find_one(
            {'_id': result.inserted_id})

        new_session['_id'] = str(new_session['_id'])

        return jsonify(new_session), 200

    @common_bp.route('/common/activity-session/<activity_id>', methods=['GET'])
    @jwt_required()
    def getActivitySession(activity_id):
        current_user = get_jwt_identity()

        if not current_user:
            return jsonify({'error': 'username not provided'}), 400

        user = mongo.db.users.find_one({'username': current_user})

        activitySessions = list(mongo.db.activitySession.find(
            {'userId': str(user['_id']), 'activity_id': activity_id},
            {'_id': 1, 'activity_id': 1, 'theme_id': 1,  'createdDate': 1, 'updatedDate': 1}))

        if not activitySessions:
            return jsonify({'message': 'No activities found'}), 404

        formatted_activitySessions = []
        for session in activitySessions:

            activity = mongo.db.activity.find_one(
                {'_id': ObjectId(session['activity_id'])})
            if activity:
                activity['_id'] = str(activity['_id'])

            theme = mongo.db.activityTheme.find_one(
                {'_id': ObjectId(session['theme_id'])})
            if theme:
                theme['_id'] = str(theme['_id'])

            # Convert ObjectId to string
            formatted_activitySession = {
                '_id': str(session['_id']),
                'activity': activity,
                'theme': theme,
                'createdDate': session.get('createdDate'),
                'updatedDate': session.get('updatedDate')
            }

            formatted_activitySessions.append(formatted_activitySession)

        return jsonify({'activities': formatted_activitySessions}), 200

    @common_bp.route('/common/session-results/<session_id>', methods=['GET'])
    @jwt_required()
    def getSessionResults(session_id):
        current_user = get_jwt_identity()

        if not current_user:
            return jsonify({'error': 'username not provided'}), 400

        user = mongo.db.users.find_one({'username': current_user})

        if not user:
            return jsonify({'error': 'user not found'}), 404

        activitySession = mongo.db.activitySession.find_one(
            {'_id': ObjectId(session_id)})

        if not activitySession:
            return jsonify({'error': 'Session not found'}), 404

        predictions_count = mongo.db.predictions.count_documents(
            {'activitySessionId': str(session_id)})

        if predictions_count != 0:
            return jsonify({'error': 'Prediction exist'}), 409

        else:
            audioFiles = list(mongo.db.audioFiles.find(
                {'activitySessionId': str(session_id)},
                {'_id': 1, 'filename': 1, 'file_url': 1, 'activitySessionId': 1, 'text': 1, 'createdDate': 1, 'updatedDate': 1}))

            if not audioFiles:
                return jsonify({'message': 'No audio files found'}), 404

            classifications = list(
                mongo.db.classifications.find({}, {'title': 1}))
            modals = list(mongo.db.modal.find(
                {'isActive': True, 'url': {'$ne': ''}}, {'type': 1, 'url': 1}))

            for files in audioFiles:

                url = files['file_url']
                user_audio_files_dir = os.path.join(
                    "files", "user", '@user_' + str(user['_id']), 'seg_aud_' + str(files['_id']))

                if not os.path.exists(user_audio_files_dir):
                    os.makedirs(user_audio_files_dir)

                num_files_before_prediction = {}

                for modal in modals:
                    modal_type = modal['type']
                    modal_url = modal['url']
                    modal_folder = os.path.join(
                        user_audio_files_dir, modal_type)

                    for classification in classifications:
                        classification_folder = os.path.join(
                            modal_folder, classification['title'])

                        if not os.path.exists(classification_folder):
                            os.makedirs(classification_folder)

                        convert_mp3_to_wav_segments(
                            url, classification_folder, str(files['_id']))

                        # Count number of files in each classification before prediction
                        if modal_type not in num_files_before_prediction:
                            num_files_before_prediction[modal_type] = {}

                        num_files_before_prediction[modal_type][classification['title']] = len(
                            os.listdir(classification_folder))

                for modal in modals:
                    modal_type = modal['type']
                    modal_url = modal['url']
                    modal_folder = os.path.join(
                        user_audio_files_dir, modal_type)

                    make_prediction(modal_url, modal_folder)

                num_files_after_prediction = {}
                for modal in modals:
                    modal_type = modal['type']
                    modal_folder = os.path.join(
                        user_audio_files_dir, modal_type)
                    num_files_after_prediction[modal_type] = {}
                    for classification in classifications:
                        classification_folder = os.path.join(
                            modal_folder, classification['title'])
                        num_files_after_prediction[modal_type][classification['title']] = len(
                            os.listdir(classification_folder))

                updated_audioFile_data = {
                    'isPredicted': True
                }

                mongo.db.audioFiles.update_one({'_id': ObjectId(files['_id'])}, {
                    '$set': updated_audioFile_data})

                updated_audioFile = mongo.db.audioFiles.find_one({'_id': ObjectId(files['_id'])}, {
                    '_id': 1, 'filename': 1, 'file_url': 1, 'text': 1, 'createdDate': 1, 'updatedDate': 1, 'isPredicted': 1})

                updated_audioFile = str(updated_audioFile['_id'])

                for modal in modals:

                    new_prediction = {
                        'user_id': str(user['_id']),
                        'audioFileId': str(files['_id']),
                        'modalId': str(modal['_id']),
                        'totalFiles': num_files_before_prediction[modal['type']]['Disfluent'],
                        'fluency': num_files_after_prediction[modal['type']]['Fluent'],
                        'disfluency': num_files_after_prediction[modal['type']]['Disfluent'],
                        'naturalPause': num_files_after_prediction[modal['type']]['NaturalPause'],
                        'interjection': num_files_after_prediction[modal['type']]['Interjection'],
                        'noSpeech': num_files_after_prediction[modal['type']]['NoSpeech'],
                        'music': num_files_after_prediction[modal['type']]['Music'],
                        'activitySessionId': str(session_id),
                        'created_at': datetime.utcnow()
                    }

                    mongo.db.predictions.insert_one(new_prediction)

                shutil.rmtree(user_audio_files_dir)

            return jsonify({'message': "Prediction saved successfully"}), 200

    @common_bp.route('/common/session-prediction-results/<session_id>', methods=['GET'])
    @jwt_required()
    def getSessionPredictionResults(session_id):
        current_user = get_jwt_identity()
        user = mongo.db.users.find_one({'username': current_user})

        if not user:
            return jsonify({'error': 'user not found'}), 404

        predictionList = list(mongo.db.predictions.find(
            {'activitySessionId': str(session_id)}, {
                '_id': 1, 'filename': 1,
                'audioFileId': 1,
                'modalId': 1,
                'totalFiles': 1,
                'fluency': 1,
                'disfluency': 1,
                'naturalPause': 1,
                'interjection': 1,
                'noSpeech': 1,
                'music': 1,
                'createdDate': 1
            }))

        if not predictionList:
            return jsonify({'message': 'No Prediction found'}), 404

        formatted_predictionList = []
        for prediction in predictionList:
            modal = mongo.db.modal.find_one(
                {'_id': ObjectId(prediction['modalId'])})

            modal['_id'] = str(modal['_id'])

            audioFile = mongo.db.audioFiles.find_one(
                {'_id': ObjectId(prediction['audioFileId'])})

            audioFile['_id'] = str(audioFile['_id'])

            formatted_prediction = {
                '_id': str(prediction['_id']),
                'modal': modal,
                'audioFile': audioFile,
                'totalFiles': str(prediction['totalFiles']),
                'fluency': prediction['fluency'],
                'disfluency': prediction['disfluency'],
                'naturalPause': prediction['naturalPause'],
                'interjection': prediction['interjection'],
                'noSpeech': prediction['noSpeech'],
                'music': prediction['music'],
                'createdDate': prediction.get('createdDate'),

            }

            formatted_predictionList.append(formatted_prediction)

        return jsonify({'results': formatted_predictionList}), 200

# ------------------------------------------ Dialog -------------------------------------------------------#

    @common_bp.route('/common/dialogue/<option>', methods=['GET'])
    @jwt_required()
    def getDialogue(option):
        current_user = get_jwt_identity()
        user = mongo.db.users.find_one({'username': current_user})

        if not user:
            return jsonify({'error': 'user not found'}), 404

        existing_activityTheme = mongo.db.activityTheme.find_one(
            {'_id': ObjectId(option)})

        if not existing_activityTheme:
            return jsonify({'error': 'Theme not found'}), 404

        friend = ["Alice", "Sophia", "Emma", "Olivia", "Ava",
                  "Isabella", "Mia", "Charlotte", "Amelia", "Harper"]
        friend_name = random.choice(friend)

        # Calculate the timestamp for 8 hours ago
        eight_hours_ago = datetime.utcnow() - timedelta(hours=8)

        existing_dialogue = mongo.db.dialogue.find_one({
            'user_id': str(user['_id']),
            'activityTheme_id': ObjectId(option),
            'created_at': {'$gte': eight_hours_ago}
        })

        if existing_dialogue:
            existing_dialogue['activityTheme'] = existing_activityTheme
            existing_dialogue['_id'] = str(existing_dialogue['_id'])
            existing_dialogue['user_id'] = str(existing_dialogue['user_id'])
            existing_dialogue['activityTheme_id'] = str(
                existing_dialogue['activityTheme_id'])
            existing_activityTheme['_id'] = str(existing_activityTheme['_id'])
            return jsonify(existing_dialogue), 200
        else:
            # Generate new feedback
            feedback = generate_practice_dialogue(
                existing_activityTheme['theme'], current_user, friend_name)

            new_dialogue = {
                'user_id': str(user['_id']),
                'activityTheme_id': ObjectId(option),
                'feedback': feedback,
                'friend_name': friend_name,
                'created_at': datetime.utcnow()
            }

            inserted_id = mongo.db.dialogue.insert_one(
                new_dialogue).inserted_id
            new_dialogue['_id'] = str(inserted_id)
            new_dialogue['user_id'] = str(new_dialogue['user_id'])
            new_dialogue['activityTheme_id'] = str(
                new_dialogue['activityTheme_id'])
            existing_activityTheme['_id'] = str(existing_activityTheme['_id'])
            new_dialogue['activityTheme'] = existing_activityTheme

            return jsonify(new_dialogue), 200
