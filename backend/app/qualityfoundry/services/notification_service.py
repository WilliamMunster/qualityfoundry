"""QualityFoundry - Notification Service

审核通知服务 - 支持 Webhook 和邮件通知
"""
from __future__ import annotations

import logging
import smtplib
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class NotificationConfig:
    """通知配置"""
    # Webhook 配置
    webhook_enabled: bool = False
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    
    # 邮件配置
    email_enabled: bool = False
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_use_tls: bool = True
    email_from: Optional[str] = None


class NotificationService:
    """通知服务"""
    
    def __init__(self, config: Optional[NotificationConfig] = None):
        self.config = config or NotificationConfig()
    
    async def send_approval_notification(
        self,
        event_type: str,
        entity_type: str,
        entity_id: str,
        status: str,
        reviewer: str,
        comment: Optional[str] = None,
        recipients: Optional[list[str]] = None
    ) -> dict[str, Any]:
        """
        发送审核通知
        
        Args:
            event_type: 事件类型（approval_created/approval_approved/approval_rejected）
            entity_type: 实体类型（scenario/testcase）
            entity_id: 实体 ID
            status: 审核状态
            reviewer: 审核人
            comment: 审核意见
            recipients: 邮件接收者列表
        
        Returns:
            通知结果
        """
        results = {
            "webhook": None,
            "email": None
        }
        
        payload = {
            "event": event_type,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "status": status,
            "reviewer": reviewer,
            "comment": comment
        }
        
        # 发送 Webhook 通知
        if self.config.webhook_enabled and self.config.webhook_url:
            results["webhook"] = await self._send_webhook(payload)
        
        # 发送邮件通知
        if self.config.email_enabled and recipients:
            subject = f"[QualityFoundry] 审核{self._status_text(status)}: {entity_type}"
            body = self._build_email_body(payload)
            results["email"] = await self._send_email(recipients, subject, body)
        
        return results
    
    async def _send_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        """发送 Webhook 通知"""
        try:
            headers = {
                "Content-Type": "application/json"
            }
            
            if self.config.webhook_secret:
                headers["X-Webhook-Secret"] = self.config.webhook_secret
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.config.webhook_url,
                    json=payload,
                    headers=headers,
                    timeout=10.0
                )
                
                return {
                    "success": response.status_code < 400,
                    "status_code": response.status_code,
                    "error": None
                }
        except Exception as e:
            logger.error(f"Webhook 发送失败: {e}")
            return {
                "success": False,
                "status_code": None,
                "error": str(e)
            }
    
    async def _send_email(
        self,
        recipients: list[str],
        subject: str,
        body: str
    ) -> dict[str, Any]:
        """发送邮件通知"""
        try:
            msg = MIMEMultipart()
            msg["From"] = self.config.email_from
            msg["To"] = ", ".join(recipients)
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "html", "utf-8"))
            
            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                if self.config.smtp_use_tls:
                    server.starttls()
                if self.config.smtp_user and self.config.smtp_password:
                    server.login(self.config.smtp_user, self.config.smtp_password)
                server.sendmail(self.config.email_from, recipients, msg.as_string())
            
            return {
                "success": True,
                "recipients": recipients,
                "error": None
            }
        except Exception as e:
            logger.error(f"邮件发送失败: {e}")
            return {
                "success": False,
                "recipients": recipients,
                "error": str(e)
            }
    
    def _status_text(self, status: str) -> str:
        """状态文本"""
        status_map = {
            "pending": "待审核",
            "approved": "已通过",
            "rejected": "已拒绝"
        }
        return status_map.get(status, status)
    
    def _build_email_body(self, payload: dict[str, Any]) -> str:
        """构建邮件正文"""
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>QualityFoundry 审核通知</h2>
            <table style="border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>事件</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{payload.get('event')}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>类型</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{payload.get('entity_type')}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>ID</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{payload.get('entity_id')}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>状态</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{self._status_text(payload.get('status', ''))}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>审核人</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{payload.get('reviewer')}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>意见</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{payload.get('comment') or '无'}</td>
                </tr>
            </table>
        </body>
        </html>
        """


# 全局通知服务实例（可通过环境变量配置）
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """获取通知服务实例"""
    global _notification_service
    if _notification_service is None:
        # 从环境变量加载配置（生产环境）
        import os
        config = NotificationConfig(
            webhook_enabled=os.getenv("NOTIFICATION_WEBHOOK_ENABLED", "").lower() == "true",
            webhook_url=os.getenv("NOTIFICATION_WEBHOOK_URL"),
            webhook_secret=os.getenv("NOTIFICATION_WEBHOOK_SECRET"),
            email_enabled=os.getenv("NOTIFICATION_EMAIL_ENABLED", "").lower() == "true",
            smtp_host=os.getenv("NOTIFICATION_SMTP_HOST"),
            smtp_port=int(os.getenv("NOTIFICATION_SMTP_PORT", "587")),
            smtp_user=os.getenv("NOTIFICATION_SMTP_USER"),
            smtp_password=os.getenv("NOTIFICATION_SMTP_PASSWORD"),
            smtp_use_tls=os.getenv("NOTIFICATION_SMTP_TLS", "true").lower() == "true",
            email_from=os.getenv("NOTIFICATION_EMAIL_FROM"),
        )
        _notification_service = NotificationService(config)
    return _notification_service
