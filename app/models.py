# 用户模型
from . import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, AnonymousUserMixin
from . import login_manager
from itsdangerous import TimedSerializer as Serializer
from authlib.jose import jwt, JoseError
from flask import current_app


# 获取已登录用户信息时调用
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class Permission:
    FOLLOW = 1
    COMMENT = 2
    WRITE = 4
    MODERATE = 8
    ADMIN = 16


class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False

    def is_administrator(self):
        return False


# 此属性告诉Flask-Login使用应用自定义的匿名用户类
login_manager.anonymous_user = AnonymousUser

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)
    users = db.relationship('User', backref='role', lazy='dynamic')  # users属性代表这个关系的面向对象视角，对于一个Role类的实例，
    # 其users属性将返回与角色相关联的用户组成的列表，第一个参数表明这个关系的另一端是哪个模型，backref参数向User模型中添加一个role属性，
    # 从而定义反向关系。通过User实例的这个属性可以获取对应的Role模型对象

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.permissions is None:
            self.permissions = 0

    def add_permission(self, perm):
        if not self.has_permission(perm):
            self.permissions += perm

    def remove_permission(self, perm):
        if self.has_permission(perm):
            self.permissions -= perm

    def reset_permission(self):
        self.permissions = 0

    def has_permission(self, perm):
        return self.permissions & perm == perm     # &位与运算，== 返回true或者false

    @staticmethod
    def insert_roles():
        roles = {
            'User': [Permission.FOLLOW, Permission.COMMENT, Permission.WRITE],
            'Moderator': [Permission.FOLLOW, Permission.COMMENT, Permission.WRITE, Permission.MODERATE],
            'Administrator': [Permission.FOLLOW, Permission.COMMENT, Permission.WRITE, Permission.MODERATE, Permission.ADMIN]
        }
        default_role = 'User'
        for r in roles:  # 取得角色名User,Moderator,Administrator
            role = Role.query.filter_by(name=r).first()  # 查询数据库中是否有角色r
            if role is None:
                role = Role(name=r)
            role.reset_permission()
            for perm in roles[r]:
                role.add_permission(perm)
            role.default = (role.name == default_role)   # 是否是默认角色User, True of False
            db.session.add(role)
        db.session.commit()


    def __repr__(self):
        return '<Role %r>' % self.name


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    # 密码散列值
    password_hash = db.Column(db.String(128))
    email = db.Column(db.String(64), unique=True, index=True)
    # 账户确认状态位
    confirmed = db.Column(db.Boolean, default=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.role is None:        # 如果创建基类对象后还没有定义角色，则根据电子邮件地址决定是否将其设为管理员或默认角色
            if self.email == current_app.config['FLASKY_ADMIN']:
                self.role = Role.query.filter_by(name='Administrator').first()
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()

    def can(self, perm):
        return self.role is not None and self.role.has_permission(perm)

    def is_administrator(self):
        return self.can(Permission.ADMIN)

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):       # 验证hash过后的password与原password是否一致
        return check_password_hash(self.password_hash, password)

    # 生成confirmation token
    def generate_confirmation_token(self, expiration=3600):  # 生成令牌
        # return jwt.encode(header={'alg': 'HS256'},  playload={'confirm': self.id}, key=current_app.config['SECRET_KEY'])
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'confirm': self.id}).decode('utf-8')

    # 确认用户
    def confirm(self, token):
        # try:
        #     data = jwt.decode(token, key=current_app.config['SECRET_KEY'])
        # except JoseError:
        #     return False
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token.encode('utf-8'))
        except:
            return False
        if data.get('confirm') != self.id:  # 如果传入的token解析出来的数据与数据库中不一致,则返回confirm操作False
            return False
        self.confirmed = True   # 确认位置True
        db.session.add(self)    # 提交数据库
        return True             # 返回confirm操作True

    # 生成重置密码token
    def generate_reset_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'reset': self.id}).decode('utf-8')

    # 重置密码
    @staticmethod
    def reset_password(token, new_password):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token.encode('utf-8'))  # 反序列化token，得到原始数据data
        except:
            return False
        user = User.quert.get(data.get('reset'))  # data.get('reset') == self.id
        if user is None:
            return False
        user.password = new_password       # 调用password()赋值新密码
        db.session.add(user)               # 添加对象user
        return True

    # 生成修改邮箱token
    def generate_email_change_token(self, new_email, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'change_email': self.id, 'new_mail': new_email}).decode('utf-8')

    # 修改邮箱
    def change_email(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token.encode('utf-8'))
        except:
            return False
        if data.get('change_email') != self.id:
            return False
        new_email = data.get('new_mail')
        if new_email is None:
            return False
        if self.query.filter_by(email=new_email).first() is not None:  # 如果数据库中有新提交的邮箱地址
            return False
        self.email = new_email
        db.session.add(self)
        return True

    def __repr__(self):
        return '<User %r>' % self.username

