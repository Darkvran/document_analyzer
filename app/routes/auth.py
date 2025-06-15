from flask import request, Blueprint, render_template, redirect, url_for, flash
from app.data import database, User
import hashlib
from flask_login import login_user, current_user

auth_bp = Blueprint("auth_bp", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
             return redirect(url_for("index_bp.index"))
    if request.method == 'POST':
        if '' in request.form.values():
            flash('Пожалуйста, заполните все поля')
            return render_template('login.html')
        existing_user = database.users.find_one({"email": request.form['email']})
        if existing_user:
            if hashlib.sha256(request.form['password'].encode()).hexdigest() == existing_user["h_password"]:
                user = User(existing_user['_id'], existing_user['username'], existing_user['collection_ids'])
                login_user(user)
                return redirect(url_for("index_bp.index"))
        else:
            flash("Ошибка аутентификации")
            return render_template("login.html")
    return render_template("login.html")

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
             return redirect(url_for("index_bp.index"))
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