# law_integration.py - Утилиты для интеграции законов в представления

from flask import current_app, flash, request
from flask_login import current_user
from functools import wraps
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
import json


class LawIntegrationError(Exception):
    """Исключение для ошибок интеграции законов"""
    pass


def check_laws(action: str, data: Dict = None, user_id: int = None):
    """
    Декоратор для проверки законов перед выполнением действия

    Использование:
    @check_laws('vote', {'poll_id': 123})
    def vote_function():
        # Ваш код
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Определяем ID пользователя
            uid = user_id if user_id is not None else (current_user.id if current_user.is_authenticated else None)

            # Получаем дополнительные данные из kwargs если они не переданы
            law_data = data or {}
            if not law_data and kwargs:
                law_data = kwargs.copy()

            # Выполняем проверку законов
            if hasattr(current_app, 'trigger_laws'):
                try:
                    results = current_app.trigger_laws(uid, action, law_data)

                    # Проверяем результаты
                    for result in results:
                        if result.get('success') and result.get('result'):
                            law_result = result['result']

                            if law_result.get('action') == 'deny':
                                reason = law_result.get('reason', 'Действие запрещено законом')
                                flash(f"❌ {reason}", 'error')
                                raise LawIntegrationError(reason)

                            elif law_result.get('action') == 'modify':
                                # Применяем модификации к kwargs
                                changes = law_result.get('changes', {})
                                kwargs.update(changes)
                                flash("🔄 Действие было изменено согласно законам", 'info')

                            elif law_result.get('action') == 'info':
                                message = law_result.get('message', 'Информация от системы законов')
                                flash(f"ℹ️ {message}", 'info')

                except LawIntegrationError:
                    raise
                except Exception as e:
                    # Логируем ошибку, но не блокируем действие
                    print(f"Ошибка при проверке законов: {e}")

            # Выполняем оригинальную функцию
            return func(*args, **kwargs)

        return wrapper

    return decorator


class LawChecker:
    """Класс для проверки законов без декораторов"""

    @staticmethod
    def check(action: str, data: Dict = None, user_id: int = None) -> Dict[str, Any]:
        """
        Проверяет законы для действия и возвращает результат

        Возвращает:
        {
            'allowed': bool,
            'reason': str,
            'modifications': dict,
            'info_messages': list
        }
        """
        uid = user_id if user_id is not None else (current_user.id if current_user.is_authenticated else None)
        law_data = data or {}

        result = {
            'allowed': True,
            'reason': None,
            'modifications': {},
            'info_messages': []
        }

        if not hasattr(current_app, 'trigger_laws'):
            return result

        try:
            results = current_app.trigger_laws(uid, action, law_data)

            for law_result in results:
                if law_result.get('success') and law_result.get('result'):
                    lr = law_result['result']

                    if lr.get('action') == 'deny':
                        result['allowed'] = False
                        result['reason'] = lr.get('reason', 'Действие запрещено законом')
                        break

                    elif lr.get('action') == 'modify':
                        changes = lr.get('changes', {})
                        result['modifications'].update(changes)

                    elif lr.get('action') == 'info':
                        message = lr.get('message', 'Информация от системы законов')
                        result['info_messages'].append(message)

        except Exception as e:
            print(f"Ошибка при проверке законов: {e}")

        return result

    @staticmethod
    def flash_results(check_result: Dict[str, Any]):
        """Отображает результаты проверки через flash сообщения"""
        if not check_result['allowed']:
            flash(f"❌ {check_result['reason']}", 'error')

        if check_result['modifications']:
            flash("🔄 Действие было изменено согласно законам", 'info')

        for message in check_result['info_messages']:
            flash(f"ℹ️ {message}", 'info')


# Примеры интеграции для различных представлений

# ============================================================================
# ИНТЕГРАЦИЯ С ГОЛОСОВАНИЕМ
# ============================================================================

def integrate_voting_laws():
    """
    Пример интеграции в polls/views.py:

    from .law_integration import LawChecker

    @bp.route('/<int:poll_id>/vote', methods=['GET', 'POST'])
    @login_required
    def vote(poll_id):
        poll = Poll.query.get_or_404(poll_id)

        # Проверка законов
        law_check = LawChecker.check('vote', {
            'poll_id': poll_id,
            'poll_type': poll.type,
            'user_party_id': current_user.party_id
        })

        if not law_check['allowed']:
            LawChecker.flash_results(law_check)
            return redirect(url_for('polls.poll_detail', poll_id=poll_id))

        # Применяем модификации если есть
        if law_check['modifications']:
            # Например, закон может изменить вес голоса
            vote_weight = law_check['modifications'].get('vote_weight', 1)

        # Отображаем информационные сообщения
        LawChecker.flash_results(law_check)

        # Остальная логика голосования...
    """
    pass


# ============================================================================
# ИНТЕГРАЦИЯ С ПАРТИЯМИ
# ============================================================================

def integrate_party_laws():
    """
    Пример интеграции в parties/views.py:

    @bp.route('/create', methods=['GET', 'POST'])
    @login_required
    def create_party():
        form = CreatePartyForm()

        if form.validate_on_submit():
            # Проверка законов для создания партии
            law_check = LawChecker.check('create_party', {
                'party_name': form.name.data,
                'founding_members': [current_user.id],
                'creator_id': current_user.id
            })

            if not law_check['allowed']:
                LawChecker.flash_results(law_check)
                return render_template('parties/create.html', form=form)

            # Создание партии с учетом модификаций
            party_data = {
                'name': form.name.data,
                'leader_id': current_user.id
            }

            # Применяем модификации от законов
            party_data.update(law_check['modifications'])

            party = Party(**party_data)
            db.session.add(party)
            db.session.commit()

            LawChecker.flash_results(law_check)
            return redirect(url_for('parties.party_profile', party_id=party.id))
    """
    pass


# ============================================================================
# ИНТЕГРАЦИЯ С ПОЛЬЗОВАТЕЛЯМИ
# ============================================================================

def integrate_user_laws():
    """
    Пример интеграции в users/views.py:

    @bp.route('/register', methods=['GET', 'POST'])
    def register():
        form = RegisterForm()

        if form.validate_on_submit():
            # Проверка законов для регистрации
            law_check = LawChecker.check('user_register', {
                'username': form.username.data,
                'timestamp': datetime.utcnow(),
                'ip_address': request.remote_addr
            })

            if not law_check['allowed']:
                LawChecker.flash_results(law_check)
                return render_template('users/register.html', form=form)

            # Создание пользователя с модификациями
            user_data = {
                'username': form.username.data,
                'password': generate_password_hash(form.password.data)
            }

            # Законы могут добавить дополнительные поля
            user_data.update(law_check['modifications'])

            user = User(**user_data)
            db.session.add(user)
            db.session.commit()

            LawChecker.flash_results(law_check)
            return redirect(url_for('users.login'))
    """
    pass


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def get_user_permissions(user_id: int) -> Dict[str, bool]:
    """
    Получает разрешения пользователя на основе активных законов
    """
    permissions = {
        'can_vote': True,
        'can_create_party': True,
        'can_join_party': True,
        'can_create_poll': True,
        'can_run_for_leader': True
    }

    if not hasattr(current_app, 'trigger_laws'):
        return permissions

    # Проверяем каждое разрешение
    for permission, default_value in permissions.items():
        try:
            action = permission.replace('can_', '')
            results = current_app.trigger_laws(user_id, f'check_{action}', {'permission_check': True})

            for result in results:
                if result.get('success') and result.get('result'):
                    lr = result['result']
                    if lr.get('action') == 'deny':
                        permissions[permission] = False
                        break
        except:
            continue

    return permissions


def validate_law_triggers(triggers: List[Dict]) -> bool:
    """
    Валидирует корректность триггеров закона
    """
    valid_trigger_types = ['action', 'time', 'conditional']
    valid_schedules = ['daily', 'weekly', 'monthly']

    for trigger in triggers:
        if not isinstance(trigger, dict):
            return False

        trigger_type = trigger.get('type')
        if trigger_type not in valid_trigger_types:
            return False

        if trigger_type == 'action':
            actions = trigger.get('actions', [])
            if not isinstance(actions, list) or not actions:
                return False

        elif trigger_type == 'time':
            schedule = trigger.get('schedule')
            if schedule not in valid_schedules:
                return False

    return True


class LawExecutionTracker:
    """Отслеживает выполнение законов в реальном времени"""

    def __init__(self):
        self.executions = []

    def track_execution(self, law_id: int, result: Dict):
        """Отслеживает выполнение закона"""
        execution_data = {
            'law_id': law_id,
            'timestamp': datetime.utcnow(),
            'result': result,
            'success': result.get('success', False)
        }

        self.executions.append(execution_data)

        # Ограничиваем размер истории
        if len(self.executions) > 1000:
            self.executions = self.executions[-500:]

    def get_recent_executions(self, limit: int = 50) -> List[Dict]:
        """Получает недавние выполнения законов"""
        return self.executions[-limit:]

    def get_law_statistics(self, law_id: int) -> Dict:
        """Получает статистику выполнения конкретного закона"""
        law_executions = [e for e in self.executions if e['law_id'] == law_id]

        if not law_executions:
            return {'total': 0, 'successful': 0, 'failed': 0, 'success_rate': 0}

        total = len(law_executions)
        successful = sum(1 for e in law_executions if e['success'])
        failed = total - successful
        success_rate = (successful / total * 100) if total > 0 else 0

        return {
            'total': total,
            'successful': successful,
            'failed': failed,
            'success_rate': round(success_rate, 2)
        }


# Глобальный трекер выполнения
execution_tracker = LawExecutionTracker()


def init_law_integration(app):
    """Инициализирует интеграцию законов в приложение"""

    # Добавляем трекер в приложение
    app.law_execution_tracker = execution_tracker

    # Регистрируем хук для отслеживания выполнений
    original_trigger = getattr(app, 'trigger_laws', None)

    if original_trigger:
        def tracked_trigger_laws(user_id, action, data=None):
            results = original_trigger(user_id, action, data)

            # Отслеживаем каждое выполнение
            for result in results:
                execution_tracker.track_execution(result.get('law_id'), result)

            return results

        app.trigger_laws = tracked_trigger_laws

    # Добавляем функции в контекст шаблонов
    @app.template_global()
    def get_user_permissions_template(user_id):
        return get_user_permissions(user_id)

    @app.template_global()
    def check_law_permission(action, user_id=None):
        """Проверяет разрешение через законы в шаблоне"""
        uid = user_id if user_id is not None else (current_user.id if current_user.is_authenticated else None)

        if not uid:
            return False

        check_result = LawChecker.check(f'check_{action}', {'permission_check': True}, uid)
        return check_result['allowed']

    print("Интеграция законов инициализирована")