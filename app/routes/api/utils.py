from flask import Blueprint, jsonify
from flasgger import swag_from
from app.metric import MetricsCollector
from dotenv import load_dotenv
import os

metrics = MetricsCollector()

load_dotenv()

api_utils_bp = Blueprint("api_utils_bp", __name__)

ALLOWED_EXTENSIONS = os.getenv("APP_ALLOWED_EXTENSIONS")


@api_utils_bp.route("/api/status")
@swag_from(
    {
        "tags": ["Utils"],
        "summary": "Проверка статуса API",
        "responses": {
            200: {
                "description": "API работает",
                "schema": {
                    "type": "object",
                    "properties": {"status": {"type": "string", "example": "OK"}},
                },
            }
        },
    }
)
def status():
    return jsonify({"status": "OK"})


@api_utils_bp.route("/api/metrics")
@swag_from(
    {
        "tags": ["Utils"],
        "summary": "Метрики системы",
        "responses": {
            200: {
                "description": "Возвращает собранные метрики",
                "schema": {
                    "type": "object",
                    "additionalProperties": {"type": "number"},
                },
            }
        },
    }
)
def metrics_endpoint():
    return jsonify(metrics.get_metrics())


@api_utils_bp.route("/api/version")
@swag_from(
    {
        "tags": ["Utils"],
        "summary": "Версия приложения",
        "responses": {
            200: {
                "description": "Актуальная версия приложения",
                "schema": {
                    "type": "object",
                    "properties": {"version": {"type": "string", "example": "1.0.0"}},
                },
            }
        },
    }
)
def version():
    return jsonify({"version": "2.1.0"})
