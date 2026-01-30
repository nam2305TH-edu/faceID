import os
import pickle
import base64
import numpy as np
from PIL import Image
import io
import face_recognition
from datetime import datetime

# Cache lưu face encodings để tăng tốc độ
known_face_encodings = []
known_face_ids = []


def load_known_faces():
    """Load tất cả face encodings từ file vào memory"""
    global known_face_encodings, known_face_ids
    known_face_encodings = []
    known_face_ids = []
    
    encoding_file = os.path.join('faces', 'encodings.pkl')
    if os.path.exists(encoding_file):
        try:
            with open(encoding_file, 'rb') as f:
                data = pickle.load(f)
                known_face_encodings = data.get('encodings', [])
                known_face_ids = data.get('employee_ids', [])
            print(f"Đã load {len(known_face_encodings)} khuôn mặt từ database")
        except Exception as e:
            print(f"Lỗi load encodings: {e}")


def save_known_faces():
    """Lưu face encodings vào file"""
    encoding_file = os.path.join('faces', 'encodings.pkl')
    try:
        with open(encoding_file, 'wb') as f:
            pickle.dump({
                'encodings': known_face_encodings,
                'employee_ids': known_face_ids
            }, f)
        print(f"Đã lưu {len(known_face_encodings)} khuôn mặt")
    except Exception as e:
        print(f"Lỗi lưu encodings: {e}")


def encode_face_from_image(image_path):
    """Tạo face encoding từ ảnh"""
    try:
        # Đọc ảnh bằng PIL để xử lý đúng định dạng
        pil_image = Image.open(image_path)
        
        if pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')
        
        # Chuyển thành numpy array
        rgb_img = np.array(pil_image, dtype=np.uint8)
        rgb_img = np.ascontiguousarray(rgb_img)
        
        # Detect faces
        face_locations = face_recognition.face_locations(rgb_img)
        
        if len(face_locations) == 0:
            return None, "Không tìm thấy khuôn mặt trong ảnh"
        
        if len(face_locations) > 1:
            return None, "Phát hiện nhiều khuôn mặt, vui lòng chỉ có 1 người trong ảnh"
        
        face_encodings = face_recognition.face_encodings(rgb_img, face_locations)
        if len(face_encodings) > 0:
            return face_encodings[0], None
        
        return None, "Không thể encode khuôn mặt"
    except Exception as e:
        return None, str(e)


def register_face(employee_id, image_data_or_path):
    """Đăng ký khuôn mặt cho nhân viên - hỗ trợ cả base64 và file path"""
    global known_face_encodings, known_face_ids
    
    try:
        if isinstance(image_data_or_path, str) and (
            image_data_or_path.startswith('data:') or 
            ',' in image_data_or_path or 
            len(image_data_or_path) > 500
        ):
            if ',' in image_data_or_path:
                image_data_or_path = image_data_or_path.split(',')[1]
            image_bytes = base64.b64decode(image_data_or_path)
            pil_image = Image.open(io.BytesIO(image_bytes))
        else:
            pil_image = Image.open(image_data_or_path)
        
        if pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')
        
        # Chuyển thành numpy array
        rgb_img = np.array(pil_image, dtype=np.uint8)
        rgb_img = np.ascontiguousarray(rgb_img)
        
        # Detect faces
        face_locations = face_recognition.face_locations(rgb_img)
        
        if len(face_locations) == 0:
            return False, "Không tìm thấy khuôn mặt trong ảnh"
        
        if len(face_locations) > 1:
            return False, "Phát hiện nhiều khuôn mặt, vui lòng chỉ có 1 người trong ảnh"
        
        # Encode face
        face_encodings = face_recognition.face_encodings(rgb_img, face_locations)
        if len(face_encodings) == 0:
            return False, "Không thể encode khuôn mặt"
        
        encoding = face_encodings[0]
        
        # Xóa encoding cũ nếu có
        if employee_id in known_face_ids:
            idx = known_face_ids.index(employee_id)
            known_face_encodings.pop(idx)
            known_face_ids.pop(idx)
        
        # Thêm encoding mới
        known_face_encodings.append(encoding)
        known_face_ids.append(employee_id)
        
        # Lưu vào file
        save_known_faces()
        
        # Lưu ảnh gốc dưới dạng JPEG đúng chuẩn
        face_image_path = os.path.join('faces', f'{employee_id}.jpg')
        pil_image.save(face_image_path, 'JPEG', quality=95)
        
        return True, "Đăng ký khuôn mặt thành công"
        
    except Exception as e:
        return False, f"Lỗi: {str(e)}"


