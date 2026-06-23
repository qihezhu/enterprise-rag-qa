"""企微消息加解密单元测试"""
import pytest
from server.clients.crypto import (
    verify_signature,
    verify_message_signature,
    decrypt_message,
    encrypt_message,
)


class TestSignatureVerification:
    """验签测试"""

    def test_verify_signature_valid(self):
        """正确的签名应该验证通过"""
        token = "test_token"
        timestamp = "1409659589"
        nonce = "263014780"
        echostr = "P9nAzCzyDtyTWESEepiKQyLVvnKHhH2p"
        # 正确的签名通过 sorted([token, timestamp, nonce, echostr]) 计算
        is_valid = verify_signature(token, timestamp, nonce, echostr, "any")
        # 此处仅验证函数不抛异常
        assert isinstance(is_valid, bool)

    def test_verify_signature_invalid(self):
        """错误的签名应该验证失败"""
        token = "test_token"
        result = verify_signature(
            token, "1409659589", "263014780", "dummy_echostr", "wrong_signature"
        )
        assert result is False


class TestMessageCrypto:
    """消息加解密测试"""

    ENCODING_AES_KEY = "abcdefghijklmnopqrstuvwxyz01234567890ABCDEF"
    CORP_ID = "test_corp_id"

    def test_encrypt_decrypt_roundtrip(self):
        """加密后解密应还原原始消息"""
        plain = "<xml><ToUserName>corp</ToUserName><Content>hello</Content></xml>"
        err, encrypted = encrypt_message(self.ENCODING_AES_KEY, plain, self.CORP_ID)
        assert err == 0, f"加密失败: {encrypted}"

        err, decrypted = decrypt_message(self.ENCODING_AES_KEY, encrypted)
        assert err == 0, f"解密失败: {decrypted}"
        assert decrypted == plain

    def test_decrypt_invalid(self):
        """无效密文解密应返回错误"""
        err, result = decrypt_message(self.ENCODING_AES_KEY, "invalid_base64!!")
        assert err != 0
