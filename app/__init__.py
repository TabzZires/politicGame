from flask_login import LoginManager

from .law_parser import init_law_system
from .models import db, User
from flask import Flask
from flask_migrate import Migrate

login_manager = LoginManager()
migrate = Migrate()


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_pyfile('config.py')

    db.init_app(app)
    init_law_system(app, db)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'users.login'  # редирект при доступе без входа

    from .views import main, users, parties, polls, laws
    app.register_blueprint(main.bp)    # добавь
    app.register_blueprint(users.bp)
    app.register_blueprint(parties.bp)
    app.register_blueprint(polls.bp)
    app.register_blueprint(laws.bp)

    return app


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
