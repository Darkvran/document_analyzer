from flask import request, jsonify, Blueprint
from app.data import database, User
import hashlib
from flask_login import login_user

api_auth_bp = Blueprint("api_auth", __name__)

@api_auth_bp.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Логин и пароль обязательны"}), 400

    user_data = database.users.find_one({"email": email})
    if not user_data or not (hashlib.sha256(password.encode()).hexdigest() == user_data["h_password"]):
        return jsonify({"error": "Неверный логин или пароль"}), 401
    user = User(user_data['_id'], user_data['username'], user_data['collections'])
    login_user(user)

    return jsonify({"message": "Успешный вход", "user_id": str(user.id)})

@api_auth_bp.route("/api/register", methods=["POST"])
def api_register():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    email = data.get("email")

    if not username or not password:
        return jsonify({"error": "Логин и пароль обязательны"}), 400

    if database.users.find_one({"username": username}):
        return jsonify({"error": "Пользователь с таким именем уже существует"}), 400

    new_user = {
        "email": email,
        "username": username,
        "h_password": hashlib.sha256(password.encode()).hexdigest(),
        "collection_ids": []
    }

    result = database.users.insert_one(new_user)
    return jsonify({"message": "Пользователь успешно зарегистрирован", "user_id": str(result.inserted_id)})