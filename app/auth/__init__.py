# 用户身份认证系统蓝图
from flask import Blueprint

auth = Blueprint('auth', __name__)

from . import views