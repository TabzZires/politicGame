# law_parser.py - Updated for Flask compatibility
import re
import json
import yaml
from typing import Dict, List, Any, Optional, Union, Callable, Type
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from abc import ABC, abstractmethod
from pathlib import Path


class TokenType(Enum):
    """Universal token types for law parsing"""
    SUBJECT = "subject"
    CONDITION = "condition"
    ACTION = "action"
    MODIFIER = "modifier"
    VALUE = "value"
    PLACEHOLDER = "placeholder"
    OPERATOR = "operator"
    DELIMITER = "delimiter"
    GROUP_START = "group_start"
    GROUP_END = "group_end"
    UNKNOWN = "unknown"


@dataclass
class Token:
    """Universal token representation"""
    type: TokenType
    value: str
    original: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    position: int = 0
    line: int = 1
    column: int = 1


@dataclass
class ActionRule:
    """Rule for specific actions - maintains compatibility with old system"""
    action_name: str
    subject_type: str
    conditions: List[Dict[str, Any]]
    allow: bool = True
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedLaw:
    """Universal parsed law representation"""
    raw_text: str
    tokens: List[Token]
    structure: Dict[str, Any]
    is_valid: bool
    errors: List[str]
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class LanguageConfig:
    """Configuration for language-specific parsing"""

    def __init__(self, config_data: Dict[str, Any]):
        self.language = config_data.get('language', 'universal')
        self.keywords = config_data.get('keywords', {})
        self.patterns = config_data.get('patterns', {})
        self.operators = config_data.get('operators', {})
        self.delimiters = config_data.get('delimiters', [';', ',', '.'])
        self.group_markers = config_data.get('group_markers', {'start': ['(', '['], 'end': [')', ']']})
        self.negation_words = config_data.get('negation_words', ['not', 'не'])
        self.conditional_words = config_data.get('conditional_words', ['if', 'если'])
        self.action_mappings = config_data.get('action_mappings', {})

    @classmethod
    def from_file(cls, config_path: Union[str, Path]) -> 'LanguageConfig':
        """Load configuration from file (JSON or YAML)"""
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(path, 'r', encoding='utf-8') as f:
            if path.suffix.lower() in ['.yml', '.yaml']:
                data = yaml.safe_load(f)
            else:
                data = json.load(f)

        return cls(data)

    @classmethod
    def create_default(cls, language: str = 'russian') -> 'LanguageConfig':
        """Create default configuration - maintains Russian as default for compatibility"""
        if language == 'russian':
            return cls({
                'language': 'russian',
                'keywords': {
                    'subjects': ['Пользователь', 'Правитель', 'Администратор'],
                    'conditions': ['член партии', 'имеет право', 'с рейтингом >', 'с рейтингом <'],
                    'actions': ['голосовать', 'создавать законы', 'создавать партии', 'быть лидером партии'],
                    'modifiers': ['если', 'и', 'или', 'не']
                },
                'operators': {
                    'comparison': ['>', '<', '>=', '<=', '==', '!='],
                    'logical': ['и', 'или', 'не']
                },
                'delimiters': [';', ',', '.'],
                'negation_words': ['не'],
                'conditional_words': ['если'],
                'action_mappings': {
                    'голосовать': 'vote',
                    'создавать законы': 'create_law',
                    'создавать партии': 'create_party',
                    'быть лидером партии': 'be_party_leader',
                    'имеет право': 'has_permission'
                }
            })
        else:  # English
            return cls({
                'language': 'english',
                'keywords': {
                    'subjects': ['User', 'Admin', 'Guest', 'Member'],
                    'conditions': ['has permission', 'member of', 'with rating'],
                    'actions': ['vote', 'create', 'delete', 'modify'],
                    'modifiers': ['if', 'and', 'or', 'not']
                },
                'operators': {
                    'comparison': ['>', '<', '>=', '<=', '==', '!='],
                    'logical': ['and', 'or', 'not']
                },
                'delimiters': [';', ',', '.'],
                'negation_words': ['not'],
                'conditional_words': ['if'],
                'action_mappings': {
                    'vote': 'vote',
                    'create': 'create',
                    'delete': 'delete',
                    'modify': 'modify'
                }
            })


