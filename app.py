from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from database import db, User, Ride, Booking, Message, Notification, FavoriteRoute, RegularRide
from datetime import datetime, timedelta
import math
import requests
import hashlib
import json
import random
from auth import auth, login_required
import requests
import json
import math
import hashlib
import random
import base64
from sqlalchemy import func
from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
from database import db, User, Ride, Booking, Message, Notification, FavoriteRoute, RegularRide, FavoriteDriver, Blacklist, DriverRating, PassengerRating, News, SiteStats, GeneralChat, Referral

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.jinja_env.auto_reload = True
app.jinja_env.cache = None
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rides.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
}
app.config['SECRET_KEY'] = 'sevastopol-2024-super-secret-key'
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

# Telegram Bot настройки
app.config['TELEGRAM_BOT_TOKEN'] = '8544437613:AAH8f_cclE3p098ZSND9WufB0ZOxzwk5loE'
app.config['TELEGRAM_BOT_USERNAME'] = 'severug_bot'
app.config['TELEGRAM_WEBHOOK_URL'] = 'https://sev-sever-ug.ru/telegram_webhook'  # Для продакшена

db.init_app(app)
app.register_blueprint(auth, url_prefix='/auth')

# Функции для работы с пользователем
def get_current_user():
    user_id = session.get('user_id')
    if user_id:
        return db.session.get(User, user_id)
    return None

def send_telegram_message(chat_id, text, keyboard=None):
    try:
        url = f"https://api.telegram.org/bot{app.config['TELEGRAM_BOT_TOKEN']}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML'
        }
        if keyboard:
            data['reply_markup'] = json.dumps(keyboard)
        requests.post(url, json=data, timeout=5)
    except Exception as e:
        print(f"Telegram error: {e}")

def haversine(lat1, lon1, lat2, lon2):
    """Расчет расстояния между точками в км"""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def send_ride_reminders():
    """Отправляет напоминания о поездках за час"""
    one_hour = datetime.now() + timedelta(hours=1)

    # Ищем поездки через час
    upcoming_rides = Ride.query.filter(
        Ride.departure_time >= one_hour - timedelta(minutes=5),
        Ride.departure_time <= one_hour + timedelta(minutes=5)
    ).all()

    for ride in upcoming_rides:
        # Напоминание водителю
        create_notification(
            ride.driver_id,
            'reminder',
            '⏰ Напоминание о поездке',
            f'Ваша поездка {ride.from_place} → {ride.to_place} через час',
            f'/ride/{ride.id}'
        )

        # Напоминание пассажирам
        bookings = Booking.query.filter_by(ride_id=ride.id, status='approved').all()
        for booking in bookings:
            create_notification(
                booking.passenger_id,
                'reminder',
                '⏰ Напоминание о поездке',
                f'Поездка {ride.from_place} → {ride.to_place} через час',
                f'/ride/{ride.id}'
            )

def send_telegram_notification(chat_id, message, parse_mode='HTML'):
    """Отправка уведомления в Telegram"""
    try:
        bot_token = app.config['TELEGRAM_BOT_TOKEN']
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

        if len(message) > 4000:
            parts = [message[i:i+4000] for i in range(0, len(message), 4000)]
            for part in parts:
                data = {
                    'chat_id': chat_id,
                    'text': part,
                    'parse_mode': parse_mode
                }
                requests.post(url, json=data, timeout=5)
        else:
            data = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': parse_mode
            }
            requests.post(url, json=data, timeout=5)
        return True
    except Exception as e:
        print(f"Telegram error: {e}")
        return False

def create_notification(user_id, type, title, text, link=''):
    notif = Notification(
        user_id=user_id,
        type=type,
        title=title,
        text=text,
        link=link,
        is_read=False
    )
    db.session.add(notif)
    db.session.commit()

    # Отправляем в Telegram
    user = db.session.get(User, user_id)
    if user and user.telegram_chat_id:
        tg_text = f"<b>{title}</b>\n\n{text}"
        if link:
            tg_text += f"\n\n<a href='{link}'>🔗 Открыть в приложении</a>"
        send_telegram_message(user.telegram_chat_id, tg_text)

    return notif.id

    # Отправляем Telegram уведомление если есть chat_id
    user = db.session.get(User, user_id)
    if user and user.telegram_chat_id:
        tg_message = f"<b>{title}</b>\n\n{text}"
        if link:
            bot_username = app.config['TELEGRAM_BOT_USERNAME']
            deep_link = f"https://t.me/{bot_username}?start={link.replace('/', '_')}"
            tg_message += f"\n\n<a href='{deep_link}'>🔗 Перейти</a>"

        send_telegram_notification(user.telegram_chat_id, tg_message)

# Добавим тестовые данные при первом запуске
def init_news():
    with app.app_context():
        if News.query.count() == 0:
            news_items = [
                News(
                    title='Обновленное расписание паромов и катеров на февраль 2026',
                    content='Друзья! Мы обновили расписание паромов через бухту. Теперь паром ходит каждые 15 минут в часы пик (7:00-9:00 и 17:00-19:00). В остальное время интервал движения составляет 45 минут. Выходные и праздничные дни - каждые 40 минут. Следите за обновлениями!',
                    excerpt='Актуальное расписание паромов через Севастопольскую бухту',
                    category='Рейд',
                    image='🚢'
                ),
                News(
                    title='Нам 1 месяц! Более 100 поездок совершено',
                    content='Всего за месяц работы нашего сервиса пользователи совершили более 100 успешных поездок! Спасибо, что выбираете Север-Юг. Мы продолжаем улучшать сервис и добавлять новые функции. Скоро появится система рейтингов и избранные водители.',
                    excerpt='Подводим итоги первого месяца работы',
                    category='Новости',
                    image='🎉'
                ),
                News(
                    title='Советы для водителей: как найти попутчиков',
                    content='1. Указывайте точное время отправления\n2. Добавляйте описание автомобиля\n3. Пишите в комментарии особые условия\n4. Быстро отвечайте на заявки\n5. Подтверждайте поездку заранее\n\nСледуя этим советам, вы быстрее найдете попутчиков!',
                    excerpt='Полезные советы для водителей',
                    category='Подсказки',
                    image='💡'
                ),
                News(
                    title='Изменение в работе парома 23 февраля',
                    content='В праздничный день 23 февраля паром будет работать по расписанию выходного дня: с 6:30 до 22:30 с интервалом 40 минут. Планируйте свои поездки заранее!',
                    excerpt='График работы в праздничный день',
                    category='Рейд',
                    image='⏰'
                ),
                News(
                    title='Теперь можно добавлять водителей в избранное',
                    content='Мы добавили новую функцию! Теперь вы можете добавлять понравившихся водителей в избранное, чтобы быстро находить их поездки. Кнопка "В избранное" доступна в профиле водителя после подтверждения поездки.',
                    excerpt='Новая функция на сайте',
                    category='Обновления',
                    image='👥'
                )
            ]
            for item in news_items:
                db.session.add(item)
            db.session.commit()

        # Инициализация статистики
        if SiteStats.query.count() == 0:
            stats = SiteStats(
                total_rides=156,
                total_drivers=89,
                total_passengers=124,
                avg_search_time=12
            )
            db.session.add(stats)
            db.session.commit()

# Создание таблиц
with app.app_context():
    db.create_all()
    init_news()
    print("✅ База данных создана/подключена")

# ========== TELEGRAM ==========
@app.route('/connect_telegram')
@login_required
def connect_telegram():
    user = get_current_user()
    code = str(random.randint(100000, 999999))
    user.telegram_code = code
    db.session.commit()

    return render_template('connect_telegram.html',
                           user=user,
                           bot_username=app.config['TELEGRAM_BOT_USERNAME'],
                           code=code)

@app.route('/api/check_telegram_connection')
@login_required
def check_telegram_connection():
    user = get_current_user()
    return jsonify({'connected': bool(user.telegram_chat_id)})


@app.route('/api/achievements')
@login_required
def get_achievements():
    user = get_current_user()

    # Статистика для ачивок
    driver_rides = Ride.query.filter_by(driver_id=user.id).count()
    passenger_rides = Booking.query.filter_by(passenger_id=user.id, status='approved').count()
    total_rides = driver_rides + passenger_rides

    # Рейтинг
    driver_ratings = DriverRating.query.filter_by(driver_id=user.id).all()
    avg_rating = sum(r.rating for r in driver_ratings) / len(driver_ratings) if driver_ratings else 5.0

    # Уникальные попутчики
    unique_passengers = db.session.query(Booking.passenger_id).filter(
        Booking.ride_id.in_(db.session.query(Ride.id).filter(Ride.driver_id == user.id))
    ).distinct().count()

    return jsonify({
        'first_ride': total_rides > 0,
        'driver_10': driver_rides >= 10,
        'passenger_10': passenger_rides >= 10,
        'rating_50': avg_rating >= 4.9,
        'companions_5': unique_passengers >= 5,
        'total_50': total_rides >= 50
    })

