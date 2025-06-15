from flask import request, jsonify, Blueprint
from flasgger import swag_from
from app.data import database, User
import hashlib, re
from flask_login import login_user

api_auth_bp = Blueprint("api_auth", __name__)

@api_auth_bp.route("/api/login", methods=["POST"])
@swag_from({
    'tags': ['Auth'],
    'summary': 'Вход пользователя',
    'description': 'Аутентификация по email и паролю. Устанавливает сессию.',
    'consumes': ['application/json'],
    'parameters': [
        {
            'in': 'body',
            'name': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['email', 'password'],
                'properties': {
                    'email': {'type': 'string'},
                    'password': {'type': 'string'}
                }
            }
        }
    ],
    'responses': {
        200: {
            'description': 'Успешный вход',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'},
                    'user_id': {'type': 'string'}
                }
            }
        },
        400: {'description': 'Логин и пароль обязательны'},
        401: {'description': 'Неверный логин или пароль'}
    }
})
def api_login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Логин и пароль обязательны"}), 400

    user_data = database.users.find_one({"email": email})
    if not user_data or not (hashlib.sha256(password.encode()).hexdigest() == user_data["h_password"]):
        return jsonify({"error": "Неверный логин или пароль"}), 401
    user = User(user_data['_id'], user_data['username'], user_data['collection_ids'])
    login_user(user)

    return jsonify({"message": "Успешный вход", "user_id": str(user.id)})

def is_valid_email(email):
    return re.match(r"^[\w\.-]+@[\w\.-]+\.\w{2,}$", email)

@api_auth_bp.route("/api/register", methods=["POST"])
@swag_from({
    'tags': ['Auth'],
    'summary': 'Регистрация пользователя',
    'description': 'Создание нового пользователя с email, логином и паролем.',
    'consumes': ['application/json'],
    'parameters': [
        {
            'in': 'body',
            'name': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['username', 'password'],
                'properties': {
                    'email': {'type': 'string'},
                    'username': {'type': 'string'},
                    'password': {'type': 'string'}
                }
            }
        }
    ],
    'responses': {
        200: {
            'description': 'Пользователь успешно зарегистрирован',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'},
                    'user_id': {'type': 'string'}
                }
            }
        },
        400: {
            'description': 'Ошибка ввода или пользователь уже существует',
            'schema': {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'}
                }
            }
        }
    }
})
def api_register():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    email = data.get("email")

    if not username or not password or not email:
        return jsonify({"error": "Имя пользователя, пароль и email обязательны"}), 400

    if not is_valid_email(email):
        return jsonify({"error": "Некорректный формат email"}), 400

    if database.users.find_one({"username": username}):
        return jsonify({"error": "Пользователь с таким именем уже существует"}), 400

    if database.users.find_one({"email": email}):
        return jsonify({"error": "Пользователь с таким email уже существует"}), 400

    new_user = {
        "email": email,
        "username": username,
        "h_password": hashlib.sha256(password.encode()).hexdigest(),
        "collection_ids": []
    }

    result = database.users.insert_one(new_user)
    return jsonify({"message": "Пользователь успешно зарегистрирован", "user_id": str(result.inserted_id)})