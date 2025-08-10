from flask import Blueprint, render_template, flash, redirect, url_for, request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import or_, and_
import json
from datetime import datetime

from ..forms import LawForm, LawTemplateForm, LawValidationForm, LawVoteForm, LawSearchForm, QuickLawForm
from ..models import Law, LawTemplate, LawExecution, LawVote, db, User, Party
from ..law_system import LawValidator, execute_laws_for_action

bp = Blueprint('laws', __name__, url_prefix='/laws')


@bp.route('/')
def index():
    """Главная страница законов с поиском и фильтрацией"""
    search_form = LawSearchForm()

    # Базовый запрос
    query = Law.query

    # Применение фильтров
    if request.args.get('query'):
        search_term = f"%{request.args.get('query')}%"
        query = query.filter(or_(
            Law.name.ilike(search_term),
            Law.description.ilike(search_term)
        ))

    if request.args.get('status'):
        status = request.args.get('status')
        if status == 'active':
            query = query.filter(Law.active == True)
        elif status == 'pending':
            query = query.filter(Law.validation_status == 'pending')
        elif status == 'rejected':
            query = query.filter(Law.validation_status == 'rejected')

    if request.args.get('author'):
        author_name = f"%{request.args.get('author')}%"
        query = query.join(User).filter(User.username.ilike(author_name))

    # Сортировка
    sort_by = request.args.get('sort', 'created_at')
    if sort_by == 'name':
        query = query.order_by(Law.name)
    elif sort_by == 'executions':
        query = query.order_by(Law.execution_count.desc())
    else:
        query = query.order_by(Law.created_at.desc())

    # Пагинация
    page = request.args.get('page', 1, type=int)
    laws = query.paginate(page=page, per_page=20, error_out=False)

    return render_template('laws/index.html', laws=laws, search_form=search_form)


@bp.route('/<int:law_id>')
def law_profile(law_id):
    """Страница конкретного закона"""
    law = Law.query.get_or_404(law_id)

    # Получение статистики выполнения
    recent_executions = LawExecution.query.filter_by(law_id=law_id).order_by(LawExecution.started_at.desc()).limit(
        10).all()

    # Получение голосов
    votes = LawVote.query.filter_by(law_id=law_id).all()
    vote_summary = {
        'for': sum(1 for v in votes if v.vote == 'for'),
        'against': sum(1 for v in votes if v.vote == 'against'),
        'abstain': sum(1 for v in votes if v.vote == 'abstain'),
        'total': len(votes)
    }

    # Проверка, голосовал ли текущий пользователь
    user_vote = None
    if current_user.is_authenticated:
        user_vote = LawVote.query.filter_by(law_id=law_id, user_id=current_user.id).first()

    return render_template('laws/profile.html',
                           law=law,
                           recent_executions=recent_executions,
                           vote_summary=vote_summary,
                           user_vote=user_vote)


@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_law():
    """Создание нового закона"""
    form = LawForm()

    if form.validate_on_submit():
        # Валидация кода
        is_valid, error_msg = LawValidator.validate_code(form.code.data)

        # Создание закона
        law = Law(
            name=form.name.data,
            description=form.description.data,
            text=form.code.data,
            user_id=current_user.id,
            party_id=current_user.party_id if current_user.party_id else None,
            validation_status='approved' if is_valid else 'rejected',
            validation_error=None if is_valid else error_msg,
            active=form.auto_activate.data and is_valid
        )

        # Настройка триггеров
        triggers = []
        if form.trigger_actions.data:
            actions = [action.strip() for action in form.trigger_actions.data.split(',')]
            triggers.append({
                'type': 'action',
                'actions': actions
            })

        if form.trigger_schedule.data:
            triggers.append({
                'type': 'time',
                'schedule': form.trigger_schedule.data
            })

        law.triggers = triggers

        db.session.add(law)
        db.session.commit()

        if is_valid:
            flash('Закон успешно создан и прошел валидацию!', 'success')
            if form.auto_activate.data:
                # Регистрация закона в системе
                if hasattr(current_app, 'law_manager'):
                    current_app.law_manager.register_law(law.id, {
                        'code': law.text,
                        'triggers': law.triggers,
                        'active': True,
                        'metadata': {
                            'name': law.name,
                            'author_id': law.user_id,
                            'party_id': law.party_id
                        }
                    })
                flash('Закон активирован!', 'info')
        else:
            flash(f'Закон создан, но не прошел валидацию: {error_msg}', 'warning')

        return redirect(url_for('laws.law_profile', law_id=law.id))

    return render_template('laws/create.html', form=form)


