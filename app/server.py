import os
import time
from flask import Flask, flash, request, redirect, render_template, jsonify, url_for, abort
from werkzeug.utils import secure_filename
from handling import file_handling
from metric import MetricsCollector
from dotenv import load_dotenv
from flask_login import LoginManager, login_required, current_user, login_user, logout_user
from data import database, User
import chardet, hashlib
from bson import ObjectId
from collections import Counter, defaultdict
import heapq

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

ALLOWED_EXTENSIONS = os.getenv("APP_ALLOWED_EXTENSIONS")
VERSION = os.getenv("APP_VERSION")

metrics = MetricsCollector()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

app = Flask(__name__)
app.config['SESSION_TYPE'] = 'filesystem'
app.secret_key = os.getenv("FLASK_SECRET_KEY")
login = LoginManager(app)

@login.user_loader
def load_user(user_id):
    try:
        user_data = database.users.find_one({'_id': ObjectId(user_id)})
        if user_data:
            return User(user_data['_id'], user_data['username'])
    except Exception as e:
        print(f"[load_user error] {e}")
    return None

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

class Node:
    def __init__(self, char=None, freq=0):
        self.char = char
        self.freq = freq
        self.left = None
        self.right = None

    # сравнение для heapq
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

def generate_codes(node, prefix='', code_map=None):
    if code_map is None:
        code_map = {}
    if node is not None:
        if node.char is not None:
            code_map[node.char] = prefix
        generate_codes(node.left, prefix + '0', code_map)
        generate_codes(node.right, prefix + '1', code_map)
    return code_map

def huffman_encode(text):
    if not text:
        return '', {}

    freq_map = Counter(text)
    root = build_huffman_tree(freq_map)
    code_map = generate_codes(root)

    encoded = ''.join(code_map[char] for char in text)
    return encoded, code_map

@app.route("/api/documents/<document_id>/huffman", methods=["GET"])
@login_required
def document_huffman(document_id):
    try:
        doc = database.documents.find_one({
            "_id": ObjectId(document_id),
            "user_id": ObjectId(current_user.id)
        })

        if not doc:
            abort(404, description="Документ не найден или доступ запрещён")

        content = doc.get("content", "")
        encoded, code_map = huffman_encode(content)

        return jsonify({
            "encoded": encoded,
            "code_map": code_map
        })
    except Exception as e:
        abort(400, description="Некорректный ID или ошибка обработки")

@app.route("/api/documents/", methods=["GET"])
@login_required
def get_user_documents():
    documents = database.documents.find({"user_id": ObjectId(current_user.id)})
    result = [{"id": str(doc["_id"]), "title": doc["filename"]} for doc in documents]
    return jsonify(result)

@app.route("/api/documents/<document_id>", methods=["GET"])
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

@app.route("/api/documents/<document_id>/statistics", methods=["GET"])
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

@app.route("/api/collections", methods=["GET"])
@login_required
def get_collections():
    collections = list(database.collections.find({"user_id": ObjectId(current_user.id)}))
    
    result = []
    for col in collections:
        doc_ids = col.get("doc_ids", [])
        documents = database.documents.find({"_id": {"$in": doc_ids}})
        document_list = [{"id": str(doc["_id"]), "filename": doc["filename"]} for doc in documents]

        result.append({
            "id": str(col["_id"]),
            "name": col.get("name", ""),
            "documents": document_list
        })

    return jsonify(result)

@app.route("/api/collections/<collection_id>", methods=["GET"])
@login_required
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

@app.route("/api/collections/<collection_id>/statistics", methods=["GET"])
@login_required
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
            freq = word_entry["tf"] * doc["words_num"]  # Преобразуем tf обратно в абсолютную частоту
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
        result.append({
            "word": word,
            "tf": round(tf, 4),
            "idf": round(idf, 4)
        })

    # Сортировка по IDF убыванию
    result.sort(key=lambda x: x["idf"], reverse=True)

    return jsonify({"statistics": result})


