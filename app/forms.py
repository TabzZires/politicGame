from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms import TextAreaField
from wtforms.fields.choices import RadioField
from wtforms.validators import DataRequired
from wtforms import PasswordField, SelectField
from wtforms.validators import Length


class CreatePartyForm(FlaskForm):
    name = StringField('Название партии', validators=[DataRequired()])
    submit = SubmitField('Создать')


class CreatePollForm(FlaskForm):
    question = StringField('Вопрос', validators=[DataRequired()])
    type = SelectField('Тип', choices=[('vote', 'Голосование'), ('suggest', 'Предложения')])
    party = SelectField('Партия', coerce=int)  # выбор из списка
    options = TextAreaField('Варианты (через новую строку)')
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
    name = StringField('Название', validators=[DataRequired()])
    text = StringField('Описание', validators=[DataRequired()])
    submit = SubmitField('Создать')