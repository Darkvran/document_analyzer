from flask import Blueprint, jsonify, abort
from flasgger import swag_from
from bson import ObjectId
from app.data import database
from flask_login import login_required, current_user
from collections import defaultdict

api_collections_bp = Blueprint("api_collections", __name__)


@api_collections_bp.route("/api/collections", methods=["GET"])
@login_required
@swag_from(
    {
        "tags": ["Collections"],
        "summary": "Получить список коллекций пользователя",
        "description": "Возвращает список всех коллекций пользователя и документы в них.",
        "responses": {
            200: {
                "description": "Список коллекций",
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "name": {"type": "string"},
                            "documents": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "string"},
                                        "filename": {"type": "string"},
                                    },
                                },
                            },
                        },
                    },
                },
            },
            401: {
                "description": "Ошибка доступа. Для данной команды необходима авторизация."
            },
        },
    }
)
def get_collections():
    collections = list(
        database.collections.find({"user_id": ObjectId(current_user.id)})
    )

    result = []
    for col in collections:
        doc_ids = col.get("doc_ids", [])
        documents = database.documents.find({"_id": {"$in": doc_ids}})
        document_list = [
            {"id": str(doc["_id"]), "filename": doc["filename"]} for doc in documents
        ]

        result.append(
            {
                "id": str(col["_id"]),
                "name": col.get("name", ""),
                "documents": document_list,
            }
        )

    return jsonify(result)


@api_collections_bp.route("/api/collections/<collection_id>", methods=["GET"])
@login_required
@swag_from(
    {
        "tags": ["Collections"],
        "summary": "Получить список ID документов в коллекции",
        "parameters": [
            {"name": "collection_id", "in": "path", "required": True, "type": "string"}
        ],
        "responses": {
            200: {
                "description": "Список ID документов",
                "schema": {
                    "type": "object",
                    "properties": {
                        "document_ids": {"type": "array", "items": {"type": "string"}}
                    },
                },
            },
            400: {"description": "Некорректный ID коллекции"},
            403: {"description": "Нет доступа"},
            401: {
                "description": "Ошибка доступа. Для данной команды необходима авторизация."
            },
            404: {"description": "Коллекция не найдена"},
        },
    }
)
def get_collection_documents(collection_id):
    try:
        collection = database.collections.find_one({"_id": ObjectId(collection_id)})
    except:
        abort(400, description="Некорректный ID коллекции")

    if not collection:
        abort(404, description="Коллекция не найдена")

    if collection["user_id"] != ObjectId(current_user.id):
        abort(403, description="Нет доступа к этой коллекции")

    doc_ids = collection.get("doc_ids", [])
    doc_id_strings = [str(doc_id) for doc_id in doc_ids]

    return jsonify({"document_ids": doc_id_strings})


@api_collections_bp.route(
    "/api/collections/<collection_id>/statistics", methods=["GET"]
)
@login_required
@swag_from(
    {
        "tags": ["Collections"],
        "summary": "Получить статистику по коллекции",
        "description": "Вычисляет и возвращает усреднённые TF и IDF значения по всем документам в коллекции.",
        "parameters": [
            {"name": "collection_id", "in": "path", "required": True, "type": "string"}
        ],
        "responses": {
            200: {
                "description": "Статистика коллекции",
                "schema": {
                    "type": "object",
                    "properties": {
                        "statistics": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "word": {"type": "string"},
                                    "tf": {"type": "number"},
                                    "idf": {"type": "number"},
                                },
                            },
                        }
                    },
                },
            },
            400: {"description": "Некорректный ID коллекции"},
            403: {"description": "Нет доступа"},
            401: {
                "description": "Ошибка доступа. Для данной команды необходима авторизация."
            },
            404: {"description": "Коллекция не найдена"},
        },
    }
)
def get_collection_statistics(collection_id):
    try:
        collection = database.collections.find_one({"_id": ObjectId(collection_id)})
    except:
        abort(400, description="Некорректный ID коллекции")

    if not collection:
        abort(404, description="Коллекция не найдена")

    if collection["user_id"] != ObjectId(current_user.id):
        abort(403, description="Нет доступа к этой коллекции")

    doc_ids = collection.get("doc_ids", [])
    if not doc_ids:
        return jsonify({"statistics": []})

    # Суммарный список слов
    total_word_count = 0
    tf_accumulator = defaultdict(int)
    idf_map = {}

    documents = list(database.documents.find({"_id": {"$in": doc_ids}}))

    for doc in documents:
        words = doc.get("words", [])
        total_word_count += doc.get("words_num", 0)

        for word_entry in words:
            word = word_entry["word"]
            freq = (
                word_entry["tf"] * doc["words_num"]
            )  # Преобразуем tf обратно в абсолютную частоту
            tf_accumulator[word] += freq

            # Берем IDF из документа (предполагаем, что одинаково у всех)
            if word not in idf_map:
                idf_map[word] = word_entry.get("idf", 0)

    if total_word_count == 0:
        return jsonify({"statistics": []})

    # Формируем итог
    result = []
    for word, freq in tf_accumulator.items():
        tf = freq / total_word_count
        idf = idf_map.get(word, 0)
        result.append({"word": word, "tf": round(tf, 4), "idf": round(idf, 4)})

    # Сортировка по IDF убыванию
    result.sort(key=lambda x: x["idf"], reverse=True)

    return jsonify({"statistics": result})


