# 🎯 Hệ Thống Điểm Danh Nhận Diện Khuôn Mặt

Hệ thống điểm danh tự động sử dụng công nghệ nhận diện khuôn mặt (Face Recognition) được xây dựng với Flask, hỗ trợ quản lý nhân viên, theo dõi chấm công và tích hợp AI chatbot.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.3.3-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## 📋 Tính Năng Chính

### 🔐 Xác thực & Phân quyền
- Đăng nhập/đăng xuất với Flask-Login
- Phân quyền Admin và Nhân viên
- Quản lý tài khoản người dùng

### 👤 Nhận Diện Khuôn Mặt
- Check-in/Check-out bằng nhận diện khuôn mặt
- Đăng ký khuôn mặt cho nhân viên mới
- Độ chính xác cao với thư viện `face_recognition`
- Lưu trữ face encodings để tối ưu tốc độ

### 📊 Quản Lý Điểm Danh
- Theo dõi thời gian check-in/check-out
- Tính toán giờ làm việc tự động
- Tính lương theo giờ làm việc
- Báo cáo đi muộn/đúng giờ

### 👨‍💼 Quản Lý Admin
- Dashboard tổng quan
- Quản lý nhân viên (thêm/sửa/xóa)
- Xem lịch sử điểm danh
- Cấu hình thời gian làm việc

### 🤖 AI Chatbot (Search_OpenAI)
- Tích hợp LLM (Llama 3.1 qua Groq)
- Tìm kiếm thông tin với Tavily API
- Lưu trữ lịch sử chat với ChromaDB
- Thông báo qua Telegram

## 🏗️ Cấu Trúc Dự Án

```
diemdanh/
├── app.py                  # Flask app factory
├── main.py                 # Entry point
├── config.py               # Cấu hình ứng dụng
├── models.py               # Database models (User, Attendance)
├── face_utils.py           # Xử lý nhận diện khuôn mặt
├── requirement.txt         # Dependencies
├── Dockerfile              # Docker image
├── Docker-compose.yaml     # Docker compose config
├── .env                    # Environment variables
│
├── routes/                 # API Routes
│   ├── auth.py            # Xác thực
│   ├── attendance.py      # Điểm danh
│   ├── admin.py           # Quản lý admin
│   ├── employee.py        # Nhân viên
│   └── chat.py            # AI Chatbot
│
├── Search_OpenAI/          # AI Module
│   ├── brain.py           # Core AI logic
│   ├── search.py          # Search manager
│   ├── database.py        # Vector database
│   └── telegram_service.py # Telegram notifications
│
├── templates/              # HTML Templates
├── static/                 # CSS, JS, Images
├── faces/                  # Face encodings storage
├── uploads/                # Uploaded images
└── logs/                   # Application logs
```

## 🚀 Cài Đặt

### Yêu Cầu Hệ Thống
- Python 3.10+
- CMake (để build dlib)
- Visual Studio Build Tools (Windows)

### Cài Đặt Thủ Công

1. **Clone repository**
   ```bash
   git clone <repository-url>
   cd diemdanh
   ```

2. **Tạo môi trường ảo**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Cài đặt dependencies**
   ```bash
   pip install -r requirement.txt
   ```

4. **Cấu hình biến môi trường**
   
   Tạo file `.env` với nội dung:
   ```env
   SECRET_KEY=your-secret-key-here
   
   # Thời gian làm việc
   WORK_START_TIME=08:00
   WORK_LATE_TIME=08:30
   WORK_END_TIME=17:30
   
   # Email configuration
   EMAIL_NAME=your-email@gmail.com
   EMAIL_PASSWORD=your-app-password
   
   # AI APIs (optional)
   TAVILY_API_KEY=your-tavily-key
   GROQ_API_KEY=your-groq-key
   
   # Telegram (optional)
   TELEGRAM_BOT_TOKEN=your-bot-token
   TELEGRAM_CHAT_ID=your-chat-id
   ```

5. **Chạy ứng dụng**
   ```bash
   python main.py
   ```

   Server sẽ chạy tại: `http://localhost:8080`

### Cài Đặt với Docker

```bash
# Build và chạy
docker-compose up --build

# Chạy ở background
docker-compose up -d
```

## 📖 Hướng Dẫn Sử Dụng

### Tạo Tài Khoản Admin
```bash
python check_acc/add_admin.py
```

### Thêm Nhân Viên
```bash
python check_acc/add_nv.py
```

### Đăng Ký Khuôn Mặt
1. Đăng nhập với quyền Admin
2. Vào **Quản lý nhân viên**
3. Chọn nhân viên → **Đăng ký khuôn mặt**
4. Chụp ảnh khuôn mặt (đảm bảo chỉ 1 người trong khung hình)

### Check-in/Check-out
1. Truy cập trang chủ `/`
2. Cho phép truy cập camera
3. Hệ thống sẽ tự động nhận diện và ghi nhận điểm danh

## 🔧 API Endpoints

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/` | Trang điểm danh công khai |
| POST | `/attendance/check` | API check-in/check-out |
| GET | `/admin/dashboard` | Dashboard admin |
| POST | `/admin/employees/add` | Thêm nhân viên |
| GET | `/employee/dashboard` | Dashboard nhân viên |
| POST | `/auth/login` | Đăng nhập |
| GET | `/auth/logout` | Đăng xuất |

## 🛠️ Công Nghệ Sử Dụng

| Công nghệ | Phiên bản | Mục đích |
|-----------|-----------|----------|
| Flask | 2.3.3 | Web framework |
| Flask-SQLAlchemy | 3.1.1 | ORM |
| Flask-Login | 0.6.3 | Authentication |
| face_recognition | 1.3.0 | Nhận diện khuôn mặt |
| OpenCV | 4.8.1 | Xử lý ảnh |
| dlib | 19.24.2 | Machine learning |
| LangChain | - | AI/LLM integration |
| ChromaDB | - | Vector database |

## ⚙️ Cấu Hình

### Thời Gian Làm Việc
Chỉnh sửa trong file `.env`:
- `WORK_START_TIME`: Giờ bắt đầu làm việc
- `WORK_LATE_TIME`: Giờ tính đi muộn
- `WORK_END_TIME`: Giờ kết thúc làm việc

### Database
- Mặc định sử dụng SQLite (`database.db`)
- Có thể chuyển sang PostgreSQL/MySQL bằng cách thay đổi `SQLALCHEMY_DATABASE_URI`

## 🐛 Xử Lý Lỗi Thường Gặp

### Lỗi cài đặt face_recognition
```bash
# Windows - cài CMake trước
pip install cmake
pip install dlib
pip install face_recognition
```

### Lỗi không tìm thấy khuôn mặt
- Đảm bảo đủ ánh sáng
- Đảm bảo chỉ có 1 người trong khung hình
- Kiểm tra camera hoạt động bình thường

## 📝 License

MIT License - Xem file [LICENSE](LICENSE) để biết thêm chi tiết.

## 👥 Đóng Góp

Mọi đóng góp đều được chào đón! Vui lòng:
1. Fork repository
2. Tạo branch mới (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Tạo Pull Request

## 📧 Liên Hệ

Nếu có câu hỏi hoặc góp ý, vui lòng tạo issue trên GitHub.

---

⭐ Nếu thấy hữu ích, hãy cho project một star nhé!
