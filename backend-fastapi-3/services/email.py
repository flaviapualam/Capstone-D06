# services/email.py
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from core.config import settings
from uuid import UUID
import asyncio
from datetime import datetime

async def send_anomaly_alert(
    farmer_email: str, 
    cow_id: UUID, 
    score: float, 
    avg_temp: float,
    time: datetime
):
    """
    Mengirim email peringatan anomali menggunakan background thread.
    """
    
    subject = f"🚨 ANOMALI KRITIS TERDETEKSI: Sapi {cow_id} ({avg_temp:.2f}°C)"
    body = f"""
    Halo Farmer,
    
    Sistem deteksi anomali telah mengidentifikasi perilaku makan yang sangat tidak biasa pada sapi Anda.
    
    DETAIL ANOMALI:
    - Sapi ID: {cow_id}
    - Waktu Kejadian: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}
    - Suhu Rata-rata Sesi: {avg_temp:.2f}°C
    - Skor Anomali (iForest): {score:.4f} (Semakin tinggi/dekat 0, semakin anomali)
    
    Mohon segera periksa kondisi sapi dan tingkat pakan di perangkat terkait.
    
    Terima kasih,
    Sistem Monitoring Sapi
    """
    
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = Header(subject, 'utf-8')
    msg['From'] = settings.EMAIL_SENDER
    msg['To'] = farmer_email

    # Membungkus pemanggilan SMTPLIB yang blocking ke dalam asyncio.to_thread
    await asyncio.to_thread(_send_mail_blocking, msg, farmer_email)
    print(f"(EMAIL ALERT) Dikirim ke {farmer_email} untuk Sapi {cow_id}.")

def _send_mail_blocking(msg: MIMEText, recipient_email: str):
    """Fungsi sinkron yang melakukan koneksi dan pengiriman SMTP."""
    try:
        # Menggunakan koneksi TLS standar
        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            server.starttls() 
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.sendmail(settings.EMAIL_SENDER, recipient_email, msg.as_string())
    except Exception as e:
        print(f"FAILED TO SEND EMAIL to {recipient_email}: {e}")

# Note: Anda perlu membuat crud_farmer.get_farmer_email(db, farmer_id) 
# di file services/crud_farmer.py untuk mendapatkan email tujuan.