@app.route('/api/active_rides')
@login_required
def get_active_rides():
    user = get_current_user()

    # Поездки как водитель
    driver_rides = Ride.query.filter(
        Ride.driver_id == user.id,
        Ride.departure_time >= datetime.now(),
        Ride.status == 'active'
    ).all()

    # Поездки как пассажир
    passenger_rides = []
    bookings = Booking.query.filter_by(
        passenger_id=user.id,
        status='approved'
    ).all()

    for booking in bookings:
        ride = db.session.get(Ride, booking.ride_id)
        if ride and ride.departure_time >= datetime.now():
            driver = db.session.get(User, ride.driver_id)
            passenger_rides.append({
                'id': ride.id,
                'from_place': ride.from_place,
                'to_place': ride.to_place,
                'time': ride.departure_time.strftime('%d.%m.%Y %H:%M'),
                'driver_id': driver.id,
                'driver_name': driver.name,
                'driver_phone': driver.contact_phone or driver.phone,
                'status': booking.status,
                'price': ride.price
            })

    # Форматируем поездки водителя
    formatted_driver = []
    for ride in driver_rides:
        pending = Booking.query.filter_by(ride_id=ride.id, status='pending').count()
        formatted_driver.append({
            'id': ride.id,
            'from_place': ride.from_place,
            'to_place': ride.to_place,
            'time': ride.departure_time.strftime('%d.%m.%Y %H:%M'),
            'driver_id': user.id,
            'price': ride.price,
            'pending_bookings': pending
        })

    return jsonify(formatted_driver + passenger_rides)

@app.route('/api/support_send_message', methods=['POST'])
@login_required
def support_send_message():
    user = get_current_user()
    data = request.json
    text = data.get('text')

    # Создаем тикет если его нет
    ticket = SupportTicket.query.filter_by(
        user_id=user.id,
        status='open'
    ).first()

    if not ticket:
        ticket = SupportTicket(
            user_id=user.id,
            subject='Обращение в поддержку',
            message=text
        )
        db.session.add(ticket)
        db.session.commit()

    # Сохраняем сообщение
    msg = SupportMessage(
        ticket_id=ticket.id,
        user_id=user.id,
        text=text
    )
    db.session.add(msg)
    db.session.commit()

    return jsonify({'success': True, 'message': {
        'id': msg.id,
        'text': msg.text,
        'created_at': datetime.now().strftime('%H:%M'),
        'sender_id': user.id,
        'sender_name': user.name
    }})

@app.route('/support')
@login_required
def support():
    return render_template('support.html', user=get_current_user())

@app.route('/api/my_tickets')
@login_required
def my_tickets():
    user = get_current_user()
    tickets = SupportTicket.query.filter_by(user_id=user.id).order_by(SupportTicket.created_at.desc()).all()

    result = []
    for t in tickets:
        result.append({
            'id': t.id,
            'subject': t.subject,
            'message': t.message[:100] + ('...' if len(t.message) > 100 else ''),
            'status': t.status,
            'created_at': t.created_at.strftime('%d.%m.%Y %H:%M')
        })

    return jsonify(result)

@app.route('/how-it-works')
def how_it_works():
    return render_template('how-it-works.html', user=get_current_user())

@app.route('/api/support_create', methods=['POST'])
@login_required
def support_create():
    user = get_current_user()
    data = request.json

    ticket = SupportTicket(
        user_id=user.id,
        subject=data.get('subject'),
        message=data.get('message')
    )
    db.session.add(ticket)
    db.session.commit()

    # Уведомление админу
    admin = User.query.filter_by(is_admin=True).first()
    if admin:
        create_notification(
            admin.id,
            'new_support',
            '📬 Новое обращение',
            f'{user.name}: {data.get("subject")}',
            f'/admin/support/{ticket.id}'
        )

    return jsonify({'success': True})

@app.route('/api/support_reply', methods=['POST'])
@login_required
def support_reply():
    user = get_current_user()
    data = request.json

    msg = SupportMessage(
        ticket_id=data.get('ticket_id'),
        user_id=user.id,
        text=data.get('message')
    )
    db.session.add(msg)
    db.session.commit()

    # Уведомление другой стороне
    ticket = db.session.get(SupportTicket, data.get('ticket_id'))
    other_id = ticket.user_id if ticket.user_id != user.id else 1

    create_notification(
        other_id,
        'support_reply',
        '📬 Ответ на обращение',
        data.get('message')[:50] + '...',
        f'/support'
    )

    return jsonify({'success': True})

@app.route('/api/set_telegram_code', methods=['POST'])
@login_required
def set_telegram_code():
    return jsonify({'success': True})

@app.route('/api/complete_ride/<int:ride_id>', methods=['POST'])
@login_required
def complete_ride(ride_id):
    """Водитель отмечает поездку как завершенную"""
    user = get_current_user()
    ride = db.session.get(Ride, ride_id)

    if not ride or ride.driver_id != user.id:
        return jsonify({'error': 'Нет доступа'}), 403

    ride.status = 'completed'

    # Уведомляем всех пассажиров о завершении
    bookings = Booking.query.filter_by(ride_id=ride_id, status='approved').all()
    for booking in bookings:
        create_notification(
            booking.passenger_id,
            'rate_driver',
            '⭐ Оцените поездку',
            f'Как прошла поездка с {user.name}? Оставьте отзыв!',
            f'/rate_ride/{ride_id}'
        )

    # Уведомление водителю
    create_notification(
        user.id,
        'rate_passengers',
        '⭐ Оцените попутчиков',
        f'Поездка {ride.from_place} → {ride.to_place} завершена. Оцените пассажиров!',
        f'/rate_ride/{ride_id}/passengers'
    )

    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/rate_driver', methods=['POST'])
@login_required
def rate_driver():
    """Пассажир оценивает водителя"""
    user = get_current_user()
    data = request.json
    ride_id = data.get('ride_id')
    rating = data.get('rating')
    comment = data.get('comment', '')

    ride = db.session.get(Ride, ride_id)
    if not ride or ride.status != 'completed':
        return jsonify({'error': 'Поездка еще не завершена'}), 400

    # Проверяем, что пользователь был пассажиром
    booking = Booking.query.filter_by(
        ride_id=ride_id,
        passenger_id=user.id,
        status='approved'
    ).first()

    if not booking:
        return jsonify({'error': 'Вы не были пассажиром в этой поездке'}), 403
    if ride.status != 'completed':
        return jsonify({'error': 'Поездка еще не завершена'}), 400

    # Проверяем, не оценивал ли уже
    existing = DriverRating.query.filter_by(
        ride_id=ride_id,
        passenger_id=user.id
    ).first()

    if existing:
        return jsonify({'error': 'Вы уже оценили'}), 400

    # Сохраняем оценку
    rating_obj = DriverRating(
        ride_id=ride_id,
        driver_id=ride.driver_id,
        passenger_id=user.id,
        rating=rating,
        comment=comment
    )
    db.session.add(rating_obj)

    # Обновляем рейтинг водителя
    driver = db.session.get(User, ride.driver_id)
    all_ratings = DriverRating.query.filter_by(driver_id=driver.id).all()
    avg_rating = sum(r.rating for r in all_ratings) / len(all_ratings)
    driver.driver_rating = round(avg_rating, 1)

    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/rate_passengers', methods=['POST'])
@login_required
def rate_passengers():
    """Водитель оценивает пассажиров"""
    user = get_current_user()
    data = request.json
    ride_id = data.get('ride_id')
    ratings = data.get('ratings')  # Список оценок для каждого пассажира

    ride = db.session.get(Ride, ride_id)
    if not ride or ride.driver_id != user.id:
        return jsonify({'error': 'Нет доступа'}), 403

    for r in ratings:
        rating_obj = PassengerRating(
            ride_id=ride_id,
            driver_id=user.id,
            passenger_id=r['passenger_id'],
            rating=r['rating'],
            comment=r.get('comment', '')
        )
        db.session.add(rating_obj)

        # Обновляем рейтинг пассажира
        passenger = db.session.get(User, r['passenger_id'])
        all_ratings = PassengerRating.query.filter_by(passenger_id=passenger.id).all()
        avg_rating = sum(ra.rating for ra in all_ratings) / len(all_ratings)
        passenger.passenger_rating = round(avg_rating, 1)

    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/ride_history')
