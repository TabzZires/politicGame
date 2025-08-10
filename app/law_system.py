# law_system.py - Модульная система для создания и выполнения законов

import ast
import inspect
from typing import Dict, List, Any, Callable, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from abc import ABC, abstractmethod


# ============================================================================
# БАЗОВЫЕ КЛАССЫ И ИНТЕРФЕЙСЫ
# ============================================================================

@dataclass
class LawContext:
    """Контекст выполнения закона с данными о пользователе, действии и времени"""
    user_id: int
    action: str
    timestamp: datetime
    data: Dict[str, Any]
    session: Any  # Flask session или аналог


class LawValidator:
    """Валидатор безопасности для кода законов"""

    ALLOWED_IMPORTS = {
        'datetime', 'timedelta', 'math', 're', 'json'
    }

    # Updated for Python 3.8+ compatibility - removed ast.Exec and ast.Eval
    FORBIDDEN_NODES = {
        ast.Import, ast.ImportFrom, ast.Delete, ast.Global, ast.Nonlocal
    }

    FORBIDDEN_NAMES = {
        'exec', 'eval', 'compile', '__import__', 'open',
        'file', 'input', 'raw_input', 'reload', 'vars',
        'globals', 'locals', 'dir', 'getattr', 'setattr',
        'delattr', 'hasattr'
    }

    @classmethod
    def validate_code(cls, code: str) -> tuple[bool, str]:
        """Проверяет код закона на безопасность"""
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, f"Синтаксическая ошибка: {e}"

        for node in ast.walk(tree):
            # Проверка запрещенных узлов
            if type(node) in cls.FORBIDDEN_NODES:
                return False, f"Запрещенная операция: {type(node).__name__}"

            # Проверка запрещенных имен
            if isinstance(node, ast.Name) and node.id in cls.FORBIDDEN_NAMES:
                return False, f"Запрещенное имя: {node.id}"

            # Проверка атрибутов
            if isinstance(node, ast.Attribute):
                if node.attr.startswith('_'):
                    return False, f"Доступ к приватным атрибутам запрещен: {node.attr}"

            # Проверка вызовов функций exec и eval
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in ['exec', 'eval', 'compile']:
                    return False, f"Запрещенный вызов функции: {node.func.id}"

        return True, "OK"


class LawAPI:
    """API для использования в законах"""

    def __init__(self, context: LawContext, db_session):
        self.context = context
        self.db = db_session
        self._cache = {}

    def get_user(self, user_id: int = None) -> Optional[Dict]:
        """Получить данные пользователя"""
        uid = user_id or self.context.user_id
        if uid not in self._cache:
            from .models import User
            user = User.query.get(uid)
            self._cache[uid] = {
                'id': user.id,
                'username': user.username,
                'party_id': user.party_id,
                'date': user.date,
                'admin': user.admin
            } if user else None
        return self._cache[uid]

    def get_party(self, party_id: int) -> Optional[Dict]:
        """Получить данные партии"""
        from .models import Party
        party = Party.query.get(party_id)
        return {
            'id': party.id,
            'name': party.name,
            'count': party.count,
            'leader_id': party.leader_id
        } if party else None

    def count_users_where(self, **conditions) -> int:
        """Подсчитать пользователей по условиям"""
        from .models import User
        query = User.query
        for field, value in conditions.items():
            if hasattr(User, field):
                query = query.filter(getattr(User, field) == value)
        return query.count()

    def get_government(self) -> Dict:
        """Получить данные правительства"""
        from .models import Government
        gov = Government.query.first()
        return {
            'form': gov.form,
            'leader_id': gov.leader_id,
            'description': gov.description
        } if gov else {'form': 'democracy', 'leader_id': None, 'description': ''}

    def log_action(self, action: str, details: str = ""):
        """Логирование действий закона"""
        print(f"[LAW LOG] {datetime.now()}: {action} - {details}")


# ============================================================================
# СИСТЕМА ВЫПОЛНЕНИЯ ЗАКОНОВ
# ============================================================================

class LawExecutor:
    """Исполнитель законов с песочницей"""

    def __init__(self, db_session):
        self.db_session = db_session

    def execute_law(self, law_code: str, context: LawContext) -> Dict[str, Any]:
        """Выполняет код закона в безопасной среде"""

        # Валидация кода
        is_valid, error_msg = LawValidator.validate_code(law_code)
        if not is_valid:
            return {
                'success': False,
                'error': f'Код закона не прошел проверку безопасности: {error_msg}',
                'result': None
            }

        # Создание безопасного пространства имен
        law_api = LawAPI(context, self.db_session)

        # Updated builtins for Python 3.12
        safe_builtins = {
            'len': len, 'str': str, 'int': int, 'float': float, 'bool': bool,
            'list': list, 'dict': dict, 'set': set, 'tuple': tuple,
            'range': range, 'enumerate': enumerate, 'zip': zip,
            'map': map, 'filter': filter, 'max': max, 'min': min,
            'sum': sum, 'abs': abs, 'round': round, 'sorted': sorted
        }

        safe_globals = {
            '__builtins__': safe_builtins,
            'datetime': datetime,
            'timedelta': timedelta,
            'api': law_api,
            'context': context,
            'True': True,
            'False': False,
            'None': None
        }

        safe_locals = {}

        try:
            # Компиляция и выполнение
            compiled_code = compile(law_code, '<law>', 'exec')
            exec(compiled_code, safe_globals, safe_locals)

            # Получение результата (функция apply должна быть определена в коде)
            if 'apply' not in safe_locals:
                return {
                    'success': False,
                    'error': 'Закон должен содержать функцию apply()',
                    'result': None
                }

            apply_func = safe_locals['apply']
            result = apply_func()

            return {
                'success': True,
                'error': None,
                'result': result
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'Ошибка выполнения: {str(e)}',
                'result': None
            }


