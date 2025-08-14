from flask import Blueprint, render_template, redirect, request, url_for, flash
from flask_login import login_required, current_user

from ..models import db, Poll, Vote, Suggestion, Option, Party, User
from ..forms import CreatePollForm, VoteForm, SuggestionForm, AddOptionForm

bp = Blueprint('polls', __name__, url_prefix='/polls')


@bp.route('/')
def list_polls():
    polls = Poll.query.all()
    return render_template('list_polls.html', polls=polls)


@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_poll():
    form = CreatePollForm()

    # Скрываем поле выбора партии
    del form.party

    if form.validate_on_submit():
        poll = Poll(
            question=form.question.data,
            type=form.type.data,
            author_id=current_user.id,
            party_id=current_user.party_id,
            end_date=form.end_date.data # автоматически от своей партии или None
        )
        db.session.add(poll)
        db.session.commit()

        if poll.type == 'vote':
            for line in form.options.data.strip().splitlines():
                if line.strip():
                    db.session.add(Option(text=line.strip(), poll=poll))
            db.session.commit()

        return redirect(url_for('polls.list_polls'))

    return render_template('create_poll.html', form=form)


@bp.route('/vote/<int:poll_id>', methods=['GET', 'POST'])
@login_required
def vote(poll_id):
    poll = Poll.query.get_or_404(poll_id)

    if poll.type == 'vote':
        form = VoteForm()
        form.options.choices = [(str(opt.id), opt.text) for opt in poll.options]

        if form.validate_on_submit():
            existing = Vote.query.filter_by(user_id=current_user.id, poll_id=poll.id).first()
            if existing:
                flash("Вы уже голосовали.")
            else:
                vote = Vote(
                    user_id=current_user.id,
                    poll_id=poll.id,
                    option_id=int(form.options.data)
                )
                db.session.add(vote)
                db.session.commit()
                flash("Голос учтён.")

        return render_template('vote.html', poll=poll, form=form)

    elif poll.type == 'suggest':
        suggestion_form = SuggestionForm()
        if suggestion_form.validate_on_submit():
            suggestion = Suggestion(text=suggestion_form.text.data, poll=poll, user_id=current_user.id)
            db.session.add(suggestion)
            db.session.commit()

        suggestions = poll.suggestions
        return render_template('suggest.html', poll=poll, suggestions=suggestions, form=suggestion_form)
