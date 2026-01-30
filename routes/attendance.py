import os
import base64
from datetime import datetime, date
from flask import Blueprint, render_template, request, jsonify
from models import db, User, Attendance
from face_utils import recognize_face_from_image, get_attendance_status
from config import WORK_START_TIME, WORK_LATE_TIME, WORK_END_TIME 
import time
attendance_bp = Blueprint('attendance', __name__)

work_start_time = datetime.strptime(WORK_START_TIME, '%H:%M').time()
work_end_time = datetime.strptime(WORK_END_TIME, '%H:%M').time()

@attendance_bp.route('/')
def index():
    """Trang chủ - chuyển đến trang điểm danh"""
    return render_template('attendance_public.html')


@attendance_bp.route('/attendance')
def check_page():
    """Trang điểm danh công khai không cần đăng nhập"""
    return render_template('attendance_public.html')


@attendance_bp.route('/attendance/check', methods=['POST'])
def check_attendance():
    """API check-in/check-out với face recognition"""
    try:
        image_data = request.json.get('image')
        if not image_data:
            return jsonify({'error': 'Không có ảnh được gửi lên'}), 400
        
        # Nhận diện khuôn mặt
        employee_id, result = recognize_face_from_image(image_data)
        
        if employee_id is None:
            return jsonify({
                'success': False,
                'error': result,
                'type': 'recognition_failed'
            }), 400
        
        # Tìm user trong database
        user = User.query.filter_by(employee_id=employee_id).first()
        
        if not user:
            return jsonify({'error': 'Không tìm thấy thông tin nhân viên'}), 404
        
        # Lưu ảnh check-in/out
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        face_data = image_data.split(',')[1] if ',' in image_data else image_data
        image_bytes = base64.b64decode(face_data)
        image_path = os.path.join('uploads', f'{employee_id}_{timestamp}.jpg')
        with open(image_path, 'wb') as f:
            f.write(image_bytes)
        
        today = date.today()
        now = datetime.now()
        
        """Kiểm tra xem đã check-in hôm nay chưa"""
        existing_attendance = Attendance.query.filter_by(
            employee_id=user.employee_id,
            date=today
        ).first()
        
        confidence_percent = round(result * 100, 1) if isinstance(result, float) else 0
        
        if existing_attendance:
            """Đã check-in, thực hiện check-out"""
            if existing_attendance.check_out:
                return jsonify({
                    'success': False,
                    'message': 'Bạn đã check-out hôm nay rồi!',
                    'type': 'already_checked_out'
                })
            MIN_WORK_MINUTES = 30
            time_since_checkin = (now - existing_attendance.check_in).total_seconds() / 60
            if time_since_checkin < MIN_WORK_MINUTES:
                remaining = int(MIN_WORK_MINUTES - time_since_checkin)
                return jsonify({
                    'success': False,
                    'message': f'Chưa đủ thời gian làm việc! Còn {remaining} phút nữa mới được check-out.',
                    'type': 'too_early_checkout'
                })
            
            """Thêm các chỉ số khi check_out, time làm việc"""           
            work_hours = 0
            work_minutes = 0
            try:
              
                existing_attendance.check_out = now
                if existing_attendance.check_in.time() < work_start_time:
                    existing_attendance.check_in = datetime.combine(existing_attendance.check_in.date(), work_start_time)
                if existing_attendance.check_out.time() > work_end_time:
                    existing_attendance.check_out = datetime.combine(existing_attendance.check_out.date(), work_end_time)
                time_lam_date = existing_attendance.check_out - existing_attendance.check_in
                work_hours = time_lam_date.seconds // 3600
                work_minutes = (time_lam_date.seconds % 3600) // 60
                # check_out_image luôn cập nhật
                existing_attendance.check_out_image = image_path
                from decimal import Decimal
                existing_attendance.time_lam = Decimal(work_hours * 60 + work_minutes)
                existing_attendance.luong = (existing_attendance.time_lam / Decimal(60)) * user.salary
                db.session.commit()
            except Exception as e:
                print("Lỗi khi tính time làm :"+str(e))
    
            return jsonify({
                'success': True,
                'type': 'check_out',
                'message': f'Check-out thành công! Làm việc: {work_hours}h {work_minutes}p',
                'confidence': confidence_percent,
                'employee': {
                    'id': user.employee_id,
                    'name': user.full_name,
                    'department': user.department or 'N/A',
                    'check_in': existing_attendance.check_in.strftime('%H:%M:%S') if existing_attendance.check_in else None,
                    'check_out': existing_attendance.check_out.strftime('%H:%M:%S') if existing_attendance.check_out else None
                }
            })
        else:
            # Chưa check-in, thực hiện check-in
            status = get_attendance_status(now)
            
            new_attendance = Attendance(
                user_id=user.id,
                employee_id=user.employee_id,
                full_name=user.full_name,
                check_in=now,
                date=today,
                check_in_image=image_path,
                status=status,
                department=user.department,
                position=user.position,
                time_lam=0,
                luong=0.0
            )
            
            db.session.add(new_attendance)
            db.session.commit()
            
            status_text = 'Đúng giờ' if status == 'present' else 'Đi trễ'
            
            return jsonify({
                'success': True,
                'type': 'check_in',
                'message': f'Check-in thành công! ({status_text})',
                'confidence': confidence_percent,
                'status': status,
                'employee': {
                    'id': user.employee_id,
                    'name': user.full_name,
                    'department': user.department or 'N/A',
                    'check_in': now.strftime('%H:%M:%S')
                }
            })
            
    except Exception as e:
        db.session.rollback()
        print(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@attendance_bp.route('/attendance/recognize', methods=['POST'])
def recognize_face():
    """API nhận diện khuôn mặt không cần check-in"""
    try:
        image_data = request.json.get('image')
        if not image_data:
            return jsonify({'error': 'Không có ảnh được gửi lên'}), 400
        
        # Debug: log kích thước ảnh
        print(f"Received image data length: {len(image_data)}")
        
        # Nhận diện khuôn mặt
        employee_id, result = recognize_face_from_image(image_data)
        
        # Debug: log kết quả
        print(f"Recognition result: employee_id={employee_id}, result={result}")
        
        if employee_id is None:
            return jsonify({
                'success': False,
                'error': result
            })
        
        user = User.query.filter_by(employee_id=employee_id).first()
        
        if not user:
            return jsonify({'error': 'Không tìm thấy thông tin'}), 404
        
        today = date.today()
        attendance = Attendance.query.filter_by(
            employee_id=user.employee_id,
            date=today
        ).first()
        
        confidence_percent = round(result * 100, 1) if isinstance(result, float) else 0
        
        response_data = {
            'success': True,
            'confidence': confidence_percent,
            'employee': {
                'id': user.employee_id,
                'name': user.full_name,
                'department': user.department or 'Chưa phân công',
                'position': user.position or 'Nhân viên'
            },
            'attendance': None
        }
        
        if attendance:
            response_data['attendance'] = {
                'has_checked_in': attendance.check_in is not None,
                'has_checked_out': attendance.check_out is not None,
                'check_in_time': attendance.check_in.strftime('%H:%M:%S') if attendance.check_in else None,
                'check_out_time': attendance.check_out.strftime('%H:%M:%S') if attendance.check_out else None,
                'status': attendance.status
            }
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Recognition error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@attendance_bp.route('/attendance/status')
def attendance_status():
    """Trạng thái điểm danh hiện tại"""
    today = date.today()
    attendances = Attendance.query.filter_by(date=today).all()
    
    stats = {
        'total': len(attendances),
        'checked_in': len([a for a in attendances if a.check_in]),
        'checked_out': len([a for a in attendances if a.check_out]),
        'present_now': len([a for a in attendances if a.check_in and not a.check_out])
    }
    
    return jsonify(stats)


@attendance_bp.route('/attendance/today')
def today_attendance():
    """Danh sách điểm danh hôm nay"""
    today = date.today()
    attendances = Attendance.query.filter_by(date=today).order_by(Attendance.check_in.desc()).all()
    
    result = []
    for att in attendances:
        result.append({
            'employee_id': att.employee_id,
            'full_name': att.full_name,
            'check_in': att.check_in.strftime('%H:%M:%S') if att.check_in else None,
            'check_out': att.check_out.strftime('%H:%M:%S') if att.check_out else None,
            'status': att.status
        })
    
    return jsonify(result)
