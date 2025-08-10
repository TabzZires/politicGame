from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate

from .law_system import init_law_system, execute_laws_for_action
from .models import db, User

login_manager = LoginManager()
migrate = Migrate()


def register_law_hooks(app):
    """Регистрирует хуки для автоматического выполнения законов при действиях пользователей"""

    @app.before_request
    def before_request():
        # Здесь можно добавить предварительные проверки
        pass

    @app.after_request
    def after_request(response):
        # Здесь можно добавить пост-обработку
        return response

    # Вспомогательная функция для выполнения законов
    def trigger_laws(user_id, action, data=None):
        """Запускает законы для конкретного действия"""
        try:
            results = execute_laws_for_action(app, user_id, action, data)

            # Обработка результатов
            for result in results:
                if result['success'] and result['result']:
                    law_result = result['result']

                    # Логирование результатов в базу данных
                    from .models import LawExecution
                    execution = LawExecution(
                        law_id=result['law_id'],
                        user_id=user_id,
                        action=action,
                        trigger_type='action',
                        success=True,
                        result=law_result,
                        completed_at=db.func.now()
                    )
                    db.session.add(execution)

                    # Обновление статистики закона
                    from .models import Law
                    law = Law.query.get(result['law_id'])
                    if law:
                        law.execution_count += 1
                        law.last_executed = db.func.now()

                    try:
                        db.session.commit()
                    except:
                        db.session.rollback()

            return results

        except Exception as e:
            print(f"Ошибка при выполнении законов: {e}")
            return []

    # Добавляем функцию в контекст приложения
    app.trigger_laws = trigger_laws


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Дополнительные шаблонные функции для использования в Jinja2
def register_template_functions(app):
    """Регистрирует дополнительные функции для шаблонов"""

    @app.template_global()
    def get_law_status(law_id):
        """Получить статус закона для шаблонов"""
        if hasattr(app, 'law_manager'):
            return app.law_manager.get_law_status(law_id)
        return {'active': False, 'metadata': {}}

    @app.template_filter()
    def format_law_result(result):
        """Форматирование результата закона для отображения"""
        if not result:
            return "Нет результата"

        action = result.get('action', 'unknown')

        if action == 'allow':
            return "✅ Разрешено"
        elif action == 'deny':
            reason = result.get('reason', 'Неизвестная причина')
            return f"❌ Отклонено: {reason}"
        elif action == 'info':
            message = result.get('message', 'Информация')
            return f"ℹ️ {message}"
        elif action == 'modify':
            return "🔄 Изменено"
        else:
            return f"❓ {action}"

    @app.template_filter()
    def law_trigger_description(triggers):
        """Описание триггеров закона"""
        if not triggers:
            return "Нет триггеров"

        descriptions = []
        for trigger in triggers:
            if trigger['type'] == 'action':
                actions = ', '.join(trigger.get('actions', []))
                descriptions.append(f"При действиях: {actions}")
            elif trigger['type'] == 'time':
                schedule = trigger.get('schedule', '')
                if schedule == 'daily':
                    descriptions.append("Ежедневно")
                elif schedule == 'weekly':
                    descriptions.append("Еженедельно")
                elif schedule == 'monthly':
                    descriptions.append("Ежемесячно")

        return "; ".join(descriptions) if descriptions else "Нет триггеров"


