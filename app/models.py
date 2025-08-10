from email.policy import default
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import json

db = SQLAlchemy()


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    date = db.Column(db.DateTime, default=db.func.now())
    admin = db.Column(db.Boolean, default=False)

    party_id = db.Column(db.Integer, db.ForeignKey('party.id'))
    party = db.relationship(
        'Party',
        backref='members',
        foreign_keys=[party_id]
    )

    parties = db.relationship(
        'Party',
        backref='leader',
        lazy=True,
        foreign_keys='Party.leader_id'
    )

    votes = db.relationship('Vote', backref='voter', lazy=True)


class Party(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)
    count = db.Column(db.Integer, nullable=False, default=0)

    leader_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id', use_alter=True, name='fk_party_leader_id'),
        nullable=True
    )


class Poll(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(256), nullable=False)
    type = db.Column(db.String(16), nullable=False)  # 'vote' или 'suggest'
    start_date = db.Column(db.DateTime, default=db.func.now())
    end_date = db.Column(db.DateTime)

    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    party_id = db.Column(db.Integer, db.ForeignKey('party.id'))

    author = db.relationship('User', backref='polls')
    party = db.relationship('Party', backref='polls')

    options = db.relationship('Option', backref='poll', lazy=True)
    votes = db.relationship('Vote', backref='poll', lazy=True)
    suggestions = db.relationship('Suggestion', backref='poll', lazy=True)


class Option(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(256), nullable=False)
    poll_id = db.Column(db.Integer, db.ForeignKey('poll.id'), nullable=False)
    votes = db.relationship('Vote', backref='option', lazy=True)


class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    poll_id = db.Column(db.Integer, db.ForeignKey('poll.id'))
    option_id = db.Column(db.Integer, db.ForeignKey('option.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)


class Suggestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    poll_id = db.Column(db.Integer, db.ForeignKey('poll.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    text = db.Column(db.Text, nullable=False)
    user = db.relationship('User', backref='user')


class Law(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    party_id = db.Column(db.Integer, db.ForeignKey('party.id'))
    name = db.Column(db.Text, nullable=False)
    text = db.Column(db.Text, nullable=False)  # Python код закона

    # Новые поля для системы законов
    active = db.Column(db.Boolean, default=False)  # Активен ли закон
    triggers_json = db.Column(db.Text, default='[]')  # JSON с триггерами
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    activated_at = db.Column(db.DateTime, nullable=True)  # Когда закон был активирован

    # Поля для валидации и статуса
    validation_status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    validation_error = db.Column(db.Text, nullable=True)  # Ошибки валидации
    validated_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    validated_at = db.Column(db.DateTime, nullable=True)

    # Статистика выполнения
    execution_count = db.Column(db.Integer, default=0)
    last_executed = db.Column(db.DateTime, nullable=True)

    user = db.relationship('User', backref='laws', foreign_keys=[user_id])
    party = db.relationship('Party', backref='laws')
    validator = db.relationship('User', foreign_keys=[validated_by])

    executions = db.relationship('LawExecution', backref='law', lazy=True)

    @property
    def triggers(self):
        """Получить триггеры как список Python объектов"""
        try:
            return json.loads(self.triggers_json)
        except:
            return []

    @triggers.setter
    def triggers(self, value):
        """Установить триггеры из списка Python объектов"""
        self.triggers_json = json.dumps(value)

    def can_execute(self) -> bool:
        """Проверить, можно ли выполнять закон"""
        return self.active and self.validation_status == 'approved'


class LawExecution(db.Model):
    """Журнал выполнения законов"""
    id = db.Column(db.Integer, primary_key=True)
    law_id = db.Column(db.Integer, db.ForeignKey('law.id'), nullable=False)

    # Контекст выполнения
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    trigger_type = db.Column(db.String(50), nullable=False)

    # Результат выполнения
    success = db.Column(db.Boolean, nullable=False)
    result_json = db.Column(db.Text, nullable=True)  # JSON с результатом
    error_message = db.Column(db.Text, nullable=True)

    # Время выполнения
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    execution_time = db.Column(db.Float, nullable=True)  # в секундах

    user = db.relationship('User', backref='law_executions')

    @property
    def result(self):
        """Получить результат как Python объект"""
        try:
            return json.loads(self.result_json) if self.result_json else None
        except:
            return None

    @result.setter
    def result(self, value):
        """Установить результат из Python объекта"""
        self.result_json = json.dumps(value) if value is not None else None


class LawTemplate(db.Model):
    """Шаблоны законов для упрощения создания"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)  # voting, governance, economy, etc.

    code_template = db.Column(db.Text, nullable=False)  # Шаблон кода с плейсхолдерами
    parameters_json = db.Column(db.Text, default='[]')  # Параметры для настройки

    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Статистика использования
    usage_count = db.Column(db.Integer, default=0)

    creator = db.relationship('User', backref='law_templates')

    @property
    def parameters(self):
        """Получить параметры как список Python объектов"""
        try:
            return json.loads(self.parameters_json)
        except:
            return []

    @parameters.setter
    def parameters(self, value):
        """Установить параметры из списка Python объектов"""
        self.parameters_json = json.dumps(value)


class Government(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    form = db.Column(db.String(64), nullable=False, default='democracy')  # democracy / autocracy / oligarchy
    leader_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # глава государства
    description = db.Column(db.Text, default="")

    # Новые поля для системы законов
    constitution_text = db.Column(db.Text, default="")  # Основной закон
    law_approval_threshold = db.Column(db.Float, default=0.5)  # Порог для принятия законов

    leader = db.relationship('User', backref='leadership', foreign_keys=[leader_id])


class News(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text)
    desc = db.Column(db.Text)
    text = db.Column(db.Text)

    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    party_id = db.Column(db.Integer, db.ForeignKey('party.id'))

    author = db.relationship('User', backref='news')
    party = db.relationship('Party', backref='news')


class LawVote(db.Model):
    """Голосования за законы"""
    id = db.Column(db.Integer, primary_key=True)
    law_id = db.Column(db.Integer, db.ForeignKey('law.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    vote = db.Column(db.String(10), nullable=False)  # 'for', 'against', 'abstain'
    voted_at = db.Column(db.DateTime, default=datetime.utcnow)

    law = db.relationship('Law', backref='votes')
    user = db.relationship('User', backref='law_votes')

    __table_args__ = (db.UniqueConstraint('law_id', 'user_id', name='unique_law_vote'),)