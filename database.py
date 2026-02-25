from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()
db.Model.metadata.extend_existing = True

class User(db.Model):
    __tablename__ = 'user'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    is_driver = db.Column(db.Boolean, default=False)
    car_model = db.Column(db.String(100))
    car_color = db.Column(db.String(50))
    car_number = db.Column(db.String(20))
    # Рейтинги
    driver_rating = db.Column(db.Float, default=5.0)  # Средний рейтинг как водителя
    passenger_rating = db.Column(db.Float, default=5.0)  # Средний рейтинг как пассажира
    driver_rating_count = db.Column(db.Integer, default=0)
    passenger_rating_count = db.Column(db.Integer, default=0)

    # Контактные данные
    contact_phone = db.Column(db.String(20))
    telegram = db.Column(db.String(100))
    telegram_chat_id = db.Column(db.String(100))
    telegram_code = db.Column(db.String(10))
    whatsapp = db.Column(db.String(20))

    # Новые поля для оптимизации
    last_seen = db.Column(db.DateTime, default=datetime.now)
    last_notification_check = db.Column(db.DateTime, default=datetime.now)

    created_at = db.Column(db.DateTime, default=datetime.now)

class Ride(db.Model):
    __tablename__ = 'ride'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    from_place = db.Column(db.String(200), nullable=False)
    to_place = db.Column(db.String(200), nullable=False)
    from_lat = db.Column(db.Float)
    from_lng = db.Column(db.Float)
    to_lat = db.Column(db.Float)
    to_lng = db.Column(db.Float)
    departure_time = db.Column(db.DateTime, nullable=False)
    seats = db.Column(db.Integer, default=4)
    price = db.Column(db.Integer, default=0)
    description = db.Column(db.String(500))
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.now)

    # Связи
    driver = db.relationship('User', foreign_keys=[driver_id], backref='drives', lazy='joined')
    bookings = db.relationship('Booking', back_populates='ride', lazy='joined', cascade='all, delete-orphan')
    messages = db.relationship('Message', backref='ride', lazy='dynamic')

class ChatGroup(db.Model):
    """Групповые чаты для поездок с несколькими пассажирами"""
    __tablename__ = 'chat_group'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    ride_id = db.Column(db.Integer, db.ForeignKey('ride.id'))
    name = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.now)

    # Связи
    ride = db.relationship('Ride', backref='chat_group')
    participants = db.relationship('ChatParticipant', back_populates='group')
    messages = db.relationship('GroupMessage', backref='group')

class ChatParticipant(db.Model):
    """Участники группового чата"""
    __tablename__ = 'chat_participant'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('chat_group.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    joined_at = db.Column(db.DateTime, default=datetime.now)
    last_read = db.Column(db.DateTime, default=datetime.now)

    # Связи
    group = db.relationship('ChatGroup', back_populates='participants')
    user = db.relationship('User')

class GroupMessage(db.Model):
    """Сообщения в групповом чате"""
    __tablename__ = 'group_message'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('chat_group.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    # Связи
    user = db.relationship('User')

class SupportTicket(db.Model):
    """Обращения в поддержку"""
    __tablename__ = 'support_ticket'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    subject = db.Column(db.String(200))
    message = db.Column(db.Text)
    status = db.Column(db.String(20), default='open')  # open, in_progress, closed
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    # Связи
    user = db.relationship('User')
    messages = db.relationship('SupportMessage', backref='ticket')

class SupportMessage(db.Model):
    """Сообщения в тикете поддержки"""
    __tablename__ = 'support_message'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('support_ticket.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    text = db.Column(db.Text, nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

class News(db.Model):
    """Новости и статьи"""
    __tablename__ = 'news'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    excerpt = db.Column(db.String(500))
    image = db.Column(db.String(200))
    category = db.Column(db.String(50))  # news, update, ferry, tips
    views = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

class SiteStats(db.Model):
    """Статистика сайта"""
    __tablename__ = 'site_stats'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    total_rides = db.Column(db.Integer, default=0)
    total_drivers = db.Column(db.Integer, default=0)
    total_passengers = db.Column(db.Integer, default=0)
    avg_search_time = db.Column(db.Integer, default=15)  # в минутах
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

class Booking(db.Model):
    __tablename__ = 'booking'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    ride_id = db.Column(db.Integer, db.ForeignKey('ride.id'))
    passenger_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    seats = db.Column(db.Integer, default=1)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected, cancelled
    pickup_point = db.Column(db.String(200))
    dropoff_point = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.now)
    processed_at = db.Column(db.DateTime)

    # Связи
    passenger = db.relationship('User', foreign_keys=[passenger_id], lazy='joined')
    ride = db.relationship('Ride', foreign_keys=[ride_id], back_populates='bookings')

class Message(db.Model):
    __tablename__ = 'message'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    ride_id = db.Column(db.Integer, db.ForeignKey('ride.id'))
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    text = db.Column(db.String(500), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

class Notification(db.Model):
    __tablename__ = 'notification'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    type = db.Column(db.String(50))
    title = db.Column(db.String(200))
    text = db.Column(db.String(500))
    link = db.Column(db.String(200))
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

class Blacklist(db.Model):
    """Черный список - водитель блокирует пассажира"""
    __tablename__ = 'blacklist'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # Кто заблокировал
    passenger_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # Кого заблокировали
    reason = db.Column(db.String(200))  # Причина блокировки
    created_at = db.Column(db.DateTime, default=datetime.now)

class DriverRating(db.Model):
    """Рейтинг водителя (от пассажиров)"""
    __tablename__ = 'driver_rating'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    ride_id = db.Column(db.Integer, db.ForeignKey('ride.id'))
    driver_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    passenger_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    rating = db.Column(db.Integer)  # 1-5
    comment = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.now)

class PassengerRating(db.Model):
    """Рейтинг пассажира (от водителей)"""
    __tablename__ = 'passenger_rating'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    ride_id = db.Column(db.Integer, db.ForeignKey('ride.id'))
    driver_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    passenger_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    rating = db.Column(db.Integer)  # 1-5
    comment = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.now)

class FavoriteDriver(db.Model):
    """Избранные водители (подписка)"""
    __tablename__ = 'favorite_driver'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    passenger_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    driver_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.now)

class FavoriteRoute(db.Model):
    __tablename__ = 'favorite_route'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    from_place = db.Column(db.String(200))
    to_place = db.Column(db.String(200))
    from_lat = db.Column(db.Float)
    from_lng = db.Column(db.Float)
    to_lat = db.Column(db.Float)
    to_lng = db.Column(db.Float)
    name = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.now)

class RegularRide(db.Model):
    __tablename__ = 'regular_ride'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    from_place = db.Column(db.String(200), nullable=False)
    to_place = db.Column(db.String(200), nullable=False)
    from_lat = db.Column(db.Float)
    from_lng = db.Column(db.Float)
    to_lat = db.Column(db.Float)
    to_lng = db.Column(db.Float)
    days_of_week = db.Column(db.String(50))
    time = db.Column(db.String(5))
    seats = db.Column(db.Integer, default=4)
    price = db.Column(db.Integer, default=0)
    description = db.Column(db.String(500))
    is_active = db.Column(db.Boolean, default=True)
    advance_hours = db.Column(db.Integer, default=24)
    last_created = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.now)