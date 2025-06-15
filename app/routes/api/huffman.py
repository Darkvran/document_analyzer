from flask import Blueprint, jsonify, abort
from flasgger import swag_from
from collections import Counter
from bson import ObjectId
import heapq
from app.data import database
from flask_login import login_required, current_user

api_huffman_bp = Blueprint("huffman", __name__)


class Node:
    def __init__(self, char=None, freq=0):
        self.char = char
        self.freq = freq
        self.left = None
        self.right = None

    def __lt__(self, other):
        return self.freq < other.freq


def build_huffman_tree(freq_map):
    heap = [Node(char, freq) for char, freq in freq_map.items()]
    heapq.heapify(heap)

    while len(heap) > 1:
        left = heapq.heappop(heap)
        right = heapq.heappop(heap)
        merged = Node(freq=left.freq + right.freq)
        merged.left = left
        merged.right = right
        heapq.heappush(heap, merged)

    return heap[0] if heap else None


def generate_codes(node, prefix="", code_map=None):
    if code_map is None:
        code_map = {}
    if node is not None:
        if node.char is not None:
            code_map[node.char] = prefix
        generate_codes(node.left, prefix + "0", code_map)
        generate_codes(node.right, prefix + "1", code_map)
    return code_map


def huffman_encode(text):
    if not text:
        return "", {}

    freq_map = Counter(text)
    root = build_huffman_tree(freq_map)
    code_map = generate_codes(root)

    encoded = "".join(code_map[char] for char in text)
    return encoded, code_map


@api_huffman_bp.route("/api/documents/<document_id>/huffman", methods=["GET"])
@login_required
@swag_from(
    {
        "tags": ["Huffman"],
        "summary": "Получить Хаффман-кодирование документа",
        "description": "Кодирует содержимое документа с помощью алгоритма Хаффмана.",
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
                "description": "Успешное кодирование",
                "schema": {
                    "type": "object",
                    "properties": {
                        "encoded": {"type": "string"},
                        "code_map": {
                            "type": "object",
                            "additionalProperties": {"type": "string"},
                        },
                    },
                },
            },
            400: {"description": "Некорректный ID или ошибка обработки"},
            404: {"description": "Документ не найден или доступ запрещён"},
            401: {
                "description": "Ошибка доступа. Для данной команды необходима авторизация."
            },
        },
    }
)
def document_huffman(document_id):
    try:
        doc = database.documents.find_one(
            {"_id": ObjectId(document_id), "user_id": ObjectId(current_user.id)}
        )

        if not doc:
            abort(404, description="Документ не найден или доступ запрещён")

        content = doc.get("content", "")
        encoded, code_map = huffman_encode(content)

        return jsonify({"encoded": encoded, "code_map": code_map})
    except Exception as e:
        abort(400, description="Некорректный ID или ошибка обработки")
