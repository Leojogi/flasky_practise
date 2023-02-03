# 首页的视图函数
from datetime import datetime
from flask import render_template, session, redirect, url_for, current_app
from . import main
from .. import db
from ..email import send_email
from .forms import NameForm
from ..models import User


@main.route('/', methods=['GET', 'POST'])
def index():
    form = NameForm()  # 实例化
    if form.validate_on_submit():  # 如果表单正常提交后，函数返回值为true
        user = User.query.filter_by(username=form.name.data).first()
        if user is None:   # 如果数据库中没有记录
            user = User(username=form.name.data)
            db.session.add(user)
            db.session.commit()
            session['known'] = False
            if current_app.config['FLASKY_ADMIN']:
                send_email(current_app.config['FLASKY_ADMIN'], 'New User', 'mail/new_user', user=user)
        else:
            session['known'] = True
        session['name'] = form.name.data  # 用户会话中保存所有请求的变量
        form.name.data = ''
        return redirect(url_for('main.index'))  # 返回重定向url
    return render_template('index.html', form=form, name=session.get('name'), known=session.get('known', False), current_time=datetime.utcnow())  # 请求返回的数据