@login_required
def ride_history():
    """История поездок пользователя"""
    user = get_current_user()

    # Поездки как водитель
    driver_rides = Ride.query.filter_by(
        driver_id=user.id,
        status='completed'
    ).order_by(Ride.departure_time.desc()).all()

    # Поездки как пассажир
    passenger_rides = []
    bookings = Booking.query.filter_by(
        passenger_id=user.id,
        status='approved'
    ).all()

    for booking in bookings:
        ride = db.session.get(Ride, booking.ride_id)
        if ride and ride.status == 'completed':
            passenger_rides.append({
                'ride': ride,
                'booking': booking,
                'driver': db.session.get(User, ride.driver_id)
            })

    return jsonify({
        'as_driver': [{
            'id': r.id,
            'from': r.from_place,
            'to': r.to_place,
            'time': r.departure_time.strftime('%d.%m.%Y %H:%M'),
            'price': r.price
        } for r in driver_rides],
        'as_passenger': [{
            'id': p['ride'].id,
            'from': p['ride'].from_place,
            'to': p['ride'].to_place,
            'time': p['ride'].departure_time.strftime('%d.%m.%Y %H:%M'),
            'driver_name': p['driver'].name,
            'driver_rating': p['driver'].driver_rating
        } for p in passenger_rides]
    })

@app.route('/rate_ride/<int:ride_id>')
@login_required
def rate_ride(ride_id):
    return render_template('rate_ride.html', ride_id=ride_id)

@app.route('/rate_ride/<int:ride_id>/passengers')
@login_required
def rate_passengers_page(ride_id):
    return render_template('rate_passengers.html', ride_id=ride_id)

@app.route('/api/ride_passengers/<int:ride_id>')
@login_required
def ride_passengers(ride_id):
    user = get_current_user()
    ride = db.session.get(Ride, ride_id)

    if ride.driver_id != user.id:
        return jsonify({'error': 'Нет доступа'}), 403

    bookings = Booking.query.filter_by(ride_id=ride_id, status='approved').all()
    passengers = []
    for b in bookings:
        passenger = db.session.get(User, b.passenger_id)
        passengers.append({
            'id': passenger.id,
            'name': passenger.name
        })

    return jsonify(passengers)

@app.route('/api/frequent_routes')
@login_required
def frequent_routes():
    """Возвращает частые маршруты пользователя"""
    user = get_current_user()

    # Анализируем историю поездок пользователя
    as_driver = Ride.query.filter_by(driver_id=user.id).all()
    as_passenger = db.session.query(Ride).join(Booking).filter(Booking.passenger_id == user.id).all()

    all_rides = as_driver + as_passenger
    routes = {}

    for ride in all_rides:
        key = f"{ride.from_place}|{ride.to_place}"
        if key in routes:
            routes[key] += 1
        else:
            routes[key] = 1

    # Сортируем и берем топ-3
    frequent = sorted(routes.items(), key=lambda x: x[1], reverse=True)[:3]

    result = []
    for key, count in frequent:
        from_place, to_place = key.split('|')
        result.append({
            'from': from_place,
            'to': to_place,
            'count': count
        })

    return jsonify(result)

class GeneralChat(db.Model):
    """Общий чат города"""
    __tablename__ = 'general_chat'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    # Связь
    user = db.relationship('User', backref='general_messages')

# Функция отправки в Telegram
def send_telegram_message(chat_id, text, keyboard=None):
    try:
        url = f"https://api.telegram.org/bot{app.config['TELEGRAM_BOT_TOKEN']}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML'
        }
        if keyboard:
            data['reply_markup'] = json.dumps(keyboard)
        requests.post(url, json=data, timeout=5)
    except Exception as e:
        print(f"Telegram error: {e}")

# Обнови функцию create_notification
def create_notification(user_id, type, title, text, link=''):
    notif = Notification(
        user_id=user_id,
        type=type,
        title=title,
        text=text,
        link=link,
        is_read=False
    )
    db.session.add(notif)
    db.session.commit()

    # Отправляем в Telegram
    user = db.session.get(User, user_id)
    if user and user.telegram_chat_id:
        tg_text = f"<b>{title}</b>\n\n{text}"
        if link:
            tg_text += f"\n\n<a href='{link}'>🔗 Открыть в приложении</a>"
        send_telegram_message(user.telegram_chat_id, tg_text)


# Обнови webhook
@app.route('/telegram_webhook', methods=['POST'])
def telegram_webhook():
    data = request.json
    print(f"Telegram webhook: {data}")

    if 'message' in data:
        chat_id = data['message']['chat']['id']
        text = data['message'].get('text', '')

        if text.startswith('/start'):
            parts = text.split()
            if len(parts) == 2:
                code = parts[1]
                user = User.query.filter_by(telegram_code=code).first()
                if user:
                    user.telegram_chat_id = str(chat_id)
                    user.telegram_code = None
                    db.session.commit()

                    welcome = "✅ <b>Telegram успешно привязан!</b>\n\nТеперь вы будете получать уведомления о поездках."
                    send_telegram_message(chat_id, welcome)

                    create_notification(user.id, 'telegram_connected', '📱 Telegram', 'Telegram подключен!')
                else:
                    send_telegram_message(chat_id, "❌ Неверный код подтверждения")

    return jsonify({'ok': True})

# ========== ГЛАВНАЯ ==========
@app.route('/')
def index():
    user = get_current_user()
    return render_template('index.html', user=user)

# ========== ПРОФИЛЬ ==========
@app.route('/profile')
@login_required
def profile():
    user = get_current_user()
    if not user:
        return redirect(url_for('auth.login'))

    # Поездки где пользователь - водитель
    driver_rides = Ride.query.filter_by(driver_id=user.id).order_by(Ride.departure_time.desc()).all()

    # Поездки где пользователь - пассажир
    bookings = Booking.query.filter_by(passenger_id=user.id).all()
    passenger_rides = []
    for booking in bookings:
        ride = db.session.get(Ride, booking.ride_id)
        if ride:
            passenger_rides.append({
                'ride': ride,
                'booking': booking,
                'driver': db.session.get(User, ride.driver_id)
            })

    # Уведомления
    notifications = Notification.query.filter_by(user_id=user.id, is_read=False).order_by(Notification.created_at.desc()).all()

    # Избранные маршруты
    favorite_routes = FavoriteRoute.query.filter_by(user_id=user.id).all()

    # Избранные водители
    favorite_drivers = FavoriteDriver.query.filter_by(passenger_id=user.id).all()
    fav_drivers_list = []
    for fav in favorite_drivers:
        driver = db.session.get(User, fav.driver_id)
        if driver:
            fav_drivers_list.append(driver)

    # Регулярные поездки
    regular_rides = RegularRide.query.filter_by(user_id=user.id).all()

    # Статистика
    stats = {
        'as_driver': len(driver_rides),
        'as_passenger': len(passenger_rides),
        'total': len(driver_rides) + len(passenger_rides)
    }

    return render_template('profile.html',
                           user=user,
                           driver_rides=driver_rides,
                           passenger_rides=passenger_rides,
                           notifications=notifications,
                           favorite_routes=favorite_routes,
                           favorite_drivers=fav_drivers_list,
                           regular_rides=regular_rides,
                           stats=stats,
                           now=datetime.now())

@app.route('/api/favorite_routes')
@login_required
def favorite_routes():
    """Возвращает избранные маршруты пользователя"""
    user = get_current_user()

    try:
        favorites = FavoriteRoute.query.filter_by(user_id=user.id).all()
        result = []
        for fav in favorites:
            result.append({
                'id': fav.id,
                'name': fav.name or 'Мой маршрут',
                'from_place': fav.from_place,
                'to_place': fav.to_place,
                'from_lat': fav.from_lat,
                'from_lng': fav.from_lng,
                'to_lat': fav.to_lat,
                'to_lng': fav.to_lng
            })
        return jsonify(result)
    except Exception as e:
        print(f"Error loading favorites: {e}")
        return jsonify([])

@app.route('/api/delete_account', methods=['DELETE'])
@login_required
def delete_account():
    """Удаление аккаунта"""
    user = get_current_user()

    try:
        # Удаляем все связанные данные
        Message.query.filter_by(sender_id=user.id).delete()
        Message.query.filter_by(receiver_id=user.id).delete()
        Booking.query.filter_by(passenger_id=user.id).delete()
        Notification.query.filter_by(user_id=user.id).delete()
        FavoriteRoute.query.filter_by(user_id=user.id).delete()
        FavoriteDriver.query.filter_by(passenger_id=user.id).delete()
        FavoriteDriver.query.filter_by(driver_id=user.id).delete()

        # Удаляем поездки (сначала удаляем связанные бронирования)
        rides = Ride.query.filter_by(driver_id=user.id).all()
        for ride in rides:
            Booking.query.filter_by(ride_id=ride.id).delete()
            db.session.delete(ride)

        db.session.delete(user)
        db.session.commit()

        session.clear()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/chat/start/<int:user_id>')
