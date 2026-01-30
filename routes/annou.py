import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sqlite3
import asyncio
from config import email

def check_email():
    if not email.EMAIL_NAME or not email.EMAIL_PASSWORD:
        print("Chưa nhập email hoặc mật khẩu")
        return False
    return True

def read_email_fromdb():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT email FROM user WHERE email IS NOT NULL and role='employee'")
    emails = [row[0] for row in cursor.fetchall()]
    conn.close()
    return emails

def send_email(to_email, subject, content):
    msg = MIMEMultipart()
    msg['From'] = email.EMAIL_NAME
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(content, 'plain', 'utf-8'))
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(email.EMAIL_NAME, email.EMAIL_PASSWORD)  
        server.sendmail(email.EMAIL_NAME, to_email, msg.as_string())
        server.quit()
        print(f"Đã gửi: {to_email}")
    except Exception as e:
        print(f"Lỗi gửi {to_email}: {e}")

def send_to_email(subject, content):
    emails = read_email_fromdb()                                                                       
    for email in emails:
        send_email(email, subject, content)

if __name__ == "__main__":
    subject = input("Nhập tiêu đề: ")
    content = input("Nhập nội dung: ")
    if check_email():
        send_to_email(subject, content)