class RegexTokenizer:
    """Regex-based tokenizer"""

    def tokenize(self, text: str, config: LanguageConfig) -> List[Token]:
        tokens = []
        position = 0
        line = 1
        column = 1

        # Create pattern for all delimiters
        delim_pattern = '|'.join(re.escape(d) for d in config.delimiters)

        # Split text while preserving delimiters
        parts = re.split(f'({delim_pattern})', text)

        for part in parts:
            part = part.strip()
            if not part:
                continue

            token = self._classify_token(part, config, position, line, column)
            if token:
                tokens.append(token)

            position += len(part)
            if '\n' in part:
                line += part.count('\n')
                column = len(part) - part.rfind('\n')
            else:
                column += len(part)

        return tokens

    def _classify_token(self, text: str, config: LanguageConfig,
                        position: int, line: int, column: int) -> Optional[Token]:
        """Classify a text fragment into a token"""

        # Check for placeholder patterns first (e.g., [ЧИСЛО]:123)
        placeholder_patterns = {
            "[ЧИСЛО]": r"\[ЧИСЛО\]:(\d+)",
            "[СТРОКА]": r"\[СТРОКА\]:(.+?)(?:;|$)",
            "[ПОЛЬЗОВАТЕЛЬ]": r"\[ПОЛЬЗОВАТЕЛЬ\]:(.+?)(?:;|$)",
            "[ПАРТИЯ]": r"\[ПАРТИЯ\]:(.+?)(?:;|$)",
            "[ДАТА]": r"\[ДАТА\]:(\d{4}-\d{2}-\d{2})"
        }

        for placeholder, pattern in placeholder_patterns.items():
            match = re.match(pattern, text)
            if match:
                return Token(TokenType.VALUE, match.group(1), original=placeholder,
                             position=position, line=line, column=column)

        # Check group markers
        if text in config.group_markers['start']:
            return Token(TokenType.GROUP_START, text, position=position, line=line, column=column)
        if text in config.group_markers['end']:
            return Token(TokenType.GROUP_END, text, position=position, line=line, column=column)

        # Check delimiters
        if text in config.delimiters:
            return Token(TokenType.DELIMITER, text, position=position, line=line, column=column)

        # Check operators
        for op_type, operators in config.operators.items():
            if text in operators:
                return Token(TokenType.OPERATOR, text,
                             metadata={'operator_type': op_type},
                             position=position, line=line, column=column)

        # Check keywords
        for keyword_type, keywords in config.keywords.items():
            if text in keywords:
                token_type = self._keyword_to_token_type(keyword_type)
                return Token(token_type, text,
                             metadata={'keyword_type': keyword_type},
                             position=position, line=line, column=column)

        # Check for standalone placeholders
        if text in ["[ЧИСЛО]", "[СТРОКА]", "[ПОЛЬЗОВАТЕЛЬ]", "[ПАРТИЯ]", "[ДАТА]"]:
            return Token(TokenType.PLACEHOLDER, text, position=position, line=line, column=column)

        # Default to value
        return Token(TokenType.VALUE, text, position=position, line=line, column=column)

    def _keyword_to_token_type(self, keyword_type: str) -> TokenType:
        """Map keyword types to token types"""
        mapping = {
            'subjects': TokenType.SUBJECT,
            'conditions': TokenType.CONDITION,
            'actions': TokenType.ACTION,
            'modifiers': TokenType.MODIFIER
        }
        return mapping.get(keyword_type, TokenType.VALUE)