@login_required
def start_chat(user_id):
    """Начать чат с пользователем (создать диалог)"""
    current_user = get_current_user()
    other_user = db.session.get(User, user_id)

    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == user_id)) |
        ((Message.sender_id == user_id) & (Message.receiver_id == current_user.id))
    ).first()

    if messages:
        # Если есть сообщения, идем в существующий чат
        return redirect(f'/chat/{messages.ride_id}')

    if not other_user:
        return "Пользователь не найден", 404

    # Ищем существующий чат между пользователями
    # Находим поездки, где они оба участвовали
    rides_as_driver = Ride.query.filter_by(driver_id=current_user.id).all()
    rides_as_passenger = [b.ride_id for b in Booking.query.filter_by(passenger_id=current_user.id).all()]

    # Ищем общую поездку
    common_ride = None
    for ride in rides_as_driver:
        if Booking.query.filter_by(ride_id=ride.id, passenger_id=user_id).first():
            common_ride = ride
            break

    if not common_ride:
        for ride_id in rides_as_passenger:
            ride = db.session.get(Ride, ride_id)
            if ride and ride.driver_id == user_id:
                common_ride = ride
                break

    if common_ride:
        return redirect(f'/chat/{common_ride.id}')
    else:
        # Если нет общей поездки, создаем специальный чат поддержки
        return redirect(f'/chat/{user_id}')

@app.route('/api/delete_ride/<int:ride_id>', methods=['DELETE'])
@login_required
def delete_ride(ride_id):
    user = get_current_user()
    ride = db.session.get(Ride, ride_id)

    if not ride:
        return jsonify({'error': 'Поездка не найдена'}), 404

    if ride.driver_id != user.id:
        return jsonify({'error': 'Нет доступа'}), 403

    # Удаляем связанные бронирования
    Booking.query.filter_by(ride_id=ride_id).delete()

    db.session.delete(ride)
    db.session.commit()

    create_notification(user.id, 'ride_deleted', 'Поездка удалена',
                        f'Поездка {ride.from_place} → {ride.to_place} удалена')

    return jsonify({'success': True})

@app.route('/api/notifications')
@login_required
def get_notifications():
    user = get_current_user()
    notifications = Notification.query.filter_by(
        user_id=user.id,
        is_read=False
    ).order_by(Notification.created_at.desc()).limit(10).all()

    result = []
    for n in notifications:
        result.append({
            'id': n.id,
            'title': n.title,
            'text': n.text,
            'created_at': n.created_at.strftime('%H:%M %d.%m'),
            'is_read': n.is_read
        })

    return jsonify(result)

def archive_old_rides():
    """Автоматически архивирует прошедшие поездки"""
    with app.app_context():
        # Находим поездки, которые закончились более 2 часов назад
        two_hours_ago = datetime.now() - timedelta(hours=2)
        old_rides = Ride.query.filter(
            Ride.departure_time <= two_hours_ago,
            Ride.status == 'active'
        ).all()

        for ride in old_rides:
            ride.status = 'completed'

            # Отправляем уведомления всем участникам о необходимости оценить
            bookings = Booking.query.filter_by(ride_id=ride.id, status='approved').all()

            # Уведомление водителю
            create_notification(
                ride.driver_id,
                'rate_passengers',
                '⭐ Оцените попутчиков',
                f'Поездка {ride.from_place} → {ride.to_place} завершена. Оцените ваших пассажиров!',
                f'/rate_ride/{ride.id}'
            )

            # Уведомления пассажирам
            for booking in bookings:
                create_notification(
                    booking.passenger_id,
                    'rate_driver',
                    '⭐ Оцените поездку',
                    f'Как прошла поездка с {ride.driver.name}? Оставьте отзыв!',
                    f'/rate_ride/{ride.id}'
                )

        db.session.commit()
        return len(old_rides)

@app.route('/api/blacklist', methods=['POST'])
@login_required
def add_to_blacklist():
    """Водитель добавляет пассажира в черный список"""
    user = get_current_user()
    data = request.json
    passenger_id = data.get('passenger_id')
    reason = data.get('reason', '')

    # Проверяем, что пользователь - водитель
    if not user.is_driver:
        return jsonify({'error': 'Только водители могут использовать черный список'}), 403

    # Проверяем, не заблокирован ли уже
    existing = Blacklist.query.filter_by(
        driver_id=user.id,
        passenger_id=passenger_id
    ).first()

    if existing:
        return jsonify({'error': 'Пассажир уже в черном списке'}), 400

    blacklist = Blacklist(
        driver_id=user.id,
        passenger_id=passenger_id,
        reason=reason
    )
    db.session.add(blacklist)
    db.session.commit()

    return jsonify({'success': True})

@app.route('/api/favorite_driver', methods=['POST'])
@login_required
def add_favorite_driver():
    """Пассажир добавляет водителя в избранное"""
    user = get_current_user()
    data = request.json
    driver_id = data.get('driver_id')

    existing = FavoriteDriver.query.filter_by(
        passenger_id=user.id,
        driver_id=driver_id
    ).first()

    if existing:
        # Если уже в избранном - удаляем
        db.session.delete(existing)
        db.session.commit()
        return jsonify({'favorite': False})
    else:
        # Добавляем в избранное
        fav = FavoriteDriver(
            passenger_id=user.id,
            driver_id=driver_id
        )
        db.session.add(fav)
        db.session.commit()
        return jsonify({'favorite': True})

@app.route('/api/notifications/count')
def notifications_count():
    """Количество непрочитанных уведомлений (для анонимных пользователей возвращает 0)"""
    user = get_current_user()
    if not user:
        return jsonify({'count': 0})
    count = Notification.query.filter_by(user_id=user.id, is_read=False).count()
    return jsonify({'count': count})

@app.route('/api/all_notifications')
@login_required
def all_notifications():
    user = get_current_user()
    notifications = Notification.query.filter_by(user_id=user.id).order_by(Notification.created_at.desc()).all()

    result = []
    for n in notifications:
        result.append({
            'id': n.id,
            'title': n.title,
            'text': n.text,
            'link': n.link,
            'created_at': n.created_at.strftime('%d.%m.%Y %H:%M'),
            'is_read': n.is_read
        })

    return jsonify(result)

@app.route('/chats')
@login_required
def chats():
    return render_template('chats.html', user=get_current_user())

@app.route('/api/chats')
@login_required
def get_chats():
    user = get_current_user()
    if not user:
        return jsonify([])  # Возвращаем пустой список если пользователь не авторизован

    # Находим все уникальные диалоги
    sent = db.session.query(
        Message.receiver_id,
        Message.ride_id,
        func.max(Message.created_at).label('last_time')
    ).filter(Message.sender_id == user.id).group_by(Message.receiver_id, Message.ride_id).all()

    received = db.session.query(
        Message.sender_id,
        Message.ride_id,
        func.max(Message.created_at).label('last_time')
    ).filter(Message.receiver_id == user.id).group_by(Message.sender_id, Message.ride_id).all()

    chats_dict = {}

    # Обрабатываем отправленные
    for other_id, ride_id, last_time in sent:
        key = f"{ride_id}_{other_id}"
        other_user = db.session.get(User, other_id)
        ride = db.session.get(Ride, ride_id)

        if not other_user:
            continue

        # Считаем непрочитанные
        unread = Message.query.filter_by(
            ride_id=ride_id,
            sender_id=other_id,
            receiver_id=user.id,
            is_read=False
        ).count()

        # Последнее сообщение
        last_msg = Message.query.filter(
            Message.ride_id == ride_id,
            ((Message.sender_id == user.id) & (Message.receiver_id == other_id)) |
            ((Message.sender_id == other_id) & (Message.receiver_id == user.id))
        ).order_by(Message.created_at.desc()).first()

        chats_dict[key] = {
            'ride_id': ride_id,
            'other_user': {
                'id': other_id,
                'name': other_user.name
            },
            'last_message': last_msg.text if last_msg else '',
            'last_time': last_time.strftime('%H:%M %d.%m') if last_time else '',
            'unread': unread,
            'route': f"{ride.from_place} → {ride.to_place}" if ride else 'Поездка',
            'is_online': False
        }

    # Обрабатываем полученные
    for other_id, ride_id, last_time in received:
        key = f"{ride_id}_{other_id}"
        if key not in chats_dict:
            other_user = db.session.get(User, other_id)
            ride = db.session.get(Ride, ride_id)

            if not other_user:
                continue

            unread = Message.query.filter_by(
                ride_id=ride_id,
                sender_id=other_id,
                receiver_id=user.id,
                is_read=False
            ).count()

            last_msg = Message.query.filter(
                Message.ride_id == ride_id,
                ((Message.sender_id == user.id) & (Message.receiver_id == other_id)) |
                ((Message.sender_id == other_id) & (Message.receiver_id == user.id))
            ).order_by(Message.created_at.desc()).first()

            chats_dict[key] = {
                'ride_id': ride_id,
                'other_user': {
                    'id': other_id,
                    'name': other_user.name
                },
                'last_message': last_msg.text if last_msg else '',
                'last_time': last_time.strftime('%H:%M %d.%m') if last_time else '',
                'unread': unread,
                'route': f"{ride.from_place} → {ride.to_place}" if ride else 'Поездка',
                'is_online': False
            }

    # Сортируем по времени последнего сообщения
    chats = sorted(chats_dict.values(), key=lambda x: x['last_time'], reverse=True)

    return jsonify(chats)

