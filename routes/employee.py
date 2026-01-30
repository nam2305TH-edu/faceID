import os
import base64
from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Attendance

employee_bp = Blueprint('employee', __name__, url_prefix='/employee')



def employee_required(f):
    """Decorator kiểm tra quyền employee"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.role != 'employee':
            flash('Bạn không có quyền truy cập!', 'danger')
            return redirect(url_for('attendance.index'))
        return f(*args, **kwargs)
    return decorated_function


@employee_bp.route('/dashboard')
@login_required
@employee_required
def dashboard():
    """Trang dashboard nhân viên"""
    today = date.today()
    user_attendance = Attendance.query.filter_by(
        employee_id=current_user.employee_id,
        date=today
    ).first()
    
    # Lấy lịch sử 7 ngày gần nhất
    history = Attendance.query.filter_by(
        employee_id=current_user.employee_id
    ).order_by(Attendance.date.desc()).limit(7).all() 
    
   #thống kê
    total_check_ins = Attendance.query.filter_by(
        employee_id=current_user.employee_id
    ).count()
    total_check_outs = Attendance.query.filter_by(
        employee_id=current_user.employee_id
    ).filter(Attendance.check_out.isnot(None)).count(
        
    )
    
   
    """Thời gian làm việc lấy từ database"""
    total_working_hours = db.session.query(db.func.sum(Attendance.time_lam )).filter(
        Attendance.employee_id == current_user.employee_id
    ).scalar() or 0
    from decimal import Decimal
    total_working_hours = round(total_working_hours / Decimal(60), 2)


    """Tổng số lương của nhân viên"""
    total_salary = db.session.query(db.func.sum(Attendance.luong)).filter(
        Attendance.employee_id == current_user.employee_id
    ).scalar() or 0.0

    return render_template('employee_dashboard.html',
                         today_attendance=user_attendance,
                         history=history,
                         current_user=current_user,
                         total_check_ins=total_check_ins,
                         total_check_outs=total_check_outs,
                         total_working_hours=total_working_hours,
                         total_salary=total_salary
                         )


@employee_bp.route('/attendance-history')
@login_required
@employee_required
def attendance_history():
    """Lịch sử điểm danh của nhân viên"""
    # Lấy tất cả lịch sử điểm danh
    history = Attendance.query.filter_by(
        employee_id=current_user.employee_id
    ).order_by(Attendance.date.desc()).all()
    
    return render_template('attendance_history.html', history=history)


@employee_bp.route('/check-in', methods=['POST'])
@login_required
@employee_required
def check_in():
    """Check-in cho nhân viên đã đăng nhập"""
    try:
        # Lấy ảnh từ request
        image_data = request.json.get('image')
        if not image_data:
            return jsonify({'error': 'No image provided'}), 400
        
        # Decode base64 image
        face_data = image_data.split(',')[1] if ',' in image_data else image_data
        image_bytes = base64.b64decode(face_data)
        
        # Lưu ảnh check-in
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"checkin_{current_user.id}_{timestamp}.jpg"
        image_path = os.path.join('uploads', filename)
        
        with open(image_path, 'wb') as f:
            f.write(image_bytes)
        
        today = date.today()
        now = datetime.now()
        
        # Kiểm tra đã check-in hôm nay chưa
        existing = Attendance.query.filter_by(
            employee_id=current_user.employee_id,
            date=today
        ).first()
        
        if existing:
            return jsonify({'error': 'Bạn đã check-in hôm nay rồi'}), 400
        
        # Tạo bản ghi điểm danh
        attendance = Attendance(
            user_id=current_user.id,
            employee_id=current_user.employee_id,
            full_name=current_user.full_name,
            check_in=now,
            date=today,
            check_in_image=image_path,
            status='present',
            department=current_user.department,
            position=current_user.position
        )
        
        db.session.add(attendance)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Check-in thành công'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500



