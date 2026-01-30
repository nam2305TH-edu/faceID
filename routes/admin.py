from calendar import monthrange
import matplotlib
from pendulum import today
matplotlib.use("Agg")

from datetime import datetime, date
import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, User, Attendance
from face_utils import register_face, delete_face_encoding
import matplotlib.pyplot as plt
import numpy as np 
import re
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


ENV_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')


def admin_required(f):
    """Decorator kiểm tra quyền admin"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.role != 'admin':
            flash('Bạn không có quyền truy cập!', 'danger')
            return redirect(url_for('attendance.check_page'))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """Trang dashboard admin"""
    today = date.today()
    
    total_users = User.query.filter_by(role='employee').count()
    today_attendances = Attendance.query.filter_by(date=today).count()
    checked_in_today = Attendance.query.filter_by(date=today).filter(
        Attendance.check_in.isnot(None)
    ).count()
    checked_out_today = Attendance.query.filter_by(date=today).filter(
        Attendance.check_out.isnot(None)
    ).count()
    

    recent_attendance = Attendance.query.order_by(
        Attendance.check_in.desc()
    ).limit(5).all()
    data_sodo = [total_users, today_attendances, checked_in_today, checked_out_today] 
    labels = ['Tổng nhân viên', 'Điểm danh hôm nay', 'Đã check-in', 'Đã check-out']
    colors = ['#4e79a7', '#f28e2b', '#e15759', '#76b7b2']
    plt.figure(figsize=(8,6))
    plt.bar(labels, data_sodo, color=colors)
    try:
        if not os.path.exists('static/public_databoard/chart.png'):
            plt.title('Thống kê điểm danh hôm nay')
            plt.ylabel('Số lượng') 
            plt.savefig('static/public_databoard/chart.png')
            plt.close() 
        else:
            os.remove('static/public_databoard/chart.png')
            plt.title('Thống kê điểm danh hôm nay')
            plt.ylabel('Số lượng') 
            plt.savefig('static/public_databoard/chart.png')
            plt.close()
    except Exception as e:
        print(f"Lỗi khi lưu biểu đồ: {e}")
    return render_template('admin_dashboard.html',                         
                         total_users=total_users,
                         today_attendances=today_attendances,
                         checked_in_today=checked_in_today,
                         checked_out_today=checked_out_today,
                         recent_attendance=recent_attendance ) 
    
@admin_bp.route('/attendance')
@login_required
@admin_required
def view_attendance():
    """Xem lịch sử điểm danh"""
    date_filter = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    selected_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
    
    attendances = Attendance.query.filter_by(date=selected_date).order_by(
        Attendance.check_in.desc()
    ).all()
    
    return render_template('view_attendance.html', 
                         attendances=attendances, 
                         selected_date=date_filter)


@admin_bp.route('/users')
@login_required
@admin_required
def manage_users():
    """Quản lý nhân viên"""
    users = User.query.filter_by(role='employee').all()
    return render_template('manage_users.html', users=users)


@admin_bp.route('/add_user', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    """Thêm nhân viên mới"""
    if request.method == 'POST':
        try:
            data = request.json
            username = data.get('username')
            password = data.get('password')
            salary = data.get('salary')
            role = data.get('role')
            full_name = data.get('full_name')
            employee_id = data.get('employee_id')
            email = data.get('email')
            department = data.get('department')
            position = data.get('position')
            face_image = data.get('face_image') 
            
            # Kiểm tra username đã tồn tại
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                return jsonify({'error': 'Username đã tồn tại'}), 400
            
            # Kiểm tra employee_id đã tồn tại
            existing_emp = User.query.filter_by(employee_id=employee_id).first()
            if existing_emp:
                return jsonify({'error': 'Mã nhân viên đã tồn tại'}), 400
            
            # Tạo user mới
            new_user = User(
                username=username,
                full_name=full_name,
                employee_id=employee_id,
                email=email,
                salary =salary,
                department=department,
                position=position,
                role=role,
                face_registered=False
            )
            new_user.set_password(password)
            
            db.session.add(new_user)
            db.session.commit()
            
            # Đăng ký khuôn mặt nếu có ảnh
            if face_image:
                success, message = register_face(employee_id, face_image)
                if success:
                    new_user.face_registered = True
                    db.session.commit()
                    return jsonify({
                        'success': True, 
                        'message': 'Thêm nhân viên và đăng ký khuôn mặt thành công'
                    })
                else:
                    return jsonify({
                        'success': True, 
                        'message': f'Thêm nhân viên thành công nhưng đăng ký khuôn mặt thất bại: {message}',
                        'face_error': message
                    })
            
            return jsonify({
                'success': True, 
                'message': 'Thêm nhân viên thành công (chưa đăng ký khuôn mặt)'
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    return render_template('add_user.html')


@admin_bp.route('/register_face/<employee_id>', methods=['POST'])
@login_required
@admin_required
def register_employee_face(employee_id):
    """API đăng ký/cập nhật khuôn mặt cho nhân viên"""
    try:
        user = User.query.filter_by(employee_id=employee_id).first()
        if not user:
            return jsonify({'error': 'Không tìm thấy nhân viên'}), 404
        
        image_data = request.json.get('image')
        if not image_data:
            return jsonify({'error': 'Không có ảnh'}), 400
        
        success, message = register_face(employee_id, image_data)
        
        if success:
            user.face_registered = True
            db.session.commit()
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'error': message}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/user_info/<int:user_id>')
@login_required
@admin_required
def user_info(user_id):
    """API lấy thông tin chi tiết nhân viên"""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'error': 'Không tìm thấy nhân viên'}), 404
        
        # Lấy thống kê điểm danh tháng này
       
        
        
        
        from calendar import monthrange
         
        from datetime import date
 
        today = date.today()
        created_date = user.created_at.date()
        if today.year == created_date.year and today.month == created_date.month:
            start_date = created_date
        else:
            start_date = today.replace(day=1)

        """Ngày của tháng"""
        days_in_month = monthrange(today.year, today.month)[1]

        working_days = 0
        for day in range(start_date.day, min(today.day, days_in_month) + 1):
            d = date(today.year, today.month, day)
            if d.weekday() < 5:
                working_days += 1

        attendances = Attendance.query.filter(
            Attendance.employee_id == user.employee_id,
            Attendance.date >= start_date,
            Attendance.date <= today
        ).all()

        
        # Tính tổng lương tháng này
        total_work_minutes = sum(float(a.time_lam) for a in attendances if a.time_lam)
        total_work_hours = round(total_work_minutes / 60, 2)
        salary_per_hour = float(user.salary) if user.salary else 0
        total_salary = round(total_work_hours * salary_per_hour, 2)
        
        on_time = sum(1 for a in attendances if a.status == 'on_time')
        late = sum(1 for a in attendances if a.status == 'late')
        total_attendance = len(attendances)
        absent = working_days - total_attendance
        if absent < 0:
            absent = 0
        
        # Lấy ảnh khuôn mặt nếu có
        face_image = None
        face_path = f'faces/{user.employee_id}.jpg'
        if os.path.exists(face_path):
            import base64
            with open(face_path, 'rb') as f:
                face_data = base64.b64encode(f.read()).decode('utf-8')
                face_image = f'data:image/jpeg;base64,{face_data}'
        
        return jsonify({
            'success': True,
            'user': {
                'id': user.id,
                'employee_id': user.employee_id,
                'username': user.username,
                'full_name': user.full_name,
                'email': user.email,
                'salary': user.salary,
                'department': user.department,
                'position': user.position,
                'role': user.role,
                'face_registered': user.face_registered,
                'face_image': face_image,
                'created_at': user.created_at.strftime('%d/%m/%Y %H:%M'),
                'time_lam' : total_work_minutes,
                'total_work_hours': total_work_hours,
                'total_work_minutes': total_work_minutes
                
            },
            'stats': {
                'on_time': on_time,
                'late': late,
                'absent': absent,
                'total': total_attendance,
                'working_days': working_days,
                'total_work_hours': total_work_hours,
                'total_salary': total_salary
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/delete_user/<int:user_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_user(user_id):
    """API xóa nhân viên"""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'Không tìm thấy nhân viên'}), 404
        
        if user.role == 'admin':
            return jsonify({'error': 'Không thể xóa tài khoản admin'}), 400
        
        # Xóa face encoding
        delete_face_encoding(user.employee_id)
        
        # Xóa attendance records
        Attendance.query.filter_by(employee_id=user.employee_id).delete()
        
        # Xóa user
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Đã xóa nhân viên'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/settings')
@login_required
@admin_required
def settings():
    """Trang cài đặt hệ thống"""
    # Đọc cấu hình hiện tại từ .env
    work_start_time = os.getenv('WORK_START_TIME', '08:30')
    work_late_time = os.getenv('WORK_LATE_TIME', '09:00')
    work_end_time = os.getenv('WORK_END_TIME', '17:30')
    
    return render_template('settings.html',
                         work_start_time=work_start_time,
                         work_late_time=work_late_time,
                         work_end_time=work_end_time)






@admin_bp.route('/settings/update', methods=['POST'])
@login_required
@admin_required
def update_settings():
    """API cập nhật cài đặt hệ thống"""
    try:
        data = request.json
        work_start_time = data.get('work_start_time', '08:30')
        work_late_time = data.get('work_late_time', '09:00')
        work_end_time = data.get('work_end_time', '17:30')
        
        # Validate format HH:MM
        
        time_pattern = re.compile(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$')
        
        if not time_pattern.match(work_start_time):
            return jsonify({'error': 'Giờ vào làm không hợp lệ (định dạng HH:MM)'}), 400
        if not time_pattern.match(work_late_time):
            return jsonify({'error': 'Giờ đi muộn không hợp lệ (định dạng HH:MM)'}), 400
        if not time_pattern.match(work_end_time):
            return jsonify({'error': 'Giờ tan làm không hợp lệ (định dạng HH:MM)'}), 400
        
        # Đọc file .env hiện tại
        env_content = {}
        if os.path.exists(ENV_FILE_PATH):
            with open(ENV_FILE_PATH, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and '=' in line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        env_content[key] = value
        
        # Cập nhật giá trị
        env_content['WORK_START_TIME'] = work_start_time
        env_content['WORK_LATE_TIME'] = work_late_time
        env_content['WORK_END_TIME'] = work_end_time
        
        # Ghi lại file .env
        with open(ENV_FILE_PATH, 'w', encoding='utf-8') as f:
            for key, value in env_content.items():
                f.write(f'{key}={value}\n')
        
        # Cập nhật biến môi trường trong runtime
        os.environ['WORK_START_TIME'] = work_start_time
        os.environ['WORK_LATE_TIME'] = work_late_time
        os.environ['WORK_END_TIME'] = work_end_time
        
        # Reload config
        from config import load_dotenv
        load_dotenv(override=True)
        
        return jsonify({
            'success': True,
            'message': 'Cập nhật cài đặt thành công',
            'settings': {
                'work_start_time': work_start_time,
                'work_late_time': work_late_time,
                'work_end_time': work_end_time
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/update_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def update_user(user_id):
    """Cập nhật thông tin nhân viên"""
    user = User.query.get(user_id)
    if not user:
        flash('Không tìm thấy nhân viên!', 'danger')
        return redirect(url_for('admin.manage_users'))
    if request.method == 'POST':
        data = request.form
        user.full_name = data.get('full_name', user.full_name)
        user.email = data.get('email', user.email)
        user.department = data.get('department', user.department)
        user.position = data.get('position', user.position)
        salary = data.get('salary')
        if salary:
            try:
                user.salary = float(salary)
            except:
                pass
        db.session.commit()
        flash('Cập nhật thông tin thành công!', 'success')
        return redirect(url_for('admin.manage_users'))
    return render_template('update_user.html', user=user)


@admin_bp.route('/send_email_all', methods=['GET', 'POST'])
@login_required
@admin_required
def send_email_all():
    """Gửi email cho tất cả nhân viên"""
    from routes.annou import check_email, send_to_email
    if request.method == 'POST':
        subject = request.form.get('subject')
        content = request.form.get('content')
        if not check_email():
            flash('Chưa cấu hình email hoặc mật khẩu!', 'danger')
            return redirect(url_for('admin.send_email_all'))
        send_to_email(subject, content)
        flash('Đã gửi email cho tất cả nhân viên!', 'success')
        return redirect(url_for('admin.send_email_all'))
    return render_template('send_email_all.html')