@app.route('/api/message/read/<int:message_id>', methods=['POST'])
@login_required
def mark_message_read(message_id):
    message = db.session.get(Message, message_id)
    if message and message.receiver_id == get_current_user().id:
        message.is_read = True
        db.session.commit()
    return jsonify({'success': True})

@app.route('/api/chat/online')
@login_required
def get_online_users():
    # Получаем список онлайн пользователей (активных в последние 5 минут)
    five_min_ago = datetime.now() - timedelta(minutes=5)
    online = User.query.filter(User.last_seen >= five_min_ago).all()
    return jsonify([{'id': u.id, 'name': u.name} for u in online])

@app.route('/city-chat')
@login_required
def city_chat():
    """Общий чат города"""
    return render_template('city_chat.html', user=get_current_user())

@app.route('/api/city_chat/messages')
@login_required
def get_city_messages():
    """Получение сообщений общего чата"""
    messages = GeneralChat.query.order_by(GeneralChat.created_at.desc()).limit(50).all()
    messages.reverse()

    result = []
    for msg in messages:
        # Используем author вместо user
        result.append({
            'id': msg.id,
            'user_id': msg.user_id,
            'user_name': msg.author.name if msg.author else 'Пользователь',
            'user_avatar': msg.author.name[0] if msg.author else '?',
            'text': msg.text,
            'time': msg.created_at.strftime('%H:%M'),
            'date': msg.created_at.strftime('%d.%m.%Y')
        })

    return jsonify(result)

@app.route('/api/city_chat/send', methods=['POST'])
@login_required
def send_city_message():
    """Отправка сообщения в общий чат"""
    user = get_current_user()
    data = request.json
    text = data.get('text', '').strip()

    if not text:
        return jsonify({'error': 'Пустое сообщение'}), 400

    message = GeneralChat(
        user_id=user.id,
        text=text
    )
    db.session.add(message)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': {
            'id': message.id,
            'user_id': user.id,
            'user_name': user.name,
            'user_avatar': user.name[0],
            'text': text,
            'time': message.created_at.strftime('%H:%M'),
            'date': message.created_at.strftime('%d.%m.%Y')
        }
    })

@app.route('/invite')
@login_required
def invite():
    """Страница приглашения друзей"""
    user = get_current_user()

    # Считаем статистику
    invites = Referral.query.filter_by(referrer_id=user.id).count()

    # Генерируем реферальную ссылку
    ref_code = base64.b64encode(f"{user.id}:{user.name}".encode()).decode()

    return render_template('invite.html',
                           user=user,
                           invites=invites,
                           ref_code=ref_code,
                           invite_link=f"http://sev-sever-ug.ru/register?ref={ref_code}")

@app.route('/privacy')
def privacy():
    return render_template('privacy.html', user=get_current_user())

@app.route('/terms')
def terms():
    return render_template('terms.html', user=get_current_user())

@app.route('/api/referral/accept', methods=['POST'])
def accept_referral():
    """Обработка реферальной ссылки"""
    data = request.json
    ref_code = data.get('ref_code')

    try:
        # Декодируем код
        decoded = base64.b64decode(ref_code).decode().split(':')
        referrer_id = int(decoded[0])

        # Сохраняем в сессии
        session['referrer_id'] = referrer_id

        return jsonify({'success': True})
    except:
        return jsonify({'success': False})

@app.route('/api/analytics')
@login_required
def analytics():
    """Аналитика для дашборда"""
    user = get_current_user()

    # Поездки по дням недели (последние 7 дней)
    days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
    driver_data = [0]*7
    passenger_data = [0]*7

    # Считаем поездки
    rides = Ride.query.filter_by(driver_id=user.id).all()
    for ride in rides:
        day = ride.created_at.weekday()
        driver_data[day] += 1

    bookings = Booking.query.filter_by(passenger_id=user.id).all()
    for booking in bookings:
        day = booking.created_at.weekday()
        passenger_data[day] += 1

    # Детальный рейтинг
    ratings = [5, 5, 5, 5, 5]  # Заглушка

    return jsonify({
        'days': days,
        'driver': driver_data,
        'passenger': passenger_data,
        'ratings': ratings
    })

@app.route('/api/favorite_drivers')
@login_required
def get_favorite_drivers():
    """Получение списка избранных водителей"""
    user = get_current_user()
    favorites = FavoriteDriver.query.filter_by(passenger_id=user.id).all()

    result = []
    for fav in favorites:
        driver = db.session.get(User, fav.driver_id)
        if driver:
            result.append({
                'id': driver.id,
                'name': driver.name,
                'rating': driver.driver_rating or 5.0,
                'car': f"{driver.car_color} {driver.car_model}" if driver.car_model else None
            })

    return jsonify(result)

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    user = get_current_user()
    # Приватность
    user.show_profile = 'show_profile' in request.form
    user.show_phone = 'show_phone' in request.form
    user.show_rating = 'show_rating' in request.form
    user.show_history = 'show_history' in request.form
    user.bio = request.form.get('bio', '')
    if not user:
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        user.name = request.form.get('name', user.name)
        user.contact_phone = request.form.get('contact_phone', user.phone)
        user.telegram = request.form.get('telegram')
        user.whatsapp = request.form.get('whatsapp')
        user.car_model = request.form.get('car_model')
        user.car_color = request.form.get('car_color')
        user.car_number = request.form.get('car_number')
        user.is_driver = 'is_driver' in request.form
        user.show_profile = 'show_profile' in request.form
        user.show_phone = 'show_phone' in request.form
        user.show_rating = 'show_rating' in request.form
        user.show_history = 'show_history' in request.form

        db.session.commit()
        return redirect(url_for('profile'))

    return render_template('edit_profile.html', user=user)

# ========== ПОЕЗДКИ ==========
@app.route('/create_ride', methods=['GET', 'POST'])
@login_required
def create_ride():
    user = get_current_user()
    if not user:
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        new_ride = Ride(
            driver_id=user.id,
            from_place=request.form['from'],
            to_place=request.form['to'],
            from_lat=float(request.form['from_lat']),
            from_lng=float(request.form['from_lng']),
            to_lat=float(request.form['to_lat']),
            to_lng=float(request.form['to_lng']),
            departure_time=datetime.strptime(request.form['time'], '%Y-%m-%dT%H:%M'),
            seats=int(request.form['seats']),
            price=int(request.form['price']),
            description=request.form['description']
        )
        db.session.add(new_ride)
        db.session.commit()

        create_notification(
            user.id,
            'ride_created',
            'Поездка создана',
            f'Вы создали поездку {request.form["from"]} → {request.form["to"]}',
            f'/ride/{new_ride.id}'
        )

        return redirect(url_for('profile'))

    return render_template('create_ride.html', user=user)

@app.route('/cron/archive_rides')
def cron_archive_rides():
    """Запуск архивации (для планировщика)"""
    count = archive_old_rides()
    return jsonify({'archived': count})

@app.route('/search')
def search():
    user = get_current_user()
    if not user:
        flash('Для поиска поездок необходимо войти')
        return redirect(url_for('auth.login'))
    return render_template('search.html', user=user)

@app.route('/ride/<int:ride_id>')
def ride_details(ride_id):
    ride = db.session.get(Ride, ride_id)
    if not ride:
        return "Поездка не найдена", 404

    driver = db.session.get(User, ride.driver_id)
    user = get_current_user()
    booking = None
    if user:
        booking = Booking.query.filter_by(ride_id=ride_id, passenger_id=user.id, status='approved').first()
        if not booking:
            booking = Booking.query.filter_by(ride_id=ride_id, passenger_id=user.id, status='pending').first()

    bookings = db.session.query(Booking).filter_by(ride_id=ride_id).all()
    for b in bookings:
        b.passenger = db.session.get(User, b.passenger_id)

    return render_template('ride_details.html',
                           ride=ride,
                           driver=driver,
                           booking=booking,
                           user=user,
                           now=datetime.now(),
                           bookings=bookings)

@app.route('/regular_rides')
@login_required
def regular_rides():
    user = get_current_user()
    return render_template('regular_rides.html', user=user)

def get_route_around_bay(from_lat, from_lng, to_lat, to_lng):
    """Строит маршрут в обход Севастопольской бухты"""
    import requests

    # Координаты объезда через Инкерман
    detour_points = [
        [44.6165, 33.5256],  # пл. Захарова
        [44.6050, 33.6050],  # объезд
        [44.6500, 33.6500],  # выход на Северную
        [44.6502, 33.5678]   # Северная
    ]

    try:
        # Используем Яндекс.Карты API
        url = "https://api.routing.yandex.net/v2/route"
        params = {
            'apikey': '4932c58f-dc3f-4c34-b0ca-a64c1ef43dca',
            'waypoints': f"{from_lat},{from_lng}|{to_lat},{to_lng}",
            'mode': 'avoid_tolls'  # избегаем паромов
        }
        response = requests.get(url, params=params)
        return response.json()
    except:
        return None

