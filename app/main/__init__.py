from flask import Blueprint

main = Blueprint('main', __name__)  # 两个参数，一个是蓝本的名称， 一个是蓝本所在的包或模块

from . import views, errors