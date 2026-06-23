"""
企微消息加解密模块
实现回调URL验签（SHA1）、AES消息解密、AES消息加密
"""
import hashlib
import struct
import base64
import random
import string
from Crypto.Cipher import AES


def verify_signature(token, timestamp, nonce, echostr, signature):
    """
    验证企微回调URL时的签名
    参数：
        token: 企微后台配置的Token
        timestamp: 时间戳
        nonce: 随机数
        echostr: 随机字符串
        signature: 企微发来的签名
    返回：
        (验证通过bool, 解密后的echostr or None)
    """
    sort_list = sorted([token, timestamp, nonce, echostr])
    sha1_str = hashlib.sha1("".join(sort_list).encode()).hexdigest()
    return sha1_str == signature


def verify_message_signature(token, timestamp, nonce, encrypted_msg, signature):
    """
    验证回调消息的签名
    参数：
        token: 企微后台配置的Token
        timestamp: 时间戳
        nonce: 随机数
        encrypted_msg: 加密的消息体
        signature: 企微发来的签名
    返回：
        验证通过返回True，否则False
    """
    sort_list = sorted([token, timestamp, nonce, encrypted_msg])
    sha1_str = hashlib.sha1("".join(sort_list).encode()).hexdigest()
    return sha1_str == signature


def decrypt_message(encoding_aes_key, encrypted_msg):
    """
    AES解密企微推送的消息
    参数：
        encoding_aes_key: 43位EncodingAESKey（需补一个"="后base64解码为32字节密钥）
        encrypted_msg: Base64编码的密文
    返回：
        (err_code, decrypted_xml_str)
        err_code: 0表示成功
    """
    try:
        aes_key = base64.b64decode(encoding_aes_key + "=")
        cipher = AES.new(aes_key, AES.MODE_CBC, iv=aes_key[:16])
        decrypted = cipher.decrypt(base64.b64decode(encrypted_msg))
        # PKCS#7 去除补位
        pad = decrypted[-1]
        decrypted = decrypted[:-pad]
        # 解析: 16字节随机数 + 4字节消息长度 + 消息内容 + CorpID
        content_len = struct.unpack(">I", decrypted[16:20])[0]
        xml_content = decrypted[20:20 + content_len].decode("utf-8")
        return 0, xml_content
    except Exception as e:
        return -1, str(e)


def encrypt_message(encoding_aes_key, plain_xml, corp_id):
    """
    AES加密回复消息
    参数：
        encoding_aes_key: 43位EncodingAESKey
        plain_xml: 明文的XML回复
        corp_id: 企业CorpID
    返回：
        (err_code, base64_encrypted_msg)
    """
    try:
        aes_key = base64.b64decode(encoding_aes_key + "=")
        # 生成16字节随机数
        random_bytes = "".join(
            random.choice(string.ascii_letters + string.digits)
            for _ in range(16)
        ).encode()
        msg_bytes = plain_xml.encode("utf-8")
        # 构造: random(16) + msg_len(4) + msg + corp_id
        packed = (
            random_bytes
            + struct.pack(">I", len(msg_bytes))
            + msg_bytes
            + corp_id.encode("utf-8")
        )
        # PKCS#7 补位
        pad = 32 - len(packed) % 32
        packed += bytes([pad] * pad)
        cipher = AES.new(aes_key, AES.MODE_CBC, iv=aes_key[:16])
        encrypted = cipher.encrypt(packed)
        return 0, base64.b64encode(encrypted).decode()
    except Exception as e:
        return -1, str(e)
