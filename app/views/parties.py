from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

from ..forms import CreatePartyForm
from ..models import db, Party

bp = Blueprint('parties', __name__, url_prefix='/parties')


@bp.route('/<int:party_id>')
def party_profile(party_id):
    party = Party.query.get_or_404(party_id)
    return render_template('party_profile.html', party=party)


@bp.route('/')
def list_parties():
    parties = Party.query.all()
    return render_template('list_parties.html', parties=parties)


@bp.route('/create', methods=['GET', 'POST'])
def create_party():
    form = CreatePartyForm()
    if form.validate_on_submit():
        party = Party(name=form.name.data)
        db.session.add(party)
        db.session.commit()
        return redirect(url_for('parties.list_parties'))
    return render_template('create_party.html', form=form)


@bp.route('/<int:party_id>/join')
@login_required
def join_party(party_id):
    party = Party.query.get_or_404(party_id)
    current_user.party = party
    party.count += 1
    db.session.commit()
    return redirect(url_for('parties.party_profile', party_id=party.id))


@bp.route('/<int:party_id>/leave')
@login_required
def leave_party(party_id):
    current_user.party = None
    Party.query.get_or_404(party_id).count -= 1
    db.session.commit()
    return redirect(url_for('parties.party_profile', party_id=party_id))


@bp.route('/<int:party_id>/become_leader')
@login_required
def become_leader(party_id):
    party = Party.query.get_or_404(party_id)
    party.leader_id = current_user.id
    db.session.commit()
    return redirect(url_for('parties.party_profile', party_id=party.id))