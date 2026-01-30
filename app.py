from flask import Flask
from flask_login import LoginManager
from config import Config, WORK_START_TIME, WORK_LATE_TIME
from models import db, User, Attendance
from face_utils import load_known_faces, get_face_count

from routes.auth import auth_bp
from routes.attendance import attendance_bp
from routes.admin import admin_bp
from routes.employee import employee_bp
from routes.chat import chat_bp 
from flask import send_from_directory


def create_app():
    """Factory function tạo Flask app"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    db.init_app(app)
    
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(employee_bp)
    app.register_blueprint(chat_bp)
    
    return app

def init_database(app):
    """Tạo  tài khoản admin mặc định và khởi tạo database nếu chưa có"""
    with app.app_context():
        db.create_all()
        load_known_faces() 
app = create_app()

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory('uploads', filename)


if __name__ == '__main__':
    init_database(app)
    print("Server đang chạy tại: http://0.0.0.0:8080")
    print("chạy: ngrok http 8080")
    app.run(debug=True, host='0.0.0.0', port=8080)
