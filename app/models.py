from email.policy import default

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    date = db.Column(db.DateTime, default=db.func.now())
    admin = db.Column(db.Boolean)

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
    text = db.Column(db.Text, nullable=False)
    user = db.relationship('User', backref='law')
    party = db.relationship('Party', backref='law')


class Government(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    form = db.Column(db.String(64), nullable=False, default='democracy')  # democracy / autocracy / oligarchy
    leader_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # глава государства
    description = db.Column(db.Text, default="")

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