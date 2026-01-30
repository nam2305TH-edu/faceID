from app import app, init_database
from config import WORK_START_TIME, WORK_LATE_TIME
from face_utils import get_face_count

_brain_instance = None

def init_search_system():
    """Khởi tạo hệ thống Search/ChatAI khi start server"""
    global _brain_instance
    try:
        from Search_OpenAI.brain import TmeBrain
        print("Đang khởi tạo hệ thống Search AI...")
        _brain_instance = TmeBrain()
        print(" Hệ thống Search AI đã sẵn sàng!")
        
        # Gán instance cho route chat
        try:
            from routes.chat import set_brain
            set_brain(_brain_instance)
            print(" Đã kết nối Search AI với Chat route!")
        except Exception as e:
            print(f" Không thể kết nối với Chat route: {e}")
        
        return _brain_instance
    except Exception as e:
        print(f"Không thể khởi tạo Search AI: {e}")
        return None

def get_brain_instance():
    """Lấy instance TmeBrain đã được khởi tạo"""
    global _brain_instance
    return _brain_instance

if __name__ == '__main__':
    init_database(app)
    print(f"Giờ bắt đầu làm việc: {WORK_START_TIME}")
    print(f"Giờ tính đi trễ: {WORK_LATE_TIME}")
    
    # Khởi tạo hệ thống Search AI
    init_search_system()
    
    print("Server đang chạy tại: http://0.0.0.0:8080")
    print("Để sử dụng với ngrok, chạy: ngrok http 8080")
    app.run(debug=True, host='0.0.0.0', port=8080)