# ========== API ПОИСКА ==========
@app.route('/api/search_rides')
def api_search_rides():
    try:
        from_lat = float(request.args.get('from_lat'))
        from_lng = float(request.args.get('from_lng'))
        to_lat = float(request.args.get('to_lat'))
        to_lng = float(request.args.get('to_lng'))
    except:
        return jsonify({'error': 'Не указаны координаты'}), 400

    # Получаем все активные поездки
    rides = Ride.query.filter(Ride.departure_time >= datetime.now()).all()
    result = []

    for ride in rides:
        driver = db.session.get(User, ride.driver_id)

        # Проверяем, что поездка ещё актуальна (в ближайшие 6 часов)
        time_diff = (ride.departure_time - datetime.now()).total_seconds() / 3600
        if time_diff > 6:
            continue

        # Проверяем, что есть свободные места
        if ride.seats <= 0:
            continue

        # УВЕЛИЧИВАЕМ РАДИУС ПОИСКА ДО 8 КМ (чтобы учитывать объезд бухты)
        dist_to_start = haversine(from_lat, from_lng, ride.from_lat, ride.from_lng)
        dist_to_end = haversine(to_lat, to_lng, ride.to_lat, ride.to_lng)

        if dist_to_start <= 8.0 and dist_to_end <= 8.0:
            result.append({
                'id': ride.id,
                'from': ride.from_place,
                'to': ride.to_place,
                'from_lat': ride.from_lat,
                'from_lng': ride.from_lng,
                'to_lat': ride.to_lat,
                'to_lng': ride.to_lng,
                'time': ride.departure_time.strftime('%d.%m.%Y %H:%M'),
                'seats': ride.seats,
                'price': ride.price,
                'description': ride.description,
                'driver_name': driver.name,
                'car_model': driver.car_model,
                'car_color': driver.car_color,
                'car_number': driver.car_number,
                'contact_phone': driver.contact_phone or driver.phone,
                'distance_to_start': round(dist_to_start, 1),
                'distance_to_end': round(dist_to_end, 1)
            })

    # Сортируем по близости
    result.sort(key=lambda x: x['distance_to_start'] + x['distance_to_end'])

    return jsonify(result)

# ========== УВЕДОМЛЕНИЯ (PUSH) ==========
@app.route('/api/last_notification_id')
@login_required
def last_notification_id():
    user = get_current_user()
    last = Notification.query.filter_by(user_id=user.id).order_by(Notification.id.desc()).first()
    return jsonify({'last_id': last.id if last else 0})

@app.route('/api/check_notifications')
def check_notifications():
    """Проверка новых уведомлений (для анонимных пользователей возвращает пустой список)"""
    user = get_current_user()
    if not user:
        return jsonify({'notifications': []})

    since = request.args.get('since', 0, type=int)

    notifications = Notification.query.filter(
        Notification.user_id == user.id,
        Notification.id > since,
        Notification.is_read == False
    ).order_by(Notification.id).all()

    result = []
    for notif in notifications:
        result.append({
            'id': notif.id,
            'type': notif.type,
            'title': notif.title,
            'text': notif.text,
            'link': notif.link or '#',
            'created_at': notif.created_at.strftime('%H:%M')
        })
        notif.is_read = True

    db.session.commit()

    return jsonify({'notifications': result})

@app.route('/api/smart_routes')
def smart_routes():
    """AI-анализ популярных маршрутов"""
    # Анализируем историю поездок
    rides = Ride.query.all()

    routes_count = {}
    for ride in rides:
        key = f"{ride.from_place}||{ride.to_place}"
        if key in routes_count:
            routes_count[key] += 1
        else:
            routes_count[key] = 1

    # Находим топ-5 популярных маршрутов
    popular = sorted(routes_count.items(), key=lambda x: x[1], reverse=True)[:5]

    result = []
    for route, count in popular:
        from_place, to_place = route.split('||')
        result.append({
            'from': from_place,
            'to': to_place,
            'count': count,
            'popularity': '🔥' * min(count, 5)
        })

    return jsonify(result)

@app.route('/api/route_suggestions')
def route_suggestions():
    """Умные подсказки маршрутов"""
    query = request.args.get('q', '').lower()

    if len(query) < 2:
        return jsonify([])

    # Ищем похожие маршруты
    rides = Ride.query.all()
    suggestions = set()

    for ride in rides:
        if query in ride.from_place.lower() or query in ride.to_place.lower():
            suggestions.add((ride.from_place, ride.to_place))

    result = []
    for from_place, to_place in list(suggestions)[:5]:
        result.append({
            'from': from_place,
            'to': to_place,
            'display': f"{from_place} → {to_place}"
        })

    return jsonify(result)

@app.route('/profile/<int:user_id>')
def public_profile(user_id):
    """Публичная страница профиля пользователя"""
    current_user = get_current_user()
    profile_user = db.session.get(User, user_id)

    if not profile_user:
        return "Пользователь не найден", 404

    # Проверяем, разрешено ли показывать профиль
    if not profile_user.show_profile and (not current_user or current_user.id != profile_user.id):
        return render_template('profile_hidden.html', user=current_user, profile_user=profile_user), 403

    # Получаем статистику
    as_driver = Ride.query.filter_by(driver_id=profile_user.id, status='completed').count()
    as_passenger = Booking.query.filter_by(passenger_id=profile_user.id, status='approved').count()

    # Получаем отзывы о пользователе как о водителе
    driver_reviews = db.session.query(DriverRating, User).join(
        User, DriverRating.passenger_id == User.id
    ).filter(DriverRating.driver_id == profile_user.id).order_by(
        DriverRating.created_at.desc()
    ).limit(10).all()

    # Получаем отзывы о пользователе как о пассажире
    passenger_reviews = db.session.query(PassengerRating, User).join(
        User, PassengerRating.driver_id == User.id
    ).filter(PassengerRating.passenger_id == profile_user.id).order_by(
        PassengerRating.created_at.desc()
    ).limit(10).all()

    # Получаем последние поездки (если разрешено)
    recent_rides = []
    if profile_user.show_history:
        recent_rides = Ride.query.filter_by(driver_id=profile_user.id, status='completed').order_by(
            Ride.departure_time.desc()
        ).limit(5).all()

    # Проверяем, есть ли пользователь в избранном у текущего
    is_favorite = False
    if current_user:
        is_favorite = FavoriteDriver.query.filter_by(
            passenger_id=current_user.id,
            driver_id=profile_user.id
        ).first() is not None

    return render_template('public_profile.html',
                           user=current_user,
                           profile_user=profile_user,
                           as_driver=as_driver,
                           as_passenger=as_passenger,
                           driver_reviews=driver_reviews,
                           passenger_reviews=passenger_reviews,
                           recent_rides=recent_rides,
                           is_favorite=is_favorite)

@app.route('/api/user/<int:user_id>/stats')
def user_stats(user_id):
    """API для получения статистики пользователя"""
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Проверяем приватность
    if not user.show_profile:
        return jsonify({'error': 'Profile hidden'}), 403

    stats = {
        'total_rides': Ride.query.filter_by(driver_id=user_id, status='completed').count() +
                       Booking.query.filter_by(passenger_id=user_id, status='approved').count(),
        'as_driver': Ride.query.filter_by(driver_id=user_id, status='completed').count(),
        'as_passenger': Booking.query.filter_by(passenger_id=user_id, status='approved').count(),
        'driver_rating': user.driver_rating or 5.0,
        'passenger_rating': user.passenger_rating or 5.0,
        'member_since': user.member_since.strftime('%B %Y') if user.member_since else '2024',
        'last_active': user.last_active.strftime('%d.%m.%Y') if user.last_active else 'Недавно'
    }

    return jsonify(stats)

@app.route('/news')
def news():
    return render_template('news.html', user=get_current_user())

@app.route('/api/news')
def get_news():
    """Получение всех новостей с правильными датами"""
    news = News.query.order_by(News.created_at.desc()).all()
    result = []
    for item in news:
        # Форматируем дату на русском
        months = {
            1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля',
            5: 'мая', 6: 'июня', 7: 'июля', 8: 'августа',
            9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'
        }
        date = item.created_at
        formatted_date = f"{date.day} {months[date.month]} {date.year}"

        # Если нет изображения, ставим заглушку по категории
        category_images = {
            'news': '📰',
            'update': '✨',
            'ferry': '🚢',
            'tips': '💡',
            'technical': '🔧'
        }
        image = item.image or category_images.get(item.category, '📰')

        result.append({
            'id': item.id,
            'title': item.title,
            'excerpt': item.excerpt or item.content[:150] + '...',
            'content': item.content,
            'category': item.category,
            'views': item.views,
            'date': formatted_date,
            'image': image
        })
    return jsonify(result)

