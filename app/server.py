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
    return render_template('collections.html', collections=user_collections, message=message)

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
        user = {"username": request.form["username"], "email": request.form["email"], "h_password": hashlib.sha256(request.form['password'].encode()).hexdigest(), "collections": []}
        database.users.insert_one(user)
        flash("Успешная регистрация! Теперь вы можете войти в свой аккаунт.")
        return render_template('register.html')
    return render_template("register.html")


@app.route("/status")
def status():
    return jsonify({"status": "OK"})

@app.route("/metrics")
def metrics_endpoint():
    return jsonify(metrics.get_metrics())

@app.route("/version")
def version():
    return jsonify({"version": VERSION})

if __name__ == "__main__":
    app.run(host=os.getenv("FLASK_HOST"), port=os.getenv("FLASK_PORT"), debug=os.getenv("FLASK_DEBUG"))