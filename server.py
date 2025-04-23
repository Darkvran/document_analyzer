import os
from flask import Flask, flash, request, redirect, render_template
from werkzeug.utils import secure_filename
from handling import file_handling

ALLOWED_EXTENSIONS = {'txt'}
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

app = Flask(__name__)
app.config['SESSION_TYPE'] = 'filesystem'
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev_fallback_key')

@app.route("/", methods = ["GET", "POST"])
def index():
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
            content = file.read().decode('cp1251')
            words_data = file_handling(content, filename)
            return render_template("index.html", words=words_data, filename=filename)
    return render_template('index.html')