# ============================================================================
# СИСТЕМА ТРИГГЕРОВ И СОБЫТИЙ
# ============================================================================

class LawTrigger(ABC):
    """Базовый класс для триггеров законов"""

    @abstractmethod
    def should_trigger(self, context: LawContext) -> bool:
        pass


class ActionTrigger(LawTrigger):
    """Триггер по действию пользователя"""

    def __init__(self, actions: List[str]):
        self.actions = actions

    def should_trigger(self, context: LawContext) -> bool:
        return context.action in self.actions


class TimeTrigger(LawTrigger):
    """Триггер по времени"""

    def __init__(self, schedule: str):
        self.schedule = schedule  # например: "daily", "weekly", "monthly"

    def should_trigger(self, context: LawContext) -> bool:
        # Упрощенная реализация
        return context.action == 'time_check'


class ConditionalTrigger(LawTrigger):
    """Триггер по условию"""

    def __init__(self, condition_func: Callable[[LawContext], bool]):
        self.condition_func = condition_func

    def should_trigger(self, context: LawContext) -> bool:
        try:
            return self.condition_func(context)
        except:
            return False


# ============================================================================
# МЕНЕДЖЕР ЗАКОНОВ
# ============================================================================

class LawManager:
    """Центральный менеджер для управления законами"""

    def __init__(self, db_session):
        self.db_session = db_session
        self.executor = LawExecutor(db_session)
        self.active_laws: Dict[int, Dict] = {}

    def register_law(self, law_id: int, law_data: Dict):
        """Регистрирует закон в системе"""
        self.active_laws[law_id] = {
            'code': law_data['code'],
            'triggers': law_data.get('triggers', []),
            'active': law_data.get('active', True),
            'metadata': law_data.get('metadata', {})
        }

    def trigger_laws(self, context: LawContext) -> List[Dict]:
        """Запускает все подходящие законы"""
        results = []

        for law_id, law_data in self.active_laws.items():
            if not law_data['active']:
                continue

            # Проверка триггеров
            should_execute = False
            for trigger in law_data['triggers']:
                if trigger.should_trigger(context):
                    should_execute = True
                    break

            if should_execute:
                result = self.executor.execute_law(law_data['code'], context)
                result['law_id'] = law_id
                results.append(result)

        return results

    def get_law_status(self, law_id: int) -> Dict:
        """Получить статус закона"""
        if law_id in self.active_laws:
            return {
                'active': self.active_laws[law_id]['active'],
                'metadata': self.active_laws[law_id]['metadata']
            }
        return {'active': False, 'metadata': {}}


# ============================================================================
# ПРИМЕРЫ ЗАКОНОВ
# ============================================================================

EXAMPLE_LAWS = {
    'voting_law': '''
# Закон о голосовании - только члены партий могут голосовать
def apply():
    user = api.get_user()

    if context.action == 'vote':
        if not user or not user['party_id']:
            api.log_action("Отклонено голосование", f"Пользователь {user['username']} не состоит в партии")
            return {
                'action': 'deny',
                'reason': 'Только члены партий могут голосовать'
            }

    return {'action': 'allow'}
''',

    'term_limit_law': '''
# Закон об ограничении срока правления
def apply():
    gov = api.get_government()

    if context.action == 'check_term_limits':
        if gov['leader_id']:
            leader = api.get_user(gov['leader_id'])
            # Проверяем, сколько лидер находится у власти
            # (упрощенная логика)

            api.log_action("Проверка срока правления", f"Лидер: {leader['username']}")

            return {
                'action': 'info',
                'message': f"Текущий лидер: {leader['username']}"
            }

    return {'action': 'no_action'}
''',

    'party_creation_law': '''
# Закон о создании партий - минимум 3 участника
def apply():
    if context.action == 'create_party':
        founding_members = context.data.get('founding_members', [])

        if len(founding_members) < 3:
            api.log_action("Отклонено создание партии", f"Недостаточно учредителей: {len(founding_members)}")
            return {
                'action': 'deny',
                'reason': 'Для создания партии необходимо минимум 3 учредителя'
            }

        api.log_action("Разрешено создание партии", f"Учредителей: {len(founding_members)}")
        return {'action': 'allow'}

    return {'action': 'no_action'}
'''
}


# ============================================================================
# ИНТЕГРАЦИЯ С FLASK
# ============================================================================

def init_law_system(app, db):
    """Инициализация системы законов"""
    law_manager = LawManager(db.session)
    app.law_manager = law_manager

    # Загрузка активных законов из базы данных
    with app.app_context():
        from .models import Law
        active_laws = Law.query.filter_by(active=True).all()

        for law in active_laws:
            triggers = []
            # Здесь можно парсить метаданные закона для создания триггеров
            if hasattr(law, 'triggers') and law.triggers:  # предполагаем, что есть поле triggers в модели
                # Парсинг триггеров из JSON или другого формата
                pass

            law_manager.register_law(law.id, {
                'code': law.text,
                'triggers': triggers,
                'active': True,
                'metadata': {
                    'name': law.name,
                    'author_id': law.user_id,
                    'party_id': law.party_id
                }
            })


def execute_laws_for_action(app, user_id: int, action: str, data: Dict = None):
    """Вспомогательная функция для выполнения законов при действии"""
    if not hasattr(app, 'law_manager'):
        return []

    context = LawContext(
        user_id=user_id,
        action=action,
        timestamp=datetime.now(),
        data=data or {},
        session=None
    )

    return app.law_manager.trigger_laws(context)