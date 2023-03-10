from functools import wraps
from flask import abort
from flask_login import current_user
from .models import Permission


def permission_required(permission):  # 返回decorator
    def decorator(f):
        @wraps(f)    # decorated_function = wraps(f)(decorated_function)
        def decorated_function(*args, **kwargs):
            if not current_user.can(permission):
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    return permission_required(Permission.ADMIN)(f)   # 等价 decorator(f)