@app.route('/api/news/<int:news_id>')
def get_news_item(news_id):
    """Получение конкретной новости"""
    news = db.session.get(News, news_id)
    if news:
        news.views += 1
        db.session.commit()
        return jsonify({
            'id': news.id,
            'title': news.title,
            'content': news.content,
            'category': news.category,
            'date': news.created_at.strftime('%d %B %Y'),
            'views': news.views
        })
    return jsonify({'error': 'Новость не найдена'}), 404

@app.route('/api/stats')
def get_stats():
    """Реальная статистика сайта"""
    # Считаем реальные данные
    total_rides = Ride.query.count()
    total_drivers = User.query.filter_by(is_driver=True).count()
    total_passengers = db.session.query(Booking.passenger_id).distinct().count()

    # Среднее время поиска (можно сделать фиксированным или рассчитывать)
    avg_search_time = 12  # минут

    # Обновляем в базе (опционально)
    stats = SiteStats.query.first()
    if stats:
        stats.total_rides = total_rides
        stats.total_drivers = total_drivers
        stats.total_passengers = total_passengers
        stats.avg_search_time = avg_search_time
        db.session.commit()
    else:
        stats = SiteStats(
            total_rides=total_rides,
            total_drivers=total_drivers,
            total_passengers=total_passengers,
            avg_search_time=avg_search_time
        )
        db.session.add(stats)
        db.session.commit()

    return jsonify({
        'total_rides': total_rides,
        'total_drivers': total_drivers,
        'total_passengers': total_passengers,
        'avg_search_time': avg_search_time
    })

@app.route('/admin/news')
@login_required
def admin_news():
    user = get_current_user()
    if user.id != 1:  # Только админ (id=1)
        return redirect('/')

    news = News.query.order_by(News.created_at.desc()).all()
    return render_template('admin_news.html', news=news, user=user)

@app.route('/api/admin/news/create', methods=['POST'])
@login_required
def admin_news_create():
    user = get_current_user()
    if user.id != 1:
        return jsonify({'error': 'Доступ запрещен'}), 403

    data = request.json
    news = News(
        title=data['title'],
        content=data['content'],
        excerpt=data.get('excerpt', data['content'][:150] + '...'),
        category=data.get('category', 'news'),
        image=data.get('image', '')
    )
    db.session.add(news)
    db.session.commit()

    return jsonify({'success': True})

@app.route('/api/admin/news/edit/<int:news_id>', methods=['POST'])
@login_required
def admin_news_edit(news_id):
    user = get_current_user()
    if user.id != 1:
        return jsonify({'error': 'Доступ запрещен'}), 403

    news = db.session.get(News, news_id)
    data = request.json

    news.title = data['title']
    news.content = data['content']
    news.excerpt = data.get('excerpt', data['content'][:150] + '...')
    news.category = data.get('category', 'news')
    news.image = data.get('image', '')

    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/admin/news/delete/<int:news_id>', methods=['DELETE'])
@login_required
def admin_news_delete(news_id):
    user = get_current_user()
    if user.id != 1:
        return jsonify({'error': 'Доступ запрещен'}), 403

    news = db.session.get(News, news_id)
    db.session.delete(news)
    db.session.commit()

    return jsonify({'success': True})

@app.route('/api/active_drivers')
def api_active_drivers():
    rides = Ride.query.filter(
        Ride.departure_time >= datetime.now(),
        Ride.seats > 0
    ).all()

    result = []
    for ride in rides:
        driver = db.session.get(User, ride.driver_id)
        result.append({
            'id': ride.id,
            'driver_name': driver.name,
            'from_place': ride.from_place,
            'to_place': ride.to_place,
            'from_lat': ride.from_lat,
            'from_lng': ride.from_lng,
            'to_lat': ride.to_lat,
            'to_lng': ride.to_lng,
            'time': ride.departure_time.strftime('%d.%m.%Y %H:%M'),
            'seats': ride.seats,
            'price': ride.price
        })

    return jsonify(result)

# ========== БРОНИРОВАНИЕ ==========
@app.route('/api/book_ride', methods=['POST'])
@login_required
def book_ride():
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Не авторизован'}), 401

    data = request.json
    ride_id = data.get('ride_id')
    seats = data.get('seats', 1)
    pickup_point = data.get('pickup_point', '')
    dropoff_point = data.get('dropoff_point', '')

    ride = db.session.get(Ride, ride_id)

    if not ride:
        return jsonify({'error': 'Поездка не найдена'}), 404
    if ride.seats < seats:
        return jsonify({'error': 'Недостаточно мест'}), 400

    existing = Booking.query.filter_by(ride_id=ride_id, passenger_id=user.id, status='pending').first()
    if existing:
        return jsonify({'error': 'У вас уже есть активная заявка'}), 400

    existing_approved = Booking.query.filter_by(ride_id=ride_id, passenger_id=user.id, status='approved').first()
    if existing_approved:
        return jsonify({'error': 'Вы уже забронировали место'}), 400

    booking = Booking(
        ride_id=ride_id,
        passenger_id=user.id,
        seats=seats,
        pickup_point=pickup_point,
        dropoff_point=dropoff_point,
        status='pending'
    )
    ride.seats -= seats
    db.session.add(booking)
    db.session.commit()

    message = f'Новая заявка от {user.name} на {seats} мест'
    if pickup_point:
        message += f'\n📍 Забрать: {pickup_point}'
    if dropoff_point:
        message += f'\n🏁 Высадить: {dropoff_point}'

    create_notification(
        ride.driver_id,
        'new_booking_request',
        '📋 Новая заявка',
        message,
        f'/ride/{ride_id}'
    )

    create_notification(
        user.id,
        'booking_request_sent',
        'Заявка отправлена',
        f'Ваша заявка отправлена водителю',
        f'/ride/{ride_id}'
    )

    return jsonify({'success': True})

@app.route('/api/popular_routes')
def popular_routes():
    """Топ популярных маршрутов"""
    # Анализируем историю поездок
    rides = Ride.query.all()
    routes = {}

    for ride in rides:
        key = f"{ride.from_place} → {ride.to_place}"
        if key in routes:
            routes[key] += 1
        else:
            routes[key] = 1

    # Сортируем и берем топ-5
    popular = sorted(routes.items(), key=lambda x: x[1], reverse=True)[:5]

    result = []
    for route, count in popular:
        result.append({
            'name': route,
            'count': count
        })

    return jsonify(result)

@app.route('/api/online_drivers')
def online_drivers():
    """Водители, которые сейчас активны"""
    # Активны те, кто создал поездку в ближайшие 2 часа
    two_hours_ago = datetime.now() - timedelta(hours=2)

    active_drivers = db.session.query(User).join(Ride).filter(
        Ride.departure_time >= two_hours_ago,
        Ride.departure_time <= datetime.now() + timedelta(hours=6),
        Ride.seats > 0,
        User.is_driver == True
    ).distinct().all()

    result = []
    for driver in active_drivers:
        # ИСПРАВЛЕНО: используем filter вместо filter_by для сложных условий
        driver_rides = Ride.query.filter(
            Ride.driver_id == driver.id,
            Ride.seats > 0
        ).count()

        result.append({
            'id': driver.id,
            'name': driver.name,
            'car': f"{driver.car_color} {driver.car_model}" if driver.car_model else None,
            'active_rides': driver_rides
        })

    return jsonify(result)

@app.route('/api/cancel_booking', methods=['POST'])
@login_required
def cancel_booking():
    user = get_current_user()
    data = request.json
    ride_id = data.get('ride_id')

    booking = Booking.query.filter_by(
        ride_id=ride_id,
        passenger_id=user.id,
        status='pending'
    ).first()

    if not booking:
        booking = Booking.query.filter_by(
            ride_id=ride_id,
            passenger_id=user.id,
            status='approved'
        ).first()

    if booking:
        booking.status = 'cancelled'
        ride = db.session.get(Ride, ride_id)
        ride.seats += booking.seats
        db.session.commit()

        create_notification(
            ride.driver_id,
            'booking_cancelled',
            'Бронирование отменено',
            f'{user.name} отменил(а) бронирование',
            f'/ride/{ride_id}'
        )

        return jsonify({'success': True})

    return jsonify({'error': 'Бронирование не найдено'}), 404

@app.route('/api/approve_booking/<int:booking_id>', methods=['POST'])
@login_required
def approve_booking(booking_id):
    user = get_current_user()
    booking = db.session.get(Booking, booking_id)

    if not booking:
        return jsonify({'error': 'Бронирование не найдено'}), 404

    ride = db.session.get(Ride, booking.ride_id)

    if ride.driver_id != user.id:
        return jsonify({'error': 'Нет доступа'}), 403

    if booking.status != 'pending':
        return jsonify({'error': 'Уже обработано'}), 400

    booking.status = 'approved'
    booking.processed_at = datetime.now()
    db.session.commit()

    create_notification(
        booking.passenger_id,
        'booking_approved',
        '✅ Заявка подтверждена',
        f'Водитель подтвердил вашу заявку на {booking.seats} мест',
        f'/ride/{ride.id}'
    )

    return jsonify({'success': True})

