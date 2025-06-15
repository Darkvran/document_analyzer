from flask import Blueprint, jsonify, abort
from flasgger import swag_from
from bson import ObjectId
from app.data import database
from flask_login import login_required, current_user

api_documents_bp = Blueprint("api_documents", __name__)


@api_documents_bp.route("/api/documents/", methods=["GET"])
@login_required
@swag_from(
    {
        "tags": ["Documents"],
        "summary": "Получить список документов пользователя",
        "description": "Возвращает список всех загруженных пользователем документов.",
        "responses": {
            200: {
                "description": "Список документов",
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "title": {"type": "string"},
                        },
                    },
                },
            },
            404: {"description": "Документ не найден или доступ запрещён"},
            401: {
                "description": "Ошибка доступа. Для данной команды необходима авторизация."
            },
        },
    }
)
def get_user_documents():
    documents = database.documents.find({"user_id": ObjectId(current_user.id)})
    result = [{"id": str(doc["_id"]), "title": doc["filename"]} for doc in documents]
    return jsonify(result)


@api_documents_bp.route("/api/documents/<document_id>", methods=["GET"])
@login_required
@swag_from(
    {
        "tags": ["Documents"],
        "summary": "Получить содержимое документа",
        "description": "Возвращает текстовое содержимое конкретного документа пользователя.",
        "parameters": [
            {
                "name": "document_id",
                "in": "path",
                "required": True,
                "type": "string",
                "description": "ID документа",
            }
        ],
        "responses": {
            200: {
                "description": "Содержимое документа",
                "schema": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "title": {"type": "string"},
                        "content": {"type": "string"},
                    },
                },
            },
            400: {"description": "Некорректный ID документа"},
            404: {"description": "Документ не найден или доступ запрещён"},
            401: {
                "description": "Ошибка доступа. Для данной команды необходима авторизация"
            },
        },
    }
)
def get_document_content(document_id):
    try:
        doc = database.documents.find_one(
            {"_id": ObjectId(document_id), "user_id": ObjectId(current_user.id)}
        )
        if not doc:
            abort(404, description="Документ не найден или доступ запрещён")

        return jsonify(
            {"id": str(doc["_id"]), "title": doc["filename"], "content": doc["content"]}
        )
    except Exception:
        abort(400, description="Некорректный ID документа")


@api_documents_bp.route("/api/documents/<document_id>/statistics", methods=["GET"])
@login_required
@swag_from(
    {
        "tags": ["Documents"],
        "summary": "Получить TF/IDF статистику по документу",
        "description": "Возвращает список слов с их TF, IDF.",
        "parameters": [
            {
                "name": "document_id",
                "in": "path",
                "required": True,
                "type": "string",
                "description": "ID документа",
            }
        ],
        "responses": {
            200: {
                "description": "Статистика документа",
                "schema": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "filename": {"type": "string"},
                        "statistics": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "term": {"type": "string"},
                                    "tf": {"type": "number"},
                                    "idf": {"type": "number"},
                                    "tf_idf": {"type": "number"},
                                },
                            },
                        },
                    },
                },
            },
            400: {"description": "Некорректный ID документа"},
            404: {"description": "Документ не найден или доступ запрещён"},
            401: {
                "description": "Ошибка доступа. Для данной команды необходима авторизация."
            },
        },
    }
)
def get_document_statistics(document_id):
    try:
        doc = database.documents.find_one(
            {"_id": ObjectId(document_id), "user_id": ObjectId(current_user.id)}
        )
        if not doc:
            abort(404, description="Документ не найден или доступ запрещён")
        words = doc.get("words", [])
        sorted_words = sorted(words, key=lambda x: x.get("idf", 0), reverse=True)
        return jsonify(
            {
                "id": str(doc["_id"]),
                "filename": doc["filename"],
                "statistics": sorted_words,
            }
        )
    except Exception:
        abort(400, description="Некорректный ID документа")
