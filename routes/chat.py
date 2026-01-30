import asyncio
import traceback
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user

chat_bp = Blueprint('chat', __name__, url_prefix='/chat')

_brain = None
_init_error = None

def get_brain():
    global _brain, _init_error
    if _brain is None and _init_error is None:
        try:
            # Thử lấy instance từ main trước
            from main import get_brain_instance
            _brain = get_brain_instance()
            if _brain is not None:
                print("Sử dụng TmeBrain instance từ main.py")
                return _brain, _init_error
        except ImportError:
            pass
        
        # Nếu không có, tự khởi tạo (fallback)
        try:
            from Search_OpenAI.brain import TmeBrain
            _brain = TmeBrain()
            print("TmeBrain initialized successfully!")
        except Exception as e:
            _init_error = str(e)
            print(f"Error initializing TmeBrain: {e}")
            traceback.print_exc()
    return _brain, _init_error

def set_brain(brain_instance):
    """Cho phép set brain instance từ bên ngoài"""
    global _brain
    _brain = brain_instance


@chat_bp.route('/')
@login_required
def index():
    """Trang ChatAI"""
    return render_template('chat.html')


@chat_bp.route('/ask', methods=['POST'])
@login_required
def ask():
    try:
        data = request.json
        query = data.get('query', '').strip()
        session_id = data.get('session_id')
        
        if not query:
            return jsonify({'success': False, 'error': 'Vui lòng nhập câu hỏi'}), 400
        
        brain, init_error = get_brain()
        if brain is None:
            error_msg = f'ChatAI chưa được cấu hình. Lỗi: {init_error}' if init_error else 'ChatAI chưa được cấu hình.'
            return jsonify({
                'success': False, 
                'error': error_msg
            }), 500
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(brain.ask_tme(query, session_id))
        finally:
            loop.close()
        
        return jsonify({
            'success': True,
            'answer': result.get('answer', ''),
            'session_id': result.get('session_id', ''),
            'user': current_user.full_name
        })
        
    except Exception as e:
        print(f"Chat error: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@chat_bp.route('/history')
@login_required
def history():
    """Lấy lịch sử chat (nếu có)"""
    try:
        brain, _ = get_brain()
        if brain is None:
            return jsonify({'success': True, 'history': []})
        
        # Có thể mở rộng để lấy lịch sử từ database
        return jsonify({'success': True, 'history': []})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