@app.route("/api/collection/<collection_id>/<document_id>", methods=["POST"])
@login_required
def add_document_to_collection(collection_id, document_id):
    try:
        collection = database.collections.find_one({"_id": ObjectId(collection_id)})
        document = database.documents.find_one({"_id": ObjectId(document_id)})
    except:
        abort(400, description="Некорректный ID")

    if not collection or not document:
        abort(404, description="Коллекция или документ не найдены")

    if collection["user_id"] != ObjectId(current_user.id) or document["user_id"] != ObjectId(current_user.id):
        abort(403, description="Нет доступа")

    # Обновляем документ
    database.documents.update_one(
        {"_id": ObjectId(document_id)},
        {"$set": {"collection_id": ObjectId(collection_id)}}
    )

    # Добавляем ID документа в коллекцию
    database.collections.update_one(
        {"_id": ObjectId(collection_id)},
        {"$addToSet": {"doc_ids": ObjectId(document_id)}}
    )

    return jsonify({"message": "Документ добавлен в коллекцию"})

@app.route("/api/collection/<collection_id>/<document_id>", methods=["DELETE"])
@login_required
def remove_document_from_collection(collection_id, document_id):
    try:
        collection = database.collections.find_one({"_id": ObjectId(collection_id)})
        document = database.documents.find_one({"_id": ObjectId(document_id)})
    except:
        abort(400, description="Некорректный ID")

    if not collection or not document:
        abort(404, description="Коллекция или документ не найдены")

    if collection["user_id"] != ObjectId(current_user.id) or document["user_id"] != ObjectId(current_user.id):
        abort(403, description="Нет доступа")

    # Удаляем ссылку на коллекцию из документа
    database.documents.update_one(
        {"_id": ObjectId(document_id)},
        {"$unset": {"collection_id": ""}}
    )

    # Удаляем ID документа из коллекции
    database.collections.update_one(
        {"_id": ObjectId(collection_id)},
        {"$pull": {"doc_ids": ObjectId(document_id)}}
    )

    return jsonify({"message": "Документ удалён из коллекции"})

@app.route("/api/login", methods=["POST"])
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

@app.route("/api/register", methods=["POST"])
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

@app.route("/api/user/<user_id>", methods=["PATCH"])
@login_required  # если используешь проверку токена
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

@app.route("/api/user/<user_id>", methods=["DELETE"])
@login_required
def delete_user(user_id):
    try:
        user_oid = ObjectId(user_id)
    except:
        return jsonify({"error": "Invalid user ID"}), 400

    # Проверка авторизации
    if str(current_user.id) != str(user_id):
        return jsonify({"error": "Unauthorized"}), 403

    # Удаление пользователя
    result = database.users.delete_one({"_id": user_oid})
    if result.deleted_count == 0:
        return jsonify({"error": "User not found"}), 404

    # Удаление коллекций пользователя
    database.collections.delete_many({"user_id": user_oid})

    # Удаление документов пользователя
    database.documents.delete_many({"user_id": user_oid})

    # Завершение сессии
    logout_user()

    response = jsonify({"message": "User and all data deleted successfully"})
    response.delete_cookie("access_token")  # если хранишь токен в cookie

    return response, 200

@app.route("/collections", methods=["GET", "POST"])
@login_required
def collections():
    if request.method == 'POST':
        if '' in request.form.values():
            flash('Пожалуйста, введите имя коллекции')
        else:
            name = request.form['collection_name'].strip()
            existing_collection = database.collections.find_one({
                "user_id": current_user.id,
                "name": name
            })
            if existing_collection:
                flash('Данная коллекция уже существует')
            else:
                collection = {
                    "user_id": current_user.id,
                    "name": name,
                    "doc_ids": []
                }
                insert_res = database.collections.insert_one(collection)
                database.users.update_one(
                    {"_id": ObjectId(current_user.id)},
                    {"$push": {"collections": insert_res.inserted_id}}
                )
                flash('Коллекция успешно создана!')

    user_collections = list(database.collections.find({"user_id": current_user.id}))
    return render_template('collections.html', collections=user_collections)

