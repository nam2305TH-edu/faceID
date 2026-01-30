"""
Routes xác thực (đăng nhập, đăng xuất, quản lý mật khẩu)
"""
import random
import string
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, login_required, logout_user, current_user
from models import User, db
from face_utils import recognize_face_from_image

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Trang đăng nhập cho admin"""
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        else:
            return redirect(url_for('employee.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash('Đăng nhập thành công!', 'success')
            if user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            else:
                return redirect(url_for('employee.dashboard'))
        else:
            flash('Tên đăng nhập hoặc mật khẩu không đúng!', 'danger')
    
    return render_template('login.html')


@auth_bp.route('/login/face', methods=['POST'])
def login_face():
    """API đăng nhập bằng FaceID"""
    try:
        image_data = request.json.get('image')
        if not image_data:
            return jsonify({'success': False, 'error': 'Không có ảnh được gửi lên'}), 400
        
        # Nhận diện khuôn mặt
        employee_id, result = recognize_face_from_image(image_data)
        
        if employee_id is None:
            return jsonify({
                'success': False,
                'error': result or 'Không nhận diện được khuôn mặt'
            }), 400
        
        # Tìm user trong database
        user = User.query.filter_by(employee_id=employee_id).first()
        
        if not user:
            return jsonify({
                'success': False,
                'error': 'Không tìm thấy thông tin nhân viên trong hệ thống'
            }), 404
        
        # Kiểm tra user đã đăng ký khuôn mặt chưa
        if not user.face_registered:
            return jsonify({
                'success': False,
                'error': 'Tài khoản chưa đăng ký khuôn mặt'
            }), 400
        
        # Đăng nhập user
        login_user(user)
        
        confidence_percent = round(result * 100, 1) if isinstance(result, float) else 0
        
        # Xác định redirect URL
        redirect_url = url_for('admin.dashboard') if user.role == 'admin' else url_for('employee.dashboard')
        
        return jsonify({
            'success': True,
            'message': f'Xin chào {user.full_name}!',
            'confidence': confidence_percent,
            'user': {
                'id': user.employee_id,
                'name': user.full_name,
                'role': user.role,
                'department': user.department or 'N/A'
            },
            'redirect_url': redirect_url
        })
        
    except Exception as e:
        print(f"Face login error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@auth_bp.route('/logout')
@login_required
def logout():
    """Đăng xuất"""
    logout_user()
    return redirect(url_for('attendance.check_page'))


# ==================== Password Recovery Routes ====================

@auth_bp.route('/password/recovery')
def password_recovery():
    """Trang quên/đổi mật khẩu"""
    return render_template('password_recovery.html')


@auth_bp.route('/password/forgot', methods=['POST'])
def forgot_password():
    """API quên mật khẩu - quét FaceID để cấp mật khẩu mới"""
    try:
        image_data = request.json.get('image')
        if not image_data:
            return jsonify({'success': False, 'error': 'Không có ảnh được gửi lên'}), 400
        
        # Nhận diện khuôn mặt
        employee_id, result = recognize_face_from_image(image_data)
        
        if employee_id is None:
            return jsonify({
                'success': False,
                'error': result or 'Không nhận diện được khuôn mặt'
            }), 400
        
        # Tìm user trong database
        user = User.query.filter_by(employee_id=employee_id).first()
        
        if not user:
            return jsonify({
                'success': False,
                'error': 'Không tìm thấy thông tin nhân viên trong hệ thống'
            }), 404
        
        if not user.face_registered:
            return jsonify({
                'success': False,
                'error': 'Tài khoản chưa đăng ký khuôn mặt'
            }), 400
        
        # Tạo mật khẩu mới 6 chữ số
        new_password = ''.join(random.choices(string.digits, k=6))
        user.set_password(new_password)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Đã cấp mật khẩu mới thành công!',
            'new_password': new_password,
            'user': {
                'id': user.employee_id,
                'name': user.full_name,
                'department': user.department or 'N/A'
            }
        })
        
    except Exception as e:
        print(f"Forgot password error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@auth_bp.route('/password/change', methods=['POST'])
def change_password():
    """API đổi mật khẩu bằng mật khẩu cũ"""
    try:
        data = request.json
        username = data.get('username')
        old_password = data.get('old_password')
        new_password = data.get('new_password')
        
        if not all([username, old_password, new_password]):
            return jsonify({'success': False, 'error': 'Vui lòng nhập đầy đủ thông tin'}), 400
        
        if len(new_password) < 6:
            return jsonify({'success': False, 'error': 'Mật khẩu mới phải có ít nhất 6 ký tự'}), 400
        
        # Tìm user
        user = User.query.filter_by(username=username).first()
        
        if not user:
            return jsonify({'success': False, 'error': 'Không tìm thấy tài khoản'}), 404
        
        # Kiểm tra mật khẩu cũ
        if not user.check_password(old_password):
            return jsonify({'success': False, 'error': 'Mật khẩu cũ không đúng'}), 400
        
        # Đổi mật khẩu
        user.set_password(new_password)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Đổi mật khẩu thành công!'
        })
        
    except Exception as e:
        print(f"Change password error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@auth_bp.route('/password/verify-face', methods=['POST'])
def verify_face_for_password():
    """API xác thực FaceID để đổi mật khẩu"""
    try:
        image_data = request.json.get('image')
        if not image_data:
            return jsonify({'success': False, 'error': 'Không có ảnh được gửi lên'}), 400
        
        # Nhận diện khuôn mặt
        employee_id, result = recognize_face_from_image(image_data)
        
        if employee_id is None:
            return jsonify({
                'success': False,
                'error': result or 'Không nhận diện được khuôn mặt'
            }), 400
        
        # Tìm user trong database
        user = User.query.filter_by(employee_id=employee_id).first()
        
        if not user:
            return jsonify({
                'success': False,
                'error': 'Không tìm thấy thông tin nhân viên trong hệ thống'
            }), 404
        
        if not user.face_registered:
            return jsonify({
                'success': False,
                'error': 'Tài khoản chưa đăng ký khuôn mặt'
            }), 400
        
        return jsonify({
            'success': True,
            'message': 'Xác thực khuôn mặt thành công!',
            'user': {
                'id': user.employee_id,
                'name': user.full_name,
                'department': user.department or 'N/A'
            }
        })
        
    except Exception as e:
        print(f"Verify face error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@auth_bp.route('/password/change-by-face', methods=['POST'])
def change_password_by_face():
    """API đổi mật khẩu sau khi đã xác thực FaceID"""
    try:
        data = request.json
        user_id = data.get('user_id')
        new_password = data.get('new_password')
        
        if not all([user_id, new_password]):
            return jsonify({'success': False, 'error': 'Vui lòng nhập đầy đủ thông tin'}), 400
        
        if len(new_password) < 6:
            return jsonify({'success': False, 'error': 'Mật khẩu mới phải có ít nhất 6 ký tự'}), 400
        
        # Tìm user
        user = User.query.filter_by(employee_id=user_id).first()
        
        if not user:
            return jsonify({'success': False, 'error': 'Không tìm thấy tài khoản'}), 404
        
        # Đổi mật khẩu
        user.set_password(new_password)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Đổi mật khẩu thành công!'
        })
        
    except Exception as e:
        print(f"Change password by face error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