class StructuralParser:
    """Structure-based parser that analyzes token relationships"""

    def parse(self, tokens: List[Token], config: LanguageConfig) -> Dict[str, Any]:
        structure = {
            'subjects': [],
            'conditions': [],
            'actions': [],
            'operators': [],
            'values': {},
            'groups': [],
            'negation': False,
            'conditional_blocks': [],
            'metadata': {}
        }

        i = 0
        while i < len(tokens):
            token = tokens[i]

            if token.type == TokenType.SUBJECT:
                structure['subjects'].append({
                    'type': token.value,
                    'metadata': token.metadata
                })

            elif token.type == TokenType.CONDITION:
                condition = {
                    'type': token.value,
                    'parameters': [],
                    'metadata': token.metadata
                }
                i = self._extract_parameters(tokens, i + 1, condition, config)
                structure['conditions'].append(condition)
                continue

            elif token.type == TokenType.ACTION:
                action = {
                    'type': token.value,
                    'parameters': [],
                    'metadata': token.metadata
                }
                i = self._extract_parameters(tokens, i + 1, action, config)
                structure['actions'].append(action)
                continue

            elif token.type == TokenType.OPERATOR:
                structure['operators'].append({
                    'type': token.value,
                    'operator_type': token.metadata.get('operator_type'),
                    'position': i
                })

                if token.value in config.negation_words:
                    structure['negation'] = True

            elif token.type == TokenType.GROUP_START:
                group_content, end_index = self._extract_group_content(tokens, i, config)
                if group_content:
                    group_structure = self.parse(group_content, config)
                    structure['groups'].append(group_structure)
                i = end_index
                continue

            elif token.type == TokenType.VALUE and token.original:
                structure['values'][token.original] = token.value

            i += 1

        return structure

    def _extract_parameters(self, tokens: List[Token], start_index: int,
                            item: Dict[str, Any], config: LanguageConfig) -> int:
        """Extract parameters for a condition or action"""
        i = start_index
        while i < len(tokens) and tokens[i].type in [TokenType.VALUE, TokenType.OPERATOR]:
            if tokens[i].type == TokenType.VALUE:
                item['parameters'].append({
                    'type': 'value',
                    'value': tokens[i].value
                })
            elif tokens[i].type == TokenType.OPERATOR:
                item['parameters'].append({
                    'type': 'operator',
                    'value': tokens[i].value,
                    'operator_type': tokens[i].metadata.get('operator_type')
                })
            i += 1

            if (i < len(tokens) and
                    (tokens[i].type == TokenType.DELIMITER or
                     tokens[i].type in [TokenType.SUBJECT, TokenType.CONDITION, TokenType.ACTION])):
                break

        return i - 1

    def _extract_group_content(self, tokens: List[Token], start_index: int,
                               config: LanguageConfig) -> tuple[List[Token], int]:
        """Extract content within group markers"""
        content = []
        depth = 1
        i = start_index + 1

        while i < len(tokens) and depth > 0:
            token = tokens[i]
            if token.type == TokenType.GROUP_START:
                depth += 1
            elif token.type == TokenType.GROUP_END:
                depth -= 1

            if depth > 0:
                content.append(token)
            i += 1

        return content, i - 1


class UniversalLawParser:
    """Universal, adaptive law parser - compatible with Flask"""

    def __init__(self, config: Optional[LanguageConfig] = None):
        self.config = config or LanguageConfig.create_default('russian')  # Default to Russian
        self.tokenizer = RegexTokenizer()
        self.parser = StructuralParser()

    def parse(self, law_text: str) -> ParsedLaw:
        """Parse a law text into structured format"""
        errors = []
        warnings = []

        try:
            tokens = self.tokenizer.tokenize(law_text, self.config)

            if not tokens:
                return ParsedLaw(
                    raw_text=law_text,
                    tokens=[],
                    structure={},
                    is_valid=False,
                    errors=["Empty or invalid law text"]
                )

            structure = self.parser.parse(tokens, self.config)
            self._validate_structure(structure, errors, warnings)

            return ParsedLaw(
                raw_text=law_text,
                tokens=tokens,
                structure=structure,
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                metadata={'config_language': self.config.language}
            )

        except Exception as e:
            return ParsedLaw(
                raw_text=law_text,
                tokens=[],
                structure={},
                is_valid=False,
                errors=[f"Parsing error: {str(e)}"]
            )

    def _validate_structure(self, structure: Dict[str, Any], errors: List[str], warnings: List[str]):
        """Validate the parsed structure"""
        if not structure.get('subjects'):
            errors.append("No subjects found in law")

        if not structure.get('actions') and not structure.get('conditions'):
            errors.append("No actions or conditions found in law")


