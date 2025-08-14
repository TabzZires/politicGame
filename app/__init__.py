from flask_login import LoginManager

from .models import db, User, Law
from flask import Flask, before_render_template
from flask_migrate import Migrate

login_manager = LoginManager()
migrate = Migrate()


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_pyfile('config.py')

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'users.login'  # редирект при доступе без входа

    from .views import main, users, parties, polls, laws, news
    app.register_blueprint(main.bp)    # добавь
    app.register_blueprint(users.bp)
    app.register_blueprint(parties.bp)
    app.register_blueprint(polls.bp)
    app.register_blueprint(laws.bp)
    app.register_blueprint(news.bp)

    @app.before_request
    def law_activation():
        lawS = Law.query.all()
        for law in lawS:
            exec(law.text)

    return app


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
