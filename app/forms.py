from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, BooleanField, SelectField
from wtforms.fields.choices import RadioField
from wtforms.fields.datetime import DateField
from wtforms.validators import DataRequired, Length, Optional
from wtforms import PasswordField


class CreatePartyForm(FlaskForm):
    name = StringField('Название партии', validators=[DataRequired()])
    submit = SubmitField('Создать')


class CreatePollForm(FlaskForm):
    question = StringField('Вопрос', validators=[DataRequired()])
    type = SelectField('Тип', choices=[('vote', 'Голосование'), ('suggest', 'Предложения')])
    party = SelectField('Партия', coerce=int)  # выбор из списка
    options = TextAreaField('Варианты (через новую строку)')
    end_date = DateField('Конечная дата', validators=[DataRequired()])
    submit = SubmitField('Создать')


class VoteForm(FlaskForm):
    options = RadioField('Ваш выбор')
    submit = SubmitField('Голосовать')


class RegisterForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired(), Length(min=3)])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=4)])
    submit = SubmitField('Зарегистрироваться')


class LoginForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')


class AddOptionForm(FlaskForm):
    text = StringField('Ваш вариант', validators=[DataRequired()])
    submit = SubmitField('Добавить вариант')


class SuggestionForm(FlaskForm):
    text = StringField('Ваше предложение', validators=[DataRequired()])
    submit = SubmitField('Отправить')


class LawForm(FlaskForm):
    name = StringField('Название закона', validators=[DataRequired(), Length(min=3, max=200)])
    description = TextAreaField('Описание (что делает этот закон)',
                                validators=[DataRequired(), Length(min=10, max=1000)])
    code = TextAreaField('Python код закона', validators=[DataRequired()],
                         render_kw={'rows': 20, 'placeholder': '''# Пример простого закона
def apply():
    """
    Основная функция закона - обязательна!
    Возвращает словарь с результатом выполнения
    """
    user = api.get_user()

    if context.action == 'vote':
        if not user or not user['party_id']:
            api.log_action("Отклонено голосование", f"Пользователь не в партии")
            return {
                'action': 'deny',
                'reason': 'Только члены партий могут голосовать'
            }

    return {'action': 'allow'}
'''})

    # Настройки триггеров
    trigger_actions = StringField('Действия-триггеры (через запятую)',
                                  validators=[Optional()],
                                  render_kw={'placeholder': 'vote, create_party, join_party'})

    trigger_schedule = SelectField('Расписание',
                                   choices=[('', 'Нет'), ('daily', 'Ежедневно'), ('weekly', 'Еженедельно'),
                                            ('monthly', 'Ежемесячно')],
                                   default='')

    auto_activate = BooleanField('Автоматически активировать после создания')

    submit = SubmitField('Создать закон')


class LawTemplateForm(FlaskForm):
    name = StringField('Название шаблона', validators=[DataRequired(), Length(min=3, max=200)])
    description = TextAreaField('Описание шаблона', validators=[DataRequired(), Length(min=10, max=1000)])
    category = SelectField('Категория', choices=[
        ('governance', 'Управление'),
        ('voting', 'Голосование'),
        ('parties', 'Партии'),
        ('economy', 'Экономика'),
        ('social', 'Социальная сфера'),
        ('other', 'Другое')
    ])
    code_template = TextAreaField('Шаблон кода', validators=[DataRequired()], render_kw={'rows': 15})
    parameters = TextAreaField('Параметры (JSON)', validators=[Optional()])
    submit = SubmitField('Создать шаблон')


class LawValidationForm(FlaskForm):
    validation_status = SelectField('Статус валидации', choices=[
        ('approved', 'Одобрен'),
        ('rejected', 'Отклонен'),
        ('needs_revision', 'Требует доработки')
    ])
    validation_comment = TextAreaField('Комментарий', validators=[Optional()], render_kw={'rows': 4})
    submit = SubmitField('Сохранить решение')


class LawVoteForm(FlaskForm):
    vote = SelectField('Ваш голос', choices=[
        ('for', 'За'),
        ('against', 'Против'),
        ('abstain', 'Воздержаться')
    ], validators=[DataRequired()])
    comment = TextAreaField('Комментарий', validators=[Optional()], render_kw={'rows': 3})
    submit = SubmitField('Проголосовать')


class LawSearchForm(FlaskForm):
    query = StringField('Поиск', validators=[Optional()])
    status = SelectField('Статус', choices=[
        ('', 'Все'),
        ('active', 'Активные'),
        ('pending', 'На рассмотрении'),
        ('rejected', 'Отклоненные')
    ], default='')
    author = StringField('Автор', validators=[Optional()])
    sort = SelectField('Сортировка', choices=[
        ('created_at', 'По дате создания'),
        ('name', 'По названию'),
        ('executions', 'По выполнениям')
    ], default='created_at')
    submit = SubmitField('Найти')


class QuickLawForm(FlaskForm):
    name = StringField('Название', validators=[DataRequired(), Length(min=3, max=200)])
    law_type = SelectField('Тип закона', choices=[
        ('permission', 'Разрешение/Запрет'),
        ('requirement', 'Требование'),
        ('notification', 'Уведомление')
    ])
    action_trigger = SelectField('Когда применять', choices=[
        ('vote', 'При голосовании'),
        ('create_party', 'При создании партии'),
        ('join_party', 'При вступлении в партию'),
        ('create_poll', 'При создании опроса')
    ])
    condition = TextAreaField('Условие', validators=[Optional()], render_kw={'rows': 2})
    result_message = StringField('Сообщение', validators=[Optional()])
    allow_or_deny = SelectField('Действие', choices=[
        ('allow', 'Разрешить'),
        ('deny', 'Запретить'),
        ('info', 'Информация')
    ])
    submit = SubmitField('Создать простой закон')