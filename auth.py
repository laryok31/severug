from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from database import db, User, Referral
from datetime import datetime
import hashlib
import re
import base64
from werkzeug.security import generate_password_hash, check_password_hash

auth = Blueprint('auth', __name__)

def hash_password(password):
    """Хеширование пароля с использованием bcrypt-like метода"""
    return generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)

def verify_password(password, hash):
    """Проверка пароля"""
    return check_password_hash(hash, password)

def format_phone(phone):
    """Форматирует номер в формат +7XXXXXXXXXX"""
    digits = re.sub(r'\D', '', phone)

    if len(digits) == 11:
        if digits.startswith('8'):
            return '+7' + digits[1:]
        elif digits.startswith('7'):
            return '+' + digits
    elif len(digits) == 10:
        return '+7' + digits

    return None

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form.get('phone')
        password = request.form.get('password')

        formatted_phone = format_phone(phone)
        if not formatted_phone:
            flash('Введите корректный номер телефона')
            return render_template('login.html')

        user = User.query.filter_by(phone=formatted_phone).first()

        if user and verify_password(password, user.password):
            session['user_id'] = user.id
            session.permanent = True
            # Логирование входа
            user.last_login = datetime.now()
            db.session.commit()
            return redirect(url_for('profile'))
        else:
            flash('Неверный номер или пароль')

    return render_template('login.html')

@auth.route('/register', methods=['GET', 'POST'])
def register():
    ref_code = request.args.get('ref')
    if ref_code:
        try:
            import base64
            decoded = base64.b64decode(ref_code).decode().split(':')
            referrer_id = int(decoded[0])
            session['referrer_id'] = referrer_id
        except:
            pass
    if request.method == 'POST':
        phone = request.form.get('phone')
        password = request.form.get('password')
        name = request.form.get('name')

        if len(password) < 6:
            flash('Пароль должен быть не менее 6 символов')
            return render_template('register.html')

        formatted_phone = format_phone(phone)
        if not formatted_phone:
            flash('Введите корректный номер телефона')
            return render_template('register.html')

        existing = User.query.filter_by(phone=formatted_phone).first()
        if existing:
            flash('Пользователь с таким номером уже существует')
            return render_template('register.html')

        user = User(
            phone=formatted_phone,
            name=name,
            password=hash_password(password),
            contact_phone=formatted_phone,
            is_driver='is_driver' in request.form,
            car_model=request.form.get('car_model', ''),
            car_color=request.form.get('car_color', ''),
            car_number=request.form.get('car_number', '')
        )
        ref_code = request.args.get('ref')  # из URL

        db.session.add(user)
        db.session.commit()

        # Отправляем приветственное уведомление
        try:
            from app import create_notification
            create_notification(
                user.id,
                'welcome',
                '👋 Добро пожаловать в Север-Юг!',
                '✅ Рады видеть вас!\n\n' +
                '📍 Как пользоваться:\n' +
                '1. Нажмите "Поиск" чтобы найти поездку\n' +
                '2. Выберите маршрут на карте\n' +
                '3. Отправьте заявку водителю\n' +
                '4. Дождитесь подтверждения\n\n' +
                '🚗 Если вы водитель - создайте поездку в профиле',
                '/search'
            )
        except:
            pass  # Если функция не доступна - игнорируем
        # После db.session.commit()
        if session.get('referrer_id'):
            referral = Referral(
                referrer_id=session['referrer_id'],
                friend_id=user.id
            )
            db.session.add(referral)
            db.session.commit()
            session.pop('referrer_id', None)
        flash('Регистрация успешна! Войдите в систему')
        return redirect(url_for('auth.login'))

    return render_template('register.html')

@auth.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

