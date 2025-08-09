from flask import Blueprint, render_template
from sqlalchemy import func

from ..models import Poll, Law, News, Party

bp = Blueprint('main', __name__)


@bp.route('/')
def index():
    polls = Poll.query.order_by(Poll.id.desc()).limit(5).all()
    laws = Law.query.all()
    news = News.query.all()
    parties = Party.query.order_by(Party.count.desc()).limit(10).all()
    return render_template('index.html', polls=polls, laws=laws, news=news, parties=parties)