@app.route('/api/reject_booking/<int:booking_id>', methods=['POST'])
@login_required
def reject_booking(booking_id):
    user = get_current_user()
    booking = db.session.get(Booking, booking_id)

    if not booking:
        return jsonify({'error': 'Бронирование не найдено'}), 404

    ride = db.session.get(Ride, booking.ride_id)

    if ride.driver_id != user.id:
        return jsonify({'error': 'Нет доступа'}), 403

    if booking.status != 'pending':
        return jsonify({'error': 'Уже обработано'}), 400

    ride.seats += booking.seats
    booking.status = 'rejected'
    booking.processed_at = datetime.now()
    db.session.commit()

    create_notification(
        booking.passenger_id,
        'booking_rejected',
        '❌ Заявка отклонена',
        f'Водитель отклонил вашу заявку',
        f'/ride/{ride.id}'
    )

    return jsonify({'success': True})

# ========== УВЕДОМЛЕНИЯ ==========
@app.route('/api/mark_notifications_read', methods=['POST'])
@login_required
def mark_notifications_read():
    user = get_current_user()
    Notification.query.filter_by(user_id=user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    return jsonify({'success': True})

# ========== РЕГУЛЯРНЫЕ ПОЕЗДКИ ==========
@app.route('/api/regular_rides', methods=['GET', 'POST'])
@login_required
def api_regular_rides():
    user = get_current_user()

    if request.method == 'POST':
        data = request.json
        regular = RegularRide(
            user_id=user.id,
            from_place=data['from_place'],
            to_place=data['to_place'],
            from_lat=data['from_lat'],
            from_lng=data['from_lng'],
            to_lat=data['to_lat'],
            to_lng=data['to_lng'],
            days_of_week=data['days'],
            time=data['time'],
            seats=data['seats'],
            price=data['price'],
            description=data.get('description', ''),
            advance_hours=data['advance']
        )
        db.session.add(regular)
        db.session.commit()

        create_notification(
            user.id,
            'regular_ride_created',
            'Регулярная поездка создана',
            f'Будет создаваться автоматически: {data["from_place"]} → {data["to_place"]}',
            '/regular_rides'
        )

        return jsonify({'success': True, 'id': regular.id})

    regulars = RegularRide.query.filter_by(user_id=user.id).all()
    result = []
    for r in regulars:
        result.append({
            'id': r.id,
            'from': r.from_place,
            'to': r.to_place,
            'days': r.days_of_week,
            'time': r.time,
            'seats': r.seats,
            'price': r.price,
            'advance': r.advance_hours,
            'is_active': r.is_active,
            'description': r.description,
            'last_created': r.last_created.strftime('%d.%m.%Y %H:%M') if r.last_created else None
        })
    return jsonify(result)

@app.route('/api/regular_rides/<int:ride_id>/toggle', methods=['POST'])
@login_required
def toggle_regular_ride(ride_id):
    user = get_current_user()
    ride = db.session.get(RegularRide, ride_id)

    if not ride or ride.user_id != user.id:
        return jsonify({'error': 'Нет доступа'}), 403

    ride.is_active = not ride.is_active
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/regular_rides/<int:ride_id>', methods=['DELETE'])
@login_required
def delete_regular_ride(ride_id):
    user = get_current_user()
    ride = db.session.get(RegularRide, ride_id)

    if not ride or ride.user_id != user.id:
        return jsonify({'error': 'Нет доступа'}), 403

    db.session.delete(ride)
    db.session.commit()
    return jsonify({'success': True})

# ========== ИЗБРАННОЕ ==========
@app.route('/api/add_favorite', methods=['POST'])
@login_required
def add_favorite():
    user = get_current_user()
    data = request.json

    fav = FavoriteRoute(
        user_id=user.id,
        from_place=data['from_place'],
        to_place=data['to_place'],
        from_lat=data['from_lat'],
        from_lng=data['from_lng'],
        to_lat=data['to_lat'],
        to_lng=data['to_lng'],
        name=data.get('name', 'Мой маршрут')
    )
    db.session.add(fav)
    db.session.commit()
    return jsonify({'success': True, 'id': fav.id})

@app.route('/api/delete_favorite/<int:fav_id>', methods=['DELETE'])
@login_required
def delete_favorite(fav_id):
    user = get_current_user()
    fav = db.session.get(FavoriteRoute, fav_id)

    if not fav or fav.user_id != user.id:
        return jsonify({'error': 'Нет доступа'}), 403

    db.session.delete(fav)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/search_favorite/<int:fav_id>')
def search_favorite(fav_id):
    fav = db.session.get(FavoriteRoute, fav_id)
    if not fav:
        return redirect('/search')
    return redirect(f'/search?from_lat={fav.from_lat}&from_lng={fav.from_lng}&to_lat={fav.to_lat}&to_lng={fav.to_lng}')

# ========== ЧАТ ==========
@app.route('/chat/<int:ride_id>')
@login_required
def chat(ride_id):
    user = get_current_user()
    ride = db.session.get(Ride, ride_id)

    if not ride:
        return "Поездка не найдена", 404

    driver = db.session.get(User, ride.driver_id)

    # Проверяем доступ
    if user.id != ride.driver_id and not Booking.query.filter_by(ride_id=ride_id, passenger_id=user.id).first():
        return "У вас нет доступа к этому чату", 403

    # Получаем все сообщения
    messages = Message.query.filter_by(ride_id=ride_id).order_by(Message.created_at).all()

    # Определяем с кем общается пользователь
    if user.id == ride.driver_id:
        # Водитель общается с пассажирами - берем первого пассажира для отображения
        booking = Booking.query.filter_by(ride_id=ride_id, status='approved').first()
        other_user = db.session.get(User, booking.passenger_id) if booking else None
        receiver_id = booking.passenger_id if booking else None
    else:
        # Пассажир общается с водителем
        other_user = driver
        receiver_id = ride.driver_id

    # Получаем всех участников для сайдбара
    participants = []

    # Добавляем водителя
    participants.append({
        'user': driver,
        'role': 'driver'
    })

    # Добавляем пассажиров
    bookings = Booking.query.filter_by(ride_id=ride_id, status='approved').all()
    for booking in bookings:
        passenger = db.session.get(User, booking.passenger_id)
        participants.append({
            'user': passenger,
            'role': 'passenger'
        })

    return render_template('chat.html',
                           ride=ride,
                           driver=driver,
                           messages=messages,
                           user=user,
                           other_user=other_user,
                           receiver_id=receiver_id,
                           participants=participants)

@app.route('/api/send_message', methods=['POST'])
@login_required
def send_message():
    user = get_current_user()
    data = request.json

    message = Message(
        ride_id=data['ride_id'],
        sender_id=user.id,
        receiver_id=data['receiver_id'],
        text=data['text']
    )
    db.session.add(message)
    db.session.commit()

    create_notification(data['receiver_id'], 'new_message', 'Новое сообщение',
                        f'{user.name}: {data["text"][:50]}...', f'/chat/{data["ride_id"]}')

    return jsonify({'success': True, 'message': {
        'id': message.id,
        'text': message.text,
        'created_at': message.created_at.strftime('%H:%M'),
        'sender_id': message.sender_id
    }})

@app.route('/api/get_messages/<int:ride_id>')
@login_required
def get_messages(ride_id):
    since = request.args.get('since', 0, type=int)
    messages = Message.query.filter(Message.ride_id == ride_id, Message.id > since).order_by(Message.created_at).all()

    result = [{
        'id': msg.id,
        'text': msg.text,
        'created_at': msg.created_at.strftime('%H:%M'),
        'sender_id': msg.sender_id
    } for msg in messages]

    return jsonify(result)

@app.route('/api/messages/read/<int:ride_id>', methods=['POST'])
@login_required
def mark_messages_read(ride_id):
    """Отметить все сообщения в чате как прочитанные"""
    user = get_current_user()

    # Отмечаем сообщения, где пользователь получатель
    Message.query.filter_by(
        ride_id=ride_id,
        receiver_id=user.id,
        is_read=False
    ).update({'is_read': True})

    db.session.commit()
    return jsonify({'success': True})

@app.route('/faq')
def faq():
    user = get_current_user()
    return render_template('faq.html', user=user)

@app.route('/safety')
def safety():
    user = get_current_user()
    return render_template('safety.html', user=user)

@app.route('/donate')
def donate():
    user = get_current_user()
    return render_template('donate.html', user=user)

if __name__ == '__main__':
    app.run(debug=True)