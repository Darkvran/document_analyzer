from flask import Blueprint, jsonify, request
from flasgger import swag_from
import hashlib
from bson import ObjectId
from app.data import database
from flask_login import login_required, current_user, logout_user

api_user_bp = Blueprint("api_user", __name__)


@api_user_bp.route("/api/user/<user_id>", methods=["PATCH"])
@login_required 
@swag_from({
    'tags': ['User'],
    'summary': 'Обновить пароль пользователя',
    'parameters': [
        {
            'name': 'user_id',
            'in': 'path',
            'required': True,
            'type': 'string',
            'description': 'ID пользователя'
        },
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'password': {'type': 'string'}
                },
                'required': ['password']
            }
        }
    ],
    'responses': {
        200: {'description': 'Пароль успешно обновлён'},
        400: {'description': 'Некорректный ID пользователя'},
        403: {'description': 'Нет прав'},
        404: {'description': 'Пользователь не найден'},
        401: {'description': 'Ошибка доступа. Для данной команды необходима авторизация.'}
    }
})
def update_password(user_id):
    try:
        user_oid = ObjectId(user_id)
    except:
        return jsonify({"error": "Invalid user ID"}), 400

    if str(current_user.id) != user_id:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json()
    new_password = data.get("password")

    hashed_password = hashlib.sha256(new_password.encode()).hexdigest()

    result = database.users.update_one(
        {"_id": user_oid},
        {"$set": {"h_password": hashed_password}}
    )

    if result.matched_count == 0:
        return jsonify({"error": "User not found"}), 404

    return jsonify({"message": "Password updated successfully"}), 200

@api_user_bp.route("/api/user/<user_id>", methods=["DELETE"])
@login_required
@swag_from({
    'tags': ['User'],
    'summary': 'Удалить пользователя и все его данные',
    'parameters': [
        {
            'name': 'user_id',
            'in': 'path',
            'required': True,
            'type': 'string',
            'description': 'ID пользователя'
        }
    ],
    'responses': {
        200: {'description': 'Пользователь и все данные удалены'},
        400: {'description': 'Некорректный ID пользователя'},
        403: {'description': 'Нет прав'},
        404: {'description': 'Пользователь не найден'},
        401: {'description': 'Ошибка доступа. Для данной команды необходима авторизация.'}
    }
})
def delete_user(user_id):
    try:
        user_oid = ObjectId(user_id)
    except:
        return jsonify({"error": "Invalid user ID"}), 400

    if str(current_user.id) != str(user_id):
        return jsonify({"error": "Unauthorized"}), 403

    result = database.users.delete_one({"_id": user_oid})
    if result.deleted_count == 0:
        return jsonify({"error": "User not found"}), 404


    database.collections.delete_many({"user_id": user_oid})

    database.documents.delete_many({"user_id": user_oid})

    logout_user()

    response = jsonify({"message": "User and all data deleted successfully"})
    response.delete_cookie("access_token")  

    return response, 200

@api_user_bp.route("/api/logout")
@login_required
@swag_from({
    'tags': ['User'],
    'summary': 'Выход пользователя',
    'responses': {
        200: {'description': 'Успешный выход пользователя'},
        401: {'description': 'Ошибка доступа. Для данной команды необходима авторизация.'}
    }
})
def logout():
    logout_user()
    response = jsonify({"message": "Logout succesful"})
    response.delete_cookie("access_token")  
    return response, 200