@app.route("/collections/<collection_id>/documents", methods=["GET", "POST"])
@login_required
def documents(collection_id: str):
    collection = database.collections.find_one({"_id":ObjectId(collection_id)})
    if not collection or collection['user_id'] != current_user.id:
        abort(403)
    collection_documents = list(database.documents.find({"collection_id": ObjectId(collection_id)}))
    return render_template('documents.html', collection=collection, documents=collection_documents)

@app.route("/collections/<collection_id>/delete", methods=['GET', 'POST'])
@login_required
def delete_collection(collection_id):
    collection = database.collections.find_one({"_id":ObjectId(collection_id)})
    if not collection or collection['user_id'] != current_user.id:
        abort(403)
    result = database.collections.delete_one({
        "_id": ObjectId(collection_id),
        "user_id": current_user.id
    })
    if result.deleted_count:
        flash("Коллекция удалена")
    else:
        flash("Коллекция не найдена")
    user_collections = list(database.collections.find({"user_id": current_user.id}))
    database.users.update_one(
        {"_id": ObjectId(current_user.id)},
        {"$pull": {"collections": ObjectId(collection_id)}}
    )
    return render_template('collections.html', collections=user_collections)

@app.route("/collections/<collection_id>/upload", methods=["GET", "POST"])
@login_required
def upload(collection_id):
    collection = database.collections.find_one({"_id":ObjectId(collection_id)})

    if not collection or collection['user_id'] != current_user.id:
        abort(403)
    
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            raw_data = file.read()
            encoding = chardet.detect(raw_data)['encoding']
            if encoding is None:
                encoding = 'utf-8' 
            content = raw_data.decode(encoding)
            start = time.time()
            words_data = file_handling(content, filename, collection_id, current_user.id)
            duration = round(time.time() - start, 3)
            metrics.register_file_processed(duration)
            return render_template("upload.html", words=words_data, filename=filename, collection_name = collection["name"])
        else:
            flash("Forbidden file extension")
            return redirect(request.url)

    return render_template('upload.html', collection_name = collection["name"])

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
             return redirect(url_for("index"))
    if request.method == 'POST':
        if '' in request.form.values():
            flash('Пожалуйста, заполните все поля')
            return render_template('login.html')
        existing_user = database.users.find_one({"email": request.form['email']})
        if existing_user:
            if hashlib.sha256(request.form['password'].encode()).hexdigest() == existing_user["h_password"]:
                user = User(existing_user['_id'], existing_user['username'], existing_user['collections'])
                login_user(user)
                return redirect(url_for("index"))
        else:
            flash("Ошибка аутентификации")
            return render_template("login.html")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
             return redirect(url_for("index"))
    if request.method == 'POST':
        if '' in request.form.values():
            flash('Пожалуйста, заполните все поля')
            return render_template('register.html')
        elif request.form['password'] != request.form['password_repeat']:
            flash("Неверный повтор пароля")
            return render_template('register.html')
        existing_user = database.users.find_one({"username": request.form['username']}) or database.users.find_one({"email": request.form['email']})
        if existing_user:
            if existing_user['email'] == request.form['email']:
                flash('Этот адрес занят')
                return render_template('register.html')
            if existing_user['username'] == request.form['username']:
                flash('Этот ник занят')
                return render_template('register.html')
        user = {"username": request.form["username"], "email": request.form["email"], "h_password": hashlib.sha256(request.form['password'].encode()).hexdigest(), "collection_ids": []}
        database.users.insert_one(user)
        flash("Успешная регистрация! Теперь вы можете войти в свой аккаунт.")
        return render_template('register.html')
    return render_template("register.html")


@app.route("/api/status")
def status():
    return jsonify({"status": "OK"})

@app.route("/api/metrics")
def metrics_endpoint():
    return jsonify(metrics.get_metrics())

@app.route("/api/version")
def version():
    return jsonify({"version": VERSION})

if __name__ == "__main__":
    app.run(host=os.getenv("FLASK_HOST"), port=os.getenv("FLASK_PORT"), debug=os.getenv("FLASK_DEBUG"))