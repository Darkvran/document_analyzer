import os
import time
from flask import Flask, flash, request, redirect, render_template, jsonify
from werkzeug.utils import secure_filename
from handling import file_handling
from metric import MetricsCollector
from dotenv import load_dotenv

load_dotenv()

ALLOWED_EXTENSIONS = os.getenv("APP_ALLOWED_EXTENSIONS")
VERSION = os.getenv("APP_VERSION")

metrics = MetricsCollector()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

app = Flask(__name__)
app.config['SESSION_TYPE'] = 'filesystem'
app.secret_key = os.getenv("FLASK_SECRET_KEY")

@app.route("/", methods=["GET", "POST"])
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
            start = time.time()
            words_data = file_handling(content, filename)
            duration = round(time.time() - start, 3)
            metrics.register_file_processed(duration)
            return render_template("index.html", words=words_data, filename=filename)
        else:
            flash("Forbidden file extension")
            return redirect(request.url)

    return render_template('index.html')

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