# Создание базовых шаблонов законов при инициализации
def create_default_templates(app):
    """Создает базовые шаблоны законов при первом запуске"""

    with app.app_context():
        from .models import LawTemplate

        # Проверяем, есть ли уже шаблоны
        if LawTemplate.query.count() > 0:
            return

        templates = [
            {
                'name': 'Закон о голосовании',
                'description': 'Ограничивает возможность голосования определенными условиями',
                'category': 'voting',
                'code_template': '''def apply():
    """
    {description}
    """
    user = api.get_user()

    if context.action == 'vote':
        if not user or not user['{required_field}']:
            api.log_action("Отклонено голосование", f"Пользователь не соответствует требованиям")
            return {
                'action': 'deny',
                'reason': '{deny_reason}'
            }

    return {'action': 'allow'}''',
                'parameters': [
                    {'name': 'description', 'type': 'text', 'default': 'Проверяет права на голосование',
                     'description': 'Описание закона'},
                    {'name': 'required_field', 'type': 'select', 'options': ['party_id', 'admin'],
                     'default': 'party_id', 'description': 'Требуемое поле'},
                    {'name': 'deny_reason', 'type': 'text', 'default': 'Не соответствует требованиям для голосования',
                     'description': 'Причина отказа'}
                ]
            },
            {
                'name': 'Закон о минимальном количестве участников',
                'description': 'Требует минимальное количество участников для действий',
                'category': 'membership',
                'code_template': '''def apply():
    """
    {description}
    """
    if context.action == '{target_action}':
        participants = context.data.get('{participants_field}', [])

        if len(participants) < {min_count}:
            api.log_action("Отклонено действие", f"Недостаточно участников: {len(participants)}")
            return {
                'action': 'deny',
                'reason': f'Требуется минимум {min_count} участников'
            }

    return {'action': 'allow'}''',
                'parameters': [
                    {'name': 'description', 'type': 'text', 'default': 'Проверяет минимальное количество участников',
                     'description': 'Описание закона'},
                    {'name': 'target_action', 'type': 'text', 'default': 'create_party',
                     'description': 'Целевое действие'},
                    {'name': 'participants_field', 'type': 'text', 'default': 'founding_members',
                     'description': 'Поле с участниками'},
                    {'name': 'min_count', 'type': 'number', 'default': 3, 'description': 'Минимальное количество'}
                ]
            },
            {
                'name': 'Закон о временных ограничениях',
                'description': 'Ограничивает действия по времени или периодичности',
                'category': 'time',
                'code_template': '''def apply():
    """
    {description}
    """
    from datetime import datetime, timedelta

    if context.action == '{target_action}':
        user = api.get_user()

        # Проверяем временные ограничения
        # Здесь может быть логика проверки последнего действия пользователя

        api.log_action("Проверка временных ограничений", f"Пользователь: {user['username']}")

        return {
            'action': 'info',
            'message': 'Временные ограничения проверены'
        }

    return {'action': 'no_action'}''',
                'parameters': [
                    {'name': 'description', 'type': 'text', 'default': 'Проверяет временные ограничения',
                     'description': 'Описание закона'},
                    {'name': 'target_action', 'type': 'text', 'default': 'vote', 'description': 'Целевое действие'},
                    {'name': 'time_limit', 'type': 'number', 'default': 24,
                     'description': 'Временное ограничение в часах'}
                ]
            }
        ]

        for template_data in templates:
            template = LawTemplate(
                name=template_data['name'],
                description=template_data['description'],
                category=template_data['category'],
                code_template=template_data['code_template'],
                parameters=template_data['parameters']
            )
            db.session.add(template)

        try:
            db.session.commit()
            print("Созданы базовые шаблоны законов")
        except Exception as e:
            db.session.rollback()
            print(f"Ошибка при создании шаблонов: {e}")


# Инициализация дополнительных компонентов
def init_additional_components(app):
    """Инициализация дополнительных компонентов системы"""

    # Регистрация шаблонных функций
    register_template_functions(app)

    # Создание базовых шаблонов при первом запуске
    with app.app_context():
        create_default_templates(app)

    # Планировщик задач для периодического выполнения законов
    # (можно использовать APScheduler или Celery)
    init_scheduler(app)


def init_scheduler(app):
    """Инициализация планировщика для периодических законов"""

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger

        scheduler = BackgroundScheduler()

        # Ежедневная проверка законов
        scheduler.add_job(
            func=lambda: daily_law_check(app),
            trigger=CronTrigger(hour=0, minute=0),  # Каждый день в полночь
            id='daily_law_check'
        )

        # Еженедельная проверка
        scheduler.add_job(
            func=lambda: weekly_law_check(app),
            trigger=CronTrigger(day_of_week=0, hour=0, minute=0),  # Каждое воскресенье
            id='weekly_law_check'
        )

        scheduler.start()
        app.scheduler = scheduler

        print("Планировщик законов запущен")

    except ImportError:
        print("APScheduler не установлен. Периодические законы не будут работать.")
        print("Установите: pip install apscheduler")


def daily_law_check(app):
    """Ежедневная проверка и выполнение законов"""

    with app.app_context():
        try:
            # Выполняем все законы с ежедневным триггером
            results = execute_laws_for_action(app, user_id=None, action='time_check', data={'schedule': 'daily'})

            from .models import LawExecution, Law

            # Сохраняем результаты
            for result in results:
                execution = LawExecution(
                    law_id=result['law_id'],
                    user_id=None,
                    action='time_check',
                    trigger_type='scheduled_daily',
                    success=result['success'],
                    result=result.get('result'),
                    error_message=result.get('error'),
                    completed_at=db.func.now()
                )
                db.session.add(execution)

                # Обновляем статистику закона
                law = Law.query.get(result['law_id'])
                if law:
                    law.execution_count += 1
                    law.last_executed = db.func.now()

            db.session.commit()
            print(f"Выполнена ежедневная проверка законов. Результатов: {len(results)}")

        except Exception as e:
            print(f"Ошибка при ежедневной проверке законов: {e}")
            db.session.rollback()


