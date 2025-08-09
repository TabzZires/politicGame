from flask import Blueprint, url_for, render_template
from flask_login import login_required, current_user
from werkzeug.utils import redirect

from app.forms import NewsForm
from app.models import News, db

bp = Blueprint('news', __name__, url_prefix='/news')


@bp.route('/create', methods=['POST', 'GET'])
@login_required
def create_news():
    form = NewsForm()
    if form.validate_on_submit():
        news = News(name=form.name.data, desc=form.desc.data, text=form.text.data, author_id=current_user.id, party_id=current_user.party_id)
        db.session.add(news)
        db.session.commit()
        return redirect(url_for('main.index'))

    return render_template('create_news.html', form=form)


@bp.route('/profile/<int:news_id>')
def profile(news_id):
    news = News.query.get_or_404(news_id)
    return render_template('news_profile.html', news=news)