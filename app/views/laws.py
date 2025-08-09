from flask import Blueprint, render_template, flash, redirect, url_for, request, jsonify
from flask_login import login_required, current_user

from ..forms import LawForm
from ..models import Law, db, User, Party

bp = Blueprint('laws', __name__, url_prefix='/laws')


@bp.route('/<int:law_id>')
def law_profile(law_id):
    law = Law.query.get_or_404(law_id)
    return render_template('law_profile.html', law=law)


@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_law():
    form = LawForm()
    if form.validate_on_submit():
        law = Law(
            name=form.name.data,
            text=form.text.data,
            user_id=current_user.id,
            party_id=current_user.party_id if current_user.party_id else None
        )
        db.session.add(law)
        db.session.commit()
        flash('Закон создан!', 'success')
        return redirect(url_for('laws.law_profile', law_id=law.id))
    # Здесь words — словарь твоего языка
    from ..law_words import LAW_WORDS
    return render_template('create_law.html', form=form, words=LAW_WORDS)


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

