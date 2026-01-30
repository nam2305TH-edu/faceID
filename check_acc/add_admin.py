from datetime import datetime
from app import create_app, db   # chỉnh lại theo cấu trúc project của bạn
from app import User       # đường dẫn tới model User

def create_admin():
    app = create_app()

    with app.app_context():
        # Kiểm tra xem admin đã tồn tại chưa
        existing_admin = User.query.filter_by(username="admin").first()
        if existing_admin:
            print("có rồi")
            return

        admin = User(
            username="admin",
            role="admin",
            full_name="Administrator",
            email="admin@example.com",
            salary=0,
            employee_id="ADMIN001",
            department="System",
            position="Administrator",
            face_registered=False,
            created_at=datetime.now()
        )

        admin.set_password("admin123")  

        db.session.add(admin)
        db.session.commit()

        print("oke")
        print("admin")
        print("admin123")

if __name__ == "__main__":
    create_admin()