class LawLanguageParser(UniversalLawParser):
    """Compatibility wrapper for old LawLanguageParser"""

    def __init__(self):
        super().__init__(LanguageConfig.create_default('russian'))

    def tokenize(self, law_text: str) -> List[Token]:
        """Compatibility method"""
        return self.tokenizer.tokenize(law_text, self.config)

    def to_readable_text(self, parsed_law: ParsedLaw) -> str:
        """Compatibility method"""
        if not parsed_law.is_valid:
            return f"Ошибка парсинга: {'; '.join(parsed_law.errors)}"

        structure = parsed_law.structure
        text_parts = []

        if structure.get('subjects'):
            subjects = [s['type'] for s in structure['subjects']]
            text_parts.append(f"Субъект: {', '.join(subjects)}")

        if structure.get('conditions'):
            conditions_text = [c['type'] for c in structure['conditions']]
            text_parts.append(f"Условия: {'; '.join(conditions_text)}")

        if structure.get('actions'):
            actions_text = [a['type'] for a in structure['actions']]
            text_parts.append(f"Действия: {'; '.join(actions_text)}")

        return "\n".join(text_parts)


class LawEnforcer:
    """Universal law enforcer - maintains compatibility with Flask app"""

    def __init__(self, config: Optional[LanguageConfig] = None):
        self.rules: Dict[str, List[ActionRule]] = {}
        self.parser = None  # Lazy initialization
        self.config = config or LanguageConfig.create_default('russian')

    def _get_parser(self):
        """Get parser with lazy initialization"""
        if self.parser is None:
            self.parser = UniversalLawParser(self.config)
        return self.parser

    def load_laws_from_db(self, db_session):
        """Load laws from database - maintains Flask compatibility"""
        try:
            # Import here to avoid circular imports
            from .models import Law

            laws = db_session.query(Law).all()
            for law in laws:
                try:
                    self.add_law(law.text, law.name)
                except Exception as e:
                    print(f"Ошибка обработки закона '{law.name}': {e}")
        except Exception as e:
            print(f"Ошибка загрузки из БД: {e}")

    def add_law(self, law_text: str, law_name: str = ""):
        """Add law to the system"""
        parsed = self._get_parser().parse(law_text)
        if not parsed.is_valid:
            raise ValueError(f"Некорректный закон '{law_name}': {parsed.errors}")

        rules = self._convert_to_rules(parsed, law_name)
        for rule in rules:
            if rule.action_name not in self.rules:
                self.rules[rule.action_name] = []
            self.rules[rule.action_name].append(rule)
            self.rules[rule.action_name].sort(key=lambda r: r.priority, reverse=True)

    def _convert_to_rules(self, parsed_law: ParsedLaw, law_name: str) -> List[ActionRule]:
        """Convert parsed law to executable rules"""
        structure = parsed_law.structure
        rules = []

        has_negation = structure.get("negation", False)

        # Get subject
        subject = ""
        if structure.get('subjects'):
            subject = structure['subjects'][0]['type']

        for action in structure.get("actions", []):
            rule = ActionRule(
                action_name=self._normalize_action_name(action["type"]),
                subject_type=subject,
                conditions=self._extract_conditions(structure),
                allow=not has_negation,
                priority=1 if has_negation else 0,
                metadata={'source_law': law_name}
            )
            rules.append(rule)

        return rules

    def _normalize_action_name(self, action: str) -> str:
        """Normalize action name using config mappings"""
        return self.config.action_mappings.get(action, action.lower().replace(" ", "_"))

    def _extract_conditions(self, structure: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract conditions from structure"""
        conditions = []

        for condition in structure.get("conditions", []):
            cond_type = condition["type"]
            params = condition.get("parameters", [])

            if cond_type == "член партии":
                conditions.append({"type": "has_party", "value": True})
            elif "рейтингом >" in cond_type and params:
                for param in params:
                    if param.get('type') == 'value':
                        try:
                            conditions.append({"type": "rating_gt", "value": int(param["value"])})
                        except (ValueError, KeyError):
                            pass
            elif "рейтингом <" in cond_type and params:
                for param in params:
                    if param.get('type') == 'value':
                        try:
                            conditions.append({"type": "rating_lt", "value": int(param["value"])})
                        except (ValueError, KeyError):
                            pass
            elif cond_type == "имеет право":
                conditions.append({"type": "has_base_permission", "value": True})

        # Add values from placeholders
        for placeholder, value in structure.get("values", {}).items():
            if placeholder == "[ПОЛЬЗОВАТЕЛЬ]":
                conditions.append({"type": "username_equals", "value": value})
            elif placeholder == "[ПАРТИЯ]":
                conditions.append({"type": "party_name_equals", "value": value})
            elif placeholder == "[ЧИСЛО]":
                try:
                    conditions.append({"type": "number_value", "value": int(value)})
                except ValueError:
                    pass

        return conditions

    def check_permission(self, user, action_name: str, context: Dict[str, Any] = None) -> bool:
        """Check permission for action"""
        if context is None:
            context = {}

        rules = self.rules.get(action_name, [])
        if not rules:
            return False

        for rule in rules:
            if self._check_rule(user, rule, context):
                return rule.allow

        return False

    def _check_rule(self, user, rule: ActionRule, context: Dict[str, Any]) -> bool:
        """Check if user matches rule"""
        # Subject check
        if rule.subject_type == "Пользователь":
            if not user:
                return False
        elif rule.subject_type == "Правитель":
            if not user or not getattr(user, 'admin', False):
                return False

        # Condition checks
        for condition in rule.conditions:
            if not self._check_condition(user, condition, context):
                return False

        return True

    def _check_condition(self, user, condition: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Check individual condition"""
        cond_type = condition["type"]
        value = condition["value"]

        if cond_type == "has_party":
            return bool(getattr(user, 'party_id', None)) == value
        elif cond_type == "rating_gt":
            return getattr(user, 'rating', 0) > value
        elif cond_type == "rating_lt":
            return getattr(user, 'rating', 0) < value
        elif cond_type == "username_equals":
            return getattr(user, 'username', '') == value
        elif cond_type == "party_name_equals":
            party = getattr(user, 'party', None)
            return party and getattr(party, 'name', '') == value
        elif cond_type == "has_base_permission":
            return True

        return True

    def get_permissions_for_user(self, user) -> Dict[str, bool]:
        """Get all permissions for user"""
        permissions = {}
        for action_name in self.rules.keys():
            permissions[action_name] = self.check_permission(user, action_name)
        return permissions


# Global law enforcer - maintains compatibility
law_enforcer = None


def get_law_enforcer():
    """Get global law enforcer instance"""
    global law_enforcer
    if law_enforcer is None:
        law_enforcer = LawEnforcer()
    return law_enforcer


def requires_permission(action_name: str):
    """Flask decorator for permission checking - maintains compatibility"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            from flask_login import current_user
            from flask import abort

            if not get_law_enforcer().check_permission(current_user, action_name):
                abort(403)

            return func(*args, **kwargs)

        return wrapper

    return decorator


def check_law_compliance(action_name: str, user=None, context: Dict[str, Any] = None) -> bool:
    """Check law compliance - maintains compatibility"""
    if user is None:
        from flask_login import current_user
        user = current_user

    return get_law_enforcer().check_permission(user, action_name, context)


def init_law_system(app, db):
    """Initialize law system - maintains Flask compatibility"""
    with app.app_context():
        try:
            enforcer = get_law_enforcer()
            enforcer.load_laws_from_db(db.session)
            print(f"✓ Система законов инициализирована. Загружено правил: {len(enforcer.rules)}")
        except Exception as e:
            print(f"⚠ Ошибка инициализации системы законов: {e}")
            print("Система будет работать без законов из БД")