from datetime import datetime, date, time
from decimal import Decimal
from app import create_app, db
from models import User, Attendance   # nếu models nằm trong app/models.py

def seed_test_data():
    app = create_app()            
    with app.app_context():        
        db.drop_all()
        db.create_all()

        user = User(
            username="test_employee",
            role="employee",
            full_name="Nguyễn Văn Test",
            email="test@example.com",
            salary=Decimal("50000.00"),  
            employee_id="EMP001",
            department="IT",
            position="Developer",
            face_registered=True
            
        )
        user.set_password("123456")

        db.session.add(user)
        db.session.commit()

        #  Tạo attendance: check-in 9:30, chưa check-out
        check_in_time = datetime.combine(
            date.today(),
            time(9, 30)
        )

        attendance = Attendance(
            user_id=user.id,
            employee_id=user.employee_id,
            full_name=user.full_name,
            check_in=check_in_time,
            check_out=None,
            time_lam=Decimal("0"),
            date=date.today(),
            status="present",
            department=user.department,
            position=user.position,
            check_in_image="uploads/abc.jpg"
        )

        db.session.add(attendance)
        db.session.commit()

        print("Đã tạo xong dữ liệu test")

if __name__ == "__main__":
    seed_test_data()
