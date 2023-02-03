# app初始化函数，工厂函数
from flask import Flask, render_template
from flask_bootstrap import Bootstrap
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from config import config
from flask_mail import Mail
from flask_login import LoginManager

'''
实例化
'''
bootstrap = Bootstrap()
moment = Moment()
db = SQLAlchemy()
mail = Mail()

login_manager = LoginManager()
login_manager.login_view = 'auth.login'


def create_app(config_name):   # app的构造函数，也叫做工厂函数
    app = Flask(__name__)
    app.config.from_object(config[config_name])  # config.py中的config字典
    config[config_name].init_app(app)  # config.py中的config字典中的某个类中的init_app()

    bootstrap.init_app(app)
    moment.init_app(app)
    mail.init_app(app)
    db.init_app(app)

    login_manager.init_app(app)

    # 注册蓝本，添加路由和自定义的错误页面
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    return app

