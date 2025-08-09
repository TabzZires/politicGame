from flask import Blueprint, render_template
from ..models import Poll, Law

bp = Blueprint('main', __name__)


@bp.route('/')
def index():
    polls = Poll.query.order_by(Poll.id.desc()).limit(5).all()
    laws = Law.query.all()
    return render_template('index.html', polls=polls, laws=laws)