@bp.route('/templates')
def templates():
    """Список шаблонов законов"""
    templates = LawTemplate.query.order_by(LawTemplate.usage_count.desc()).all()
    return render_template('laws/templates.html', templates=templates)


@bp.route('/templates/<int:template_id>')
def template_detail(template_id):
    """Детали шаблона"""
    template = LawTemplate.query.get_or_404(template_id)
    return render_template('laws/template_detail.html', template=template)


@bp.route('/templates/create', methods=['GET', 'POST'])
@login_required
def create_template():
    """Создание шаблона закона"""
    if not current_user.admin:
        flash('Только администраторы могут создавать шаблоны', 'error')
        return redirect(url_for('laws.templates'))

    form = LawTemplateForm()

    if form.validate_on_submit():
        try:
            parameters = json.loads(form.parameters.data) if form.parameters.data else []
        except json.JSONDecodeError:
            flash('Ошибка в формате параметров JSON', 'error')
            return render_template('laws/create_template.html', form=form)

        template = LawTemplate(
            name=form.name.data,
            description=form.description.data,
            category=form.category.data,
            code_template=form.code_template.data,
            parameters=parameters,
            created_by=current_user.id
        )

        db.session.add(template)
        db.session.commit()

        flash('Шаблон успешно создан!', 'success')
        return redirect(url_for('laws.template_detail', template_id=template.id))

    return render_template('laws/create_template.html', form=form)


@bp.route('/create_from_template/<int:template_id>', methods=['GET', 'POST'])
@login_required
def create_from_template(template_id):
    """Создание закона из шаблона"""
    template = LawTemplate.query.get_or_404(template_id)

    if request.method == 'POST':
        name = request.form.get('name')
        if not name:
            flash('Название закона обязательно', 'error')
            return render_template('laws/create_from_template.html', template=template)

        # Получение значений параметров
        param_values = {}
        for param in template.parameters:
            value = request.form.get(f"param_{param['name']}")
            if value:
                # Приведение типов
                if param['type'] == 'number':
                    try:
                        value = int(value)
                    except ValueError:
                        value = param.get('default', 0)
                param_values[param['name']] = value
            else:
                param_values[param['name']] = param.get('default', '')

        # Подстановка параметров в код
        code = template.code_template
        for param_name, param_value in param_values.items():
            code = code.replace(f"{{{param_name}}}", str(param_value))

        # Валидация кода
        is_valid, error_msg = LawValidator.validate_code(code)

        # Создание закона
        law = Law(
            name=name,
            description=f"Создан из шаблона: {template.name}",
            text=code,
            user_id=current_user.id,
            party_id=current_user.party_id if current_user.party_id else None,
            validation_status='approved' if is_valid else 'rejected',
            validation_error=None if is_valid else error_msg
        )

        db.session.add(law)

        # Увеличение счетчика использования шаблона
        template.usage_count += 1
        db.session.commit()

        if is_valid:
            flash('Закон успешно создан из шаблона!', 'success')
        else:
            flash(f'Закон создан, но не прошел валидацию: {error_msg}', 'warning')

        return redirect(url_for('laws.law_profile', law_id=law.id))

    return render_template('laws/create_from_template.html', template=template)


@bp.route('/<int:law_id>/vote', methods=['GET', 'POST'])
@login_required
def vote_law(law_id):
    """Голосование за закон"""
    law = Law.query.get_or_404(law_id)

    # Проверка, не голосовал ли уже пользователь
    existing_vote = LawVote.query.filter_by(law_id=law_id, user_id=current_user.id).first()
    if existing_vote:
        flash('Вы уже голосовали за этот закон', 'warning')
        return redirect(url_for('laws.law_profile', law_id=law_id))

    form = LawVoteForm()

    if form.validate_on_submit():
        vote = LawVote(
            law_id=law_id,
            user_id=current_user.id,
            vote=form.vote.data
        )

        db.session.add(vote)
        db.session.commit()

        flash(f'Ваш голос "{form.vote.data}" учтен!', 'success')

        # Проверка, нужно ли активировать закон
        votes = LawVote.query.filter_by(law_id=law_id).all()
        total_votes = len(votes)
        for_votes = sum(1 for v in votes if v.vote == 'for')

        # Простое правило: если больше половины за, то активируем
        if total_votes >= 3 and for_votes > total_votes / 2 and not law.active:
            law.active = True
            law.activated_at = datetime.utcnow()
            db.session.commit()

            # Регистрация в системе законов
            if hasattr(current_app, 'law_manager'):
                current_app.law_manager.register_law(law.id, {
                    'code': law.text,
                    'triggers': law.triggers,
                    'active': True,
                    'metadata': {
                        'name': law.name,
                        'author_id': law.user_id,
                        'party_id': law.party_id
                    }
                })

            flash('Закон набрал достаточно голосов и активирован!', 'success')

        return redirect(url_for('laws.law_profile', law_id=law_id))

    return render_template('laws/vote.html', law=law, form=form)


