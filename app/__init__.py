from flask import Flask
from app.routes import register_blueprints
import os
from flask_login import LoginManager
from app.data import User, database
from bson import ObjectId

def create_app():
    app = Flask(__name__)
    app.config['SESSION_TYPE'] = 'filesystem'
    app.secret_key = os.getenv("FLASK_SECRET_KEY")

    login = LoginManager()
    @login.user_loader
    def load_user(user_id):
        try:
            user_data = database.users.find_one({'_id': ObjectId(user_id)})
            if user_data:
                return User(user_data['_id'], user_data['username'])
        except Exception as e:
            print(f"[load_user error] {e}")
        return None
    login.init_app(app)

    register_blueprints(app)
    return app