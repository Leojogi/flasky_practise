# 用户身份认证系统路由,视图函数
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from . import auth
from .. import db
from ..models import User
from .forms import LoginForm, RegistrationForm, ChangePasswordForm, PasswordResetRequestForm, PasswordResetForm, ChangeEmailForm
from ..email import send_email


@auth.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()  # 创建LoginForm对象
    if form.validate_on_submit():  # Flask-WTK的validate_on_submit()函数会验证表单数据
        user = User.query.filter_by(email=form.email.data).first()  # 从数据库中加载用户
        if user is not None and user.verify_password(form.email.data): # 用户存在，调用verify_password()方法，参数是表单中的密码
            login_user(user, form.remember_me.data) # 调用Flask-Login的login_user()函数，在用户会话中把用户标记为已登录，参数为要登录的用户
            next = request.args.get('next')  # 用户访问未经授权的URL时会显示登录表单，Flask-Login会将原URL会保存至查询字符串的next参数中
            if next is None or not next.startswith('/'):  # 如果查询字符中没有next参数，则重定向至首页，next中的URL是相对路径
                next = url_for('main.index')
            return redirect(next)
        flash('Invalid username or password.')  # 如果输入的电子邮件地址或密码不正确，会设定一个闪现消息
    return render_template('auth/login.html', form=form)


@auth.route('/logout')
@login_required  # 保护路由，禁止未授权的用户登录
def logout():
    logout_user()  # 删除并重设用户会话
    flash('You have been logged out.')
    return redirect(url_for('main.index'))    # 重定向至主页面路由


@auth.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():  # Flask-WTK的validate_on_submit()函数会验证表单数据
        user = User(email=form.email.data, username=form.username.data, password=form.password.data)
        db.session.add(user)
        db.session.commit()
        token = user.generate_confirmation_token()
        send_email(to=user.email, subject='Confirm Your Account', template='auth/email/confirm', user=user, token=token)
        flash('A confirmation email has been sent to you by email.')
        return redirect(url_for('main.index'))   # 重定向至主页面路由
    return render_template('auth/register.html', form=form)


@auth.route('/confirm/<token>')
@login_required   # 保护这个路由
def confirm(token):
    if current_user.confirmed:    # 如果当前用户确认过了
        return redirect(url_for('main.index'))
    if current_user.confirm(token):   # 如果当前用户没确认过，执行确认操作，如果成功确认，则更新提交数据库
        db.session.commit()
        flash('You have confirmed your account.Thanks!')
    else:                             # 如果当前用户没确认过，执行确认操作，如果确认失败，提示用户
        flash('The confirmation link is invalid or has expired.')
    return redirect(url_for('main.index'))  # 重定向至主页面路由


@auth.before_app_request
def before_request():
    if current_user.is_authenticated and not current_user.confirmed and request.blueprint != 'auth' and request.endpoint != 'static':
        return redirect(url_for('auth.unconfirmed'))      # 重定向至未确认路由


# 未确认路由
@auth.route('/unconfirmed')
def unconfirmed():
    if current_user.is_anonymous or current_user.confirmed:
        return redirect(url_for('main.index'))   # 重定向至主页面路由
    return render_template('auth/unconfirmed.html')


# 确认路由
@auth.route('/confirm')
@login_required   # 保护这个路由
def resend_confirmation():
    token = current_user.generate_confirmation_token()
    send_email(to=current_user.email, subject='Confirm Your Account', template='auth/email/confirm', user=current_user, token=token)
    flash('A new confirmation email has been sent to you by email.')
    return redirect(url_for('main.index'))    # 重定向至主页面路由


@auth.route('/change-password', methods=['GET', 'POST'])
@login_required   # 保护这个路由
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.old_password.data):   # 验证老密码hash
            current_user.password = form.password.data             # 调用password()赋值表单提交的新密码
            db.session.add(current_user)
            db.session.commit()
            flash('You password has been updated.')
            return redirect(url_for('main.index'))   # 重定向至主页面路由
        else:
            flash('Invalid password.')
    return render_template('auth/change_password.html', form=form)


@auth.route('/reset', methods=['GET', 'POST'])
def password_reset_request():
    if not current_user.is_anonymous:            # 如果不是匿名用户
        return redirect(url_for('main.index'))   # 重定向至主页面路由
    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()    # 查询数据库中重置密码表单提交上来的邮箱地址
        if user:
            token = user.generate_reset_token()     # 生成token
            send_email(to=user.email, subject='Reset your password', template='auth/email/reset_password', user=user, token=token)   # 发送邮件
        flash('An email with instructions to reset your password has been sent to you.')
        return redirect(url_for('auth.login'))     # 重定向至登录路由
    return render_template('auth/reset_password.html', form=form)


@auth.route('/reset/<token>', methods=['GET', 'POST'])
def password_reset(token):
    if not current_user.is_anonymous:              # 如果不是匿名用户
        return redirect(url_for('main.index'))     # 重定向至主页面路由
    form = PasswordResetForm()
    if form.validate_on_submit():
        if User.reset_password(token=token, new_password=form.password.data):   # 调用reset_password()重置密码
            db.session.commit()
            flash('You password has been updated.')
            return redirect(url_for('auth.login'))    # 重定向至登录路由
        else:
            return redirect(url_for('main.index'))    # 重定向至主页面路由
    return render_template('auth/reset_password.html', form=form)


@auth.route('/change_email', methods=['GET', 'POST'])
@login_required   # 保护这个路由
def change_email_request():
    form = ChangeEmailForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.password.data):
            new_email = form.email.data.lower()
            token = current_user.generate_email_change_token(new_email)
            send_email(to=new_email, subject='Confirm your email address', template='auth/email/change_email', user=current_user, token=token)  # 发送邮件
            flash('An email with instructions to reset your new email address has been sent to you.')
            return redirect(url_for('main.index'))
        else:
            flash('Invalid email or password.')
    return render_template('auth/change_email.html', form=form)


@auth.route('/change_email/<token>')
@login_required
def change_email(token):
    if current_user.change_email(token):
        db.session.commit()
        flash('Your email address has been updated.')
    else:
        flash('Invalid request.')
    return redirect(url_for('main.index'))

