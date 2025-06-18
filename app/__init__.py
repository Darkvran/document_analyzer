from flask import Flask
from flasgger import Swagger
from app.routes import register_blueprints
from flask_login import LoginManager
from app.data import User, database
from bson import ObjectId
from app.config import FLASK_SECRET_KEY

# Описание инициализации Flask приложения
def create_app():
    app = Flask(__name__)
    app.config["SWAGGER"] = {"title": "TF-IDF API", "uiversion": 3}
    app.secret_key = FLASK_SECRET_KEY

    Swagger(app)

    login = LoginManager()

    @login.user_loader
    def load_user(user_id):
        try:
            user_data = database.users.find_one({"_id": ObjectId(user_id)})
            if user_data:
                return User(user_data["_id"], user_data["username"])
        except Exception as e:
            print(f"[load_user error] {e}")
        return None

    login.init_app(app)

    register_blueprints(app)  # Регистрация всех возможных endpoints (api, pages)

    return app
