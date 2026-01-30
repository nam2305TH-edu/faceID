import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'fallback-secret-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///database.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'uploads'
    FACES_FOLDER = 'faces'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  

class email:
    EMAIL_NAME = os.getenv("EMAIL_NAME")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
    
    
WORK_START_TIME = os.getenv('WORK_START_TIME')
WORK_LATE_TIME = os.getenv('WORK_LATE_TIME')
WORK_END_TIME = os.getenv('WORK_END_TIME')

os.makedirs('faces', exist_ok=True)
os.makedirs('uploads', exist_ok=True)
os.makedirs('logs', exist_ok=True)
os.makedirs('static', exist_ok=True)

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