@api_collections_bp.route(
    "/api/collections/<collection_id>/<document_id>", methods=["POST"]
)
@login_required
@swag_from(
    {
        "tags": ["Collections"],
        "summary": "Добавить документ в коллекцию",
        "parameters": [
            {"name": "collection_id", "in": "path", "required": True, "type": "string"},
            {"name": "document_id", "in": "path", "required": True, "type": "string"},
        ],
        "responses": {
            200: {"description": "Документ добавлен в коллекцию"},
            400: {"description": "Некорректный ID"},
            403: {"description": "Нет доступа"},
            401: {
                "description": "Ошибка доступа. Для данной команды необходима авторизация."
            },
            404: {"description": "Коллекция или документ не найдены"},
        },
    }
)
def add_document_to_collection(collection_id, document_id):
    try:
        collection = database.collections.find_one({"_id": ObjectId(collection_id)})
        document = database.documents.find_one({"_id": ObjectId(document_id)})
    except:
        abort(400, description="Некорректный ID")

    if not collection or not document:
        abort(404, description="Коллекция или документ не найдены")

    if collection["user_id"] != ObjectId(current_user.id) or document[
        "user_id"
    ] != ObjectId(current_user.id):
        abort(403, description="Нет доступа")

    # Обновляем документ
    database.documents.update_one(
        {"_id": ObjectId(document_id)},
        {"$set": {"collection_id": ObjectId(collection_id)}},
    )

    # Добавляем ID документа в коллекцию
    database.collections.update_one(
        {"_id": ObjectId(collection_id)},
        {"$addToSet": {"doc_ids": ObjectId(document_id)}},
    )

    return jsonify({"message": "Документ добавлен в коллекцию"})


@api_collections_bp.route(
    "/api/collections/<collection_id>/<document_id>", methods=["DELETE"]
)
@login_required
@swag_from(
    {
        "tags": ["Collections"],
        "summary": "Удалить документ из коллекции",
        "parameters": [
            {"name": "collection_id", "in": "path", "required": True, "type": "string"},
            {"name": "document_id", "in": "path", "required": True, "type": "string"},
        ],
        "responses": {
            200: {"description": "Документ удалён из коллекции"},
            400: {"description": "Некорректный ID"},
            403: {"description": "Нет доступа"},
            401: {
                "description": "Ошибка доступа. Для данной команды необходима авторизация."
            },
            404: {"description": "Коллекция или документ не найдены"},
        },
    }
)
def remove_document_from_collection(collection_id, document_id):
    try:
        collection = database.collections.find_one({"_id": ObjectId(collection_id)})
        document = database.documents.find_one({"_id": ObjectId(document_id)})
    except:
        abort(400, description="Некорректный ID")

    if not collection or not document:
        abort(404, description="Коллекция или документ не найдены")

    if collection["user_id"] != ObjectId(current_user.id) or document[
        "user_id"
    ] != ObjectId(current_user.id):
        abort(403, description="Нет доступа")

    # Удаляем ссылку на коллекцию из документа
    database.documents.update_one(
        {"_id": ObjectId(document_id)}, {"$unset": {"collection_id": ""}}
    )

    # Удаляем ID документа из коллекции
    database.collections.update_one(
        {"_id": ObjectId(collection_id)}, {"$pull": {"doc_ids": ObjectId(document_id)}}
    )

    return jsonify({"message": "Документ удалён из коллекции"})
