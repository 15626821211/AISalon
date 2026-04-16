"""邮件发送服务。"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import Config

logger = logging.getLogger(__name__)


def send_email(to_list, subject, html_body):
    """发送 HTML 邮件给多个收件人。

    Args:
        to_list: 收件人邮箱列表
        subject: 邮件主题
        html_body: HTML 正文
    Returns:
        (success_count, fail_count)
    """
    if not to_list:
        return 0, 0

    smtp_host = Config.SMTP_HOST
    smtp_port = Config.SMTP_PORT
    smtp_user = Config.SMTP_USER
    smtp_password = Config.SMTP_PASSWORD
    smtp_from = Config.SMTP_FROM or smtp_user

    if not smtp_user or not smtp_password or smtp_host == 'smtp.example.com':
        logger.warning('SMTP 未配置，跳过邮件发送')
        return 0, len(to_list)

    success = 0
    fail = 0
    try:
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=15)
            server.starttls()
        server.login(smtp_user, smtp_password)

        for to_addr in to_list:
            try:
                msg = MIMEMultipart('alternative')
                msg['From'] = smtp_from
                msg['To'] = to_addr
                msg['Subject'] = subject
                msg.attach(MIMEText(html_body, 'html', 'utf-8'))
                server.sendmail(smtp_from, [to_addr], msg.as_string())
                success += 1
                logger.info(f'邮件已发送: {to_addr}')
            except Exception as e:
                fail += 1
                logger.error(f'邮件发送失败 {to_addr}: {e}')

        server.quit()
    except Exception as e:
        logger.error(f'SMTP 连接失败: {e}')
        fail = len(to_list)

    return success, fail


def build_event_notification_html(event_dict, action='invited'):
    """构建活动通知邮件 HTML。"""
    title = event_dict.get('title', '未命名活动')
    location = event_dict.get('location', '待定')
    description = event_dict.get('description', '')
    start_time = event_dict.get('start_time', '待定')
    creator = event_dict.get('creator_name', '未知')

    if action == 'invited':
        heading = f'您已被邀请参加活动：{title}'
    else:
        heading = f'活动通知：{title}'

    return f"""
    <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:600px;margin:0 auto;padding:24px;background:#ffffff;">
        <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:16px;padding:32px;">
            <h1 style="font-size:22px;margin:0 0 16px;color:#4f46e5;">{heading}</h1>
            <table style="width:100%;font-size:15px;color:#1e293b;">
                <tr><td style="padding:8px 0;color:#64748b;width:90px;">📅 时间</td><td style="padding:8px 0;color:#1e293b;">{start_time}</td></tr>
                <tr><td style="padding:8px 0;color:#64748b;">📍 地点</td><td style="padding:8px 0;color:#1e293b;">{location}</td></tr>
                <tr><td style="padding:8px 0;color:#64748b;">👤 发起人</td><td style="padding:8px 0;color:#1e293b;">{creator}</td></tr>
            </table>
            {'<div style="margin-top:16px;padding:14px;background:#eef2ff;border-radius:10px;font-size:14px;color:#334155;">' + description + '</div>' if description else ''}
            <p style="margin-top:20px;font-size:13px;color:#94a3b8;">此邮件由 AI 沙龙平台自动发送，请勿回复。</p>
        </div>
    </div>
    """
