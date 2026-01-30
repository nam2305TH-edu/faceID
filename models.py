from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """Model người dùng (Admin và Nhân viên)"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'admin' hoặc 'employee'
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120))
    salary = db.Column(db.Numeric(10, 2), nullable=False) 
    employee_id = db.Column(db.String(50), unique=True)
    department = db.Column(db.String(100))
    position = db.Column(db.String(100))
    face_registered = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Attendance(db.Model):
    """Model điểm danh"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    employee_id = db.Column(db.String(50))
    full_name = db.Column(db.String(100))
    check_in = db.Column(db.DateTime)
    check_out = db.Column(db.DateTime)
    time_lam = db.Column(db.Numeric(5, 2))
    date = db.Column(db.Date, default=date.today)
    status = db.Column(db.String(20), default='present')  
    check_in_image = db.Column(db.String(200))
    check_out_image = db.Column(db.String(200))
    department = db.Column(db.String(100))
    position = db.Column(db.String(100))
    luong = db.Column(db.Numeric(10, 2)) 
    
    user = db.relationship('User', backref=db.backref('attendances', lazy=True))

    def calculate_salary(self):
        hours = (self.time_lam or 0) / 60.0
        salary_per_hour = self.user.salary if self.user and self.user.salary else 0
        luong = round(hours * salary_per_hour, 2)
        self.luong = luong
        return luong