def weekly_law_check(app):
    """Еженедельная проверка и выполнение законов"""

    with app.app_context():
        try:
            # Выполняем все законы с еженедельным триггером
            results = execute_laws_for_action(app, user_id=None, action='time_check', data={'schedule': 'weekly'})

            from .models import LawExecution, Law

            # Сохраняем результаты
            for result in results:
                execution = LawExecution(
                    law_id=result['law_id'],
                    user_id=None,
                    action='time_check',
                    trigger_type='scheduled_weekly',
                    success=result['success'],
                    result=result.get('result'),
                    error_message=result.get('error'),
                    completed_at=db.func.now()
                )
                db.session.add(execution)

                # Обновляем статистику закона
                law = Law.query.get(result['law_id'])
                if law:
                    law.execution_count += 1
                    law.last_executed = db.func.now()

            db.session.commit()
            print(f"Выполнена еженедельная проверка законов. Результатов: {len(results)}")

        except Exception as e:
            print(f"Ошибка при еженедельной проверке законов: {e}")
            db.session.rollback()


# Интеграция с основными действиями пользователей
def integrate_laws_with_actions():
    """Документация интеграции законов с действиями пользователей"""

    # Примеры интеграции в других представлениях:

    # В views/polls.py при голосовании:
    # from flask import current_app
    # results = current_app.trigger_laws(current_user.id, 'vote', {'poll_id': poll.id})
    # for result in results:
    #     if result['success'] and result['result'].get('action') == 'deny':
    #         flash(result['result'].get('reason', 'Действие запрещено законом'), 'error')
    #         return redirect(url_for('polls.poll_detail', poll_id=poll.id))

    # В views/parties.py при создании партии:
    # results = current_app.trigger_laws(current_user.id, 'create_party', {
    #     'party_name': form.name.data,
    #     'founding_members': [current_user.id]
    # })
    # for result in results:
    #     if result['success'] and result['result'].get('action') == 'deny':
    #         flash(result['result'].get('reason'), 'error')
    #         return render_template('parties/create.html', form=form)

    # В views/users.py при регистрации:
    # results = current_app.trigger_laws(None, 'user_register', {
    #     'username': form.username.data,
    #     'timestamp': datetime.utcnow()
    # })

    pass


# Дополнительная конфигурация для законов
class LawConfig:
    """Конфигурация системы законов"""

    # Максимальное время выполнения закона в секундах
    MAX_EXECUTION_TIME = 10

    # Максимальное количество законов, выполняемых за одно действие
    MAX_LAWS_PER_ACTION = 20

    # Включить детальное логирование
    DETAILED_LOGGING = True

    # Автоматическая деактивация законов при ошибках
    AUTO_DEACTIVATE_ON_ERROR = True

    # Количество ошибок подряд для автодеактивации
    ERROR_THRESHOLD = 5


def apply_law_config(app):
    """Применяет конфигурацию системы законов"""

    # Добавляем конфигурацию в приложение
    if not hasattr(app, 'law_config'):
        app.law_config = LawConfig()

    # Можно переопределить настройки из конфигурации Flask
    app.law_config.MAX_EXECUTION_TIME = app.config.get('LAW_MAX_EXECUTION_TIME', 10)
    app.law_config.MAX_LAWS_PER_ACTION = app.config.get('LAW_MAX_LAWS_PER_ACTION', 20)
    app.law_config.DETAILED_LOGGING = app.config.get('LAW_DETAILED_LOGGING', True)


# Модифицируем основную функцию создания приложения
def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_pyfile('config.py')

    db.init_app(app)
    migrate.init_app(app, db)

    # Инициализация системы законов
    init_law_system(app, db)

    # Применяем конфигурацию законов
    apply_law_config(app)

    login_manager.init_app(app)
    login_manager.login_view = 'users.login'

    from .views import main, users, parties, polls, laws, news
    app.register_blueprint(main.bp)
    app.register_blueprint(users.bp)
    app.register_blueprint(parties.bp)
    app.register_blueprint(polls.bp)
    app.register_blueprint(laws.bp)
    app.register_blueprint(news.bp)

    # Регистрация хуков для выполнения законов
    register_law_hooks(app)

    # Инициализация дополнительных компонентов
    init_additional_components(app)

    return app
