from flask import Blueprint, jsonify, abort
from bson import ObjectId
from app.data import database
from flask_login import login_required, current_user

api_documents_bp = Blueprint("api_documents", __name__)

@api_documents_bp.route("/api/documents/", methods=["GET"])
@login_required
def get_user_documents():
    documents = database.documents.find({"user_id": ObjectId(current_user.id)})
    result = [{"id": str(doc["_id"]), "title": doc["filename"]} for doc in documents]
    return jsonify(result)

@api_documents_bp.route("/api/documents/<document_id>", methods=["GET"])
@login_required
def get_document_content(document_id):
    try:
        doc = database.documents.find_one({
            "_id": ObjectId(document_id),
            "user_id": ObjectId(current_user.id)
        })
        if not doc:
            abort(404, description="Документ не найден или доступ запрещён")

        return jsonify({
            "id": str(doc["_id"]),
            "title": doc["filename"],
            "content": doc["content"]
        })
    except Exception:
        abort(400, description="Некорректный ID документа")

@api_documents_bp.route("/api/documents/<document_id>/statistics", methods=["GET"])
@login_required
def get_document_statistics(document_id):
    try:
        doc = database.documents.find_one({
            "_id": ObjectId(document_id),
            "user_id": ObjectId(current_user.id)
        })
        if not doc:
            abort(404, description="Документ не найден или доступ запрещён")
        words = doc.get("words", [])
        sorted_words = sorted(words, key=lambda x: x.get("idf", 0), reverse=True)
        return jsonify({
            "id": str(doc["_id"]),
            "filename": doc["filename"],
            "statistics": sorted_words
        })
    except Exception:
        abort(400, description="Некорректный ID документа")
