from flask import Blueprint, jsonify
from app.metric import MetricsCollector
from dotenv import load_dotenv
import os

metrics = MetricsCollector()

load_dotenv()

api_utils_bp = Blueprint("api_utils_bp", __name__)

ALLOWED_EXTENSIONS = os.getenv("APP_ALLOWED_EXTENSIONS")
VERSION = os.getenv("APP_VERSION")


@api_utils_bp.route("/api/status")
def status():
    return jsonify({"status": "OK"})

@api_utils_bp.route("/api/metrics")
def metrics_endpoint():
    return jsonify(metrics.get_metrics())

@api_utils_bp.route("/api/version")
def version():
    return jsonify({"version": VERSION})