@bp.route('/<int:law_id>/toggle_active', methods=['POST'])
@login_required
def toggle_active(law_id):
    """Активация/деактивация закона (только для админов)"""
    if not current_user.admin:
        flash('Только администраторы могут управлять активностью законов', 'error')
        return redirect(url_for('laws.law_profile', law_id=law_id))

    law = Law.query.get_or_404(law_id)

    if law.validation_status != 'approved':
        flash('Можно активировать только одобренные законы', 'error')
        return redirect(url_for('laws.law_profile', law_id=law_id))

    law.active = not law.active
    if law.active:
        law.activated_at = datetime.utcnow()

    db.session.commit()

    # Обновление в системе законов
    if hasattr(current_app, 'law_manager'):
        if law.active:
            current_app.law_manager.register_law(law.id, {
                'code': law.text,
                'triggers': law.triggers,
                'active': True,
                'metadata': {
                    'name': law.name,
                    'author_id': law.user_id,
                    'party_id': law.party_id
                }
            })
        else:
            current_app.law_manager.active_laws.pop(law.id, None)

    status = 'активирован' if law.active else 'деактивирован'
    flash(f'Закон {status}!', 'success')

    return redirect(url_for('laws.law_profile', law_id=law_id))


@bp.route('/validate/<int:law_id>', methods=['GET', 'POST'])
@login_required
def validate_law(law_id):
    """Валидация закона администратором"""
    if not current_user.admin:
        flash('Только администраторы могут валидировать законы', 'error')
        return redirect(url_for('laws.law_profile', law_id=law_id))

    law = Law.query.get_or_404(law_id)
    form = LawValidationForm()

    if form.validate_on_submit():
        law.validation_status = form.validation_status.data
        law.validation_error = form.validation_comment.data
        law.validated_by = current_user.id
        law.validated_at = datetime.utcnow()

        db.session.commit()

        flash('Решение по валидации сохранено!', 'success')
        return redirect(url_for('laws.law_profile', law_id=law_id))

    return render_template('laws/validate.html', law=law, form=form)


@bp.route('/<int:law_id>/executions')
def law_executions(law_id):
    """История выполнения закона"""
    law = Law.query.get_or_404(law_id)
    page = request.args.get('page', 1, type=int)

    executions = LawExecution.query.filter_by(law_id=law_id).order_by(
        LawExecution.started_at.desc()
    ).paginate(page=page, per_page=50, error_out=False)

    return render_template('laws/executions.html', law=law, executions=executions)


@bp.route('/api/test_law', methods=['POST'])
@login_required
def test_law():
    """API для тестирования кода закона"""
    code = request.json.get('code', '')

    # Валидация
    is_valid, error_msg = LawValidator.validate_code(code)

    if not is_valid:
        return jsonify({
            'success': False,
            'error': error_msg,
            'result': None
        })

    # Тестовое выполнение
    try:
        from ..law_system import LawExecutor, LawContext
        context = LawContext(
            user_id=current_user.id,
            action='test',
            timestamp=datetime.now(),
            data={'test': True},
            session=None
        )

        executor = LawExecutor(db.session)
        result = executor.execute_law(code, context)

        return jsonify(result)

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Ошибка тестирования: {str(e)}',
            'result': None
        })


# API endpoints для поиска (оставляем для совместимости)
@bp.route("/api/search_users")
def search_users():
    q = request.args.get("q", "")
    users = User.query.filter(User.username.ilike(f"%{q}%")).limit(10).all()
    return jsonify([{"id": u.id, "name": u.username} for u in users])


@bp.route("/api/search_parties")
def search_parties():
    q = request.args.get("q", "")
    parties = Party.query.filter(Party.name.ilike(f"%{q}%")).limit(10).all()
    return jsonify([{"id": p.id, "name": p.name} for p in parties])