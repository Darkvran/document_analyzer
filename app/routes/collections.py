from flask import Blueprint, abort, request, flash, render_template, redirect
from bson import ObjectId
from app.data import database
from flask_login import login_required, current_user
import os, time, chardet
from dotenv import load_dotenv
from app.metric import MetricsCollector
from werkzeug.utils import secure_filename
from app.handling import file_handling



load_dotenv()

collections_bp = Blueprint("collections_bp", __name__)

ALLOWED_EXTENSIONS = os.getenv("APP_ALLOWED_EXTENSIONS")
VERSION = os.getenv("APP_VERSION")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@collections_bp.route("/collections", methods=["GET", "POST"])
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
                    {"$push": {"collection_ids": insert_res.inserted_id}}
                )
                flash('Коллекция успешно создана!')

    user_collections = list(database.collections.find({"user_id": current_user.id}))
    return render_template('collections.html', collections=user_collections)


@collections_bp.route("/collections/<collection_id>/documents", methods=["GET", "POST"])
@login_required
def documents(collection_id: str):
    collection = database.collections.find_one({"_id":ObjectId(collection_id)})
    if not collection or collection['user_id'] != current_user.id:
        abort(403)
    collection_documents = list(database.documents.find({"collection_id": ObjectId(collection_id)}))
    return render_template('documents.html', collection=collection, documents=collection_documents)


@collections_bp.route("/collections/<collection_id>/delete", methods=['GET', 'POST'])
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
        {"$pull": {"collection_ids": ObjectId(collection_id)}}
    )

    return render_template('collections.html', collections=user_collections)


@collections_bp.route("/collections/<collection_id>/upload", methods=["GET", "POST"])
@login_required
def upload(collection_id):
    metrics = MetricsCollector()
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