# run.py
from app import create_app
from flask_jwt_extended import JWTManager
import datetime


app = create_app()
jwt = JWTManager(app)

# Set the expiry time for JWT tokens
expires_delta = datetime.timedelta(days=1)
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = expires_delta
app.config['STATIC_FOLDER'] = 'files'

if __name__ == '__main__':
    app.run(host='0.0.0.0')