def recognize_face_from_image(image_data):
    """Nhận diện khuôn mặt từ ảnh base64"""
    global known_face_encodings, known_face_ids
    
    if len(known_face_encodings) == 0:
        return None, "Chưa có dữ liệu khuôn mặt nào được đăng ký"
    
    try:
        # Decode base64 image
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        image_bytes = base64.b64decode(image_data)
        
        # Đọc ảnh bằng PIL
        pil_image = Image.open(io.BytesIO(image_bytes))
        
        # Resize nhỏ hơn để giảm RAM (max 400px)
        max_size = 400
        if pil_image.width > max_size or pil_image.height > max_size:
            ratio = min(max_size / pil_image.width, max_size / pil_image.height)
            new_size = (int(pil_image.width * ratio), int(pil_image.height * ratio))
            pil_image = pil_image.resize(new_size, Image.LANCZOS)
        
        # Chuyển sang RGB
        if pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')
        
        # Chuyển thành numpy array
        rgb_img = np.array(pil_image, dtype=np.uint8)
        rgb_img = np.ascontiguousarray(rgb_img)
        
        # Detect faces với model HOG (nhẹ hơn CNN)
        try:
            face_locations = face_recognition.face_locations(rgb_img, model="hog", number_of_times_to_upsample=1)
        except Exception as e:
            print(f"Face detection error: {e}")
            return None, "Lỗi phát hiện khuôn mặt"
        
        if len(face_locations) == 0:
            return None, "Không phát hiện khuôn mặt"
        
        # Encode face
        try:
            face_encodings = face_recognition.face_encodings(rgb_img, face_locations, num_jitters=1)
        except Exception as e:
            print(f"Face encoding error: {e}")
            return None, "Lỗi mã hóa khuôn mặt"
        
        if len(face_encodings) == 0:
            return None, "Không thể nhận diện khuôn mặt"
        
        # So sánh với known faces
        for face_encoding in face_encodings:
            matches = face_recognition.compare_faces(
                known_face_encodings, face_encoding, tolerance=0.5
            )
            face_distances = face_recognition.face_distance(
                known_face_encodings, face_encoding
            )
            
            if len(face_distances) > 0:
                best_match_index = np.argmin(face_distances)
                if matches[best_match_index]:
                    confidence = 1 - face_distances[best_match_index]
                    employee_id = known_face_ids[best_match_index]
                    return employee_id, confidence
        
        return None, "Không nhận diện được - khuôn mặt chưa được đăng ký"
        
    except Exception as e:
        print(f"Recognition error: {e}")
        return None, f"Lỗi: {str(e)}"


def get_attendance_status(check_in_time):
    """Xác định trạng thái điểm danh dựa trên giờ check-in"""
    # Đọc cấu hình động từ environment
    work_late_time = os.getenv('WORK_LATE_TIME', '09:00')
    late_time = datetime.strptime(work_late_time, '%H:%M').time()
    
    if check_in_time.time() <= late_time:
        return 'present'  # Đúng giờ
    else:
        return 'late'  # Đi trễ


def delete_face_encoding(employee_id):
    """Xóa face encoding của nhân viên"""
    global known_face_encodings, known_face_ids
    
    if employee_id in known_face_ids:
        idx = known_face_ids.index(employee_id)
        known_face_encodings.pop(idx)
        known_face_ids.pop(idx)
        save_known_faces()
        
        # Xóa ảnh face nếu có
        face_path = os.path.join('faces', f'{employee_id}.jpg')
        if os.path.exists(face_path):
            os.remove(face_path)
        
        return True
    return False


def get_face_count():
    """Lấy số lượng khuôn mặt đã đăng ký"""
    return len(known_face_encodings)
