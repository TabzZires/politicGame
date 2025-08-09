# law_words.py - Updated for universal parser compatibility

from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class LawWord:
    """Represents a draggable word in the law constructor"""
    text: str
    type: str
    category: str = ""
    description: str = ""
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class LawWordsProvider:
    """Provider for law construction words - configurable and extensible"""

    def __init__(self, language: str = 'russian'):
        self.language = language
        self.words = self._get_default_words(language)

    def _get_default_words(self, language: str) -> List[LawWord]:
        """Get default words for a language"""
        if language == 'russian':
            return self._get_russian_words()
        elif language == 'english':
            return self._get_english_words()
        else:
            return self._get_universal_words()

    def _get_russian_words(self) -> List[LawWord]:
        """Russian law construction words"""
        return [
            # Субъекты
            LawWord("Пользователь", "subject", "Субъекты", "Обычный пользователь системы"),
            LawWord("Правитель", "subject", "Субъекты", "Администратор или правитель"),
            LawWord("Администратор", "subject", "Субъекты", "Системный администратор"),

            # Условия
            LawWord("член партии", "condition", "Условия", "Является членом политической партии"),
            LawWord("имеет право", "condition", "Условия", "Имеет базовое право"),
            LawWord("с рейтингом >", "condition", "Условия", "Рейтинг больше указанного"),
            LawWord("с рейтингом <", "condition", "Условия", "Рейтинг меньше указанного"),
            LawWord("с рейтингом >=", "condition", "Условия", "Рейтинг больше или равен"),
            LawWord("с рейтингом <=", "condition", "Условия", "Рейтинг меньше или равен"),
            LawWord("с рейтингом ==", "condition", "Условия", "Рейтинг равен указанному"),

            # Действия
            LawWord("голосовать", "action", "Действия", "Участвовать в голосованиях"),
            LawWord("создавать законы", "action", "Действия", "Создавать новые законы"),
            LawWord("создавать партии", "action", "Действия", "Основывать политические партии"),
            LawWord("быть лидером партии", "action", "Действия", "Возглавлять партию"),
            LawWord("удалять законы", "action", "Действия", "Удалять существующие законы"),
            LawWord("модерировать", "action", "Действия", "Модерировать контент"),

            # Модификаторы
            LawWord("если", "extra", "Модификаторы", "Условное выражение"),
            LawWord("и", "extra", "Модификаторы", "Логическое И"),
            LawWord("или", "extra", "Модификаторы", "Логическое ИЛИ"),
            LawWord("не", "extra", "Модификаторы", "Логическое НЕ"),

            # Операторы сравнения
            LawWord(">", "extra", "Операторы", "Больше"),
            LawWord("<", "extra", "Операторы", "Меньше"),
            LawWord(">=", "extra", "Операторы", "Больше или равно"),
            LawWord("<=", "extra", "Операторы", "Меньше или равно"),
            LawWord("==", "extra", "Операторы", "Равно"),
            LawWord("!=", "extra", "Операторы", "Не равно"),

            # Плейсхолдеры
            LawWord("[ЧИСЛО]", "placeholder", "Параметры", "Числовое значение"),
            LawWord("[СТРОКА]", "placeholder", "Параметры", "Текстовое значение"),
            LawWord("[ПОЛЬЗОВАТЕЛЬ]", "placeholder", "Параметры", "Текстовое значение"),
            LawWord("[ПАРТИЯ]", "placeholder", "Параметры", "Текстовое значение")]