"""QualityFoundry - Encryption Service

凭证加密/解密服务
"""
from cryptography.fernet import Fernet
from pathlib import Path


class EncryptionService:
    """加密服务"""
    
    def __init__(self, key_file: str = ".encryption_key"):
        """
        初始化加密服务
        
        Args:
            key_file: 密钥文件路径
        """
        self.key_file = Path(key_file)
        self.key = self._load_or_create_key()
        self.cipher = Fernet(self.key)
    
    def _load_or_create_key(self) -> bytes:
        """
        加载或创建加密密钥
        
        Returns:
            加密密钥
        """
        if self.key_file.exists():
            # 加载现有密钥
            with open(self.key_file, "rb") as f:
                return f.read()
        else:
            # 生成新密钥
            key = Fernet.generate_key()
            with open(self.key_file, "wb") as f:
                f.write(key)
            return key
    
    def encrypt(self, plaintext: str) -> str:
        """
        加密文本
        
        Args:
            plaintext: 明文
            
        Returns:
            密文（Base64 编码）
        """
        if not plaintext:
            return ""
        
        encrypted = self.cipher.encrypt(plaintext.encode())
        return encrypted.decode()
    
    def decrypt(self, ciphertext: str) -> str:
        """
        解密文本
        
        Args:
            ciphertext: 密文（Base64 编码）
            
        Returns:
            明文
        """
        if not ciphertext:
            return ""
        
        try:
            decrypted = self.cipher.decrypt(ciphertext.encode())
            return decrypted.decode()
        except Exception as e:
            raise ValueError(f"解密失败: {e}")


# 全局实例
encryption_service = EncryptionService()
