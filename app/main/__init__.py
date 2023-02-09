# app主蓝图
from flask import Blueprint

main = Blueprint('main', __name__)  # 两个参数，一个是蓝本的名称， 一个是蓝本所在的包或模块

from . import views, errors
from ..models import Permission

@main.app_context_processor
def inject_permissions():
    return dict(Permission=Permission)