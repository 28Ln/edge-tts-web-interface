# 腾讯云一句话语音识别客户端
import base64
import hashlib
import hmac
import json
import time
import requests
from datetime import datetime

from config import TENCENT_SECRET_ID, TENCENT_SECRET_KEY, TENCENT_APPID


class TencentASR:
    """腾讯云一句话语音识别"""
    
    def __init__(self):
        self.secret_id = TENCENT_SECRET_ID
        self.secret_key = TENCENT_SECRET_KEY
        self.appid = TENCENT_APPID
        self.host = "asr.tencentcloudapi.com"
        self.service = "asr"
        self.version = "2019-06-14"
        self.action = "SentenceRecognition"
    
    def _get_signature(self, params, timestamp, date):
        """生成签名"""
        # 1. 拼接规范请求串
        http_request_method = "POST"
        canonical_uri = "/"
        canonical_querystring = ""
        canonical_headers = f"content-type:application/json; charset=utf-8\nhost:{self.host}\nx-tc-action:{self.action.lower()}\n"
        signed_headers = "content-type;host;x-tc-action"
        payload = json.dumps(params)
        hashed_payload = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        canonical_request = f"{http_request_method}\n{canonical_uri}\n{canonical_querystring}\n{canonical_headers}\n{signed_headers}\n{hashed_payload}"
        
        # 2. 拼接待签名字符串
        algorithm = "TC3-HMAC-SHA256"
        credential_scope = f"{date}/{self.service}/tc3_request"
        hashed_canonical_request = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
        string_to_sign = f"{algorithm}\n{timestamp}\n{credential_scope}\n{hashed_canonical_request}"
        
        # 3. 计算签名
        def sign(key, msg):
            return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()
        
        secret_date = sign(("TC3" + self.secret_key).encode("utf-8"), date)
        secret_service = sign(secret_date, self.service)
        secret_signing = sign(secret_service, "tc3_request")
        signature = hmac.new(secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
        
        return signature, credential_scope, signed_headers, algorithm

    def recognize(self, audio_path: str, voice_format: str = "wav", engine: str = "16k_zh_en") -> dict:
        """
        识别音频文件
        
        Args:
            audio_path: 音频文件路径
            voice_format: 音频格式 (wav, mp3, m4a, flac, ogg, amr 等)
            engine: 引擎类型
                - 16k_zh: 中文普通话
                - 16k_zh_en: 中英文混合（默认）
                - 16k_en: 纯英文
                - 16k_zh_dialect: 中文方言
        
        Returns:
            dict: {"success": bool, "text": str, "error": str}
        """
        try:
            # 读取音频文件并 base64 编码
            with open(audio_path, "rb") as f:
                audio_data = base64.b64encode(f.read()).decode("utf-8")
            
            # 构建请求参数
            params = {
                "ProjectId": 0,
                "SubServiceType": 2,  # 一句话识别
                "EngSerViceType": engine,  # 引擎类型
                "SourceType": 1,  # 语音数据来源为语音 base64
                "VoiceFormat": voice_format,
                "Data": audio_data,
                "DataLen": len(audio_data),
            }
            
            # 生成时间戳
            timestamp = int(time.time())
            date = datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d")
            
            # 生成签名
            signature, credential_scope, signed_headers, algorithm = self._get_signature(params, timestamp, date)
            
            # 构建请求头
            authorization = (
                f"{algorithm} "
                f"Credential={self.secret_id}/{credential_scope}, "
                f"SignedHeaders={signed_headers}, "
                f"Signature={signature}"
            )
            
            headers = {
                "Authorization": authorization,
                "Content-Type": "application/json; charset=utf-8",
                "Host": self.host,
                "X-TC-Action": self.action,
                "X-TC-Timestamp": str(timestamp),
                "X-TC-Version": self.version,
            }
            
            # 发送请求
            url = f"https://{self.host}"
            response = requests.post(url, headers=headers, json=params, timeout=30)
            result = response.json()
            
            # 解析结果
            if "Response" in result:
                if "Error" in result["Response"]:
                    return {
                        "success": False,
                        "text": "",
                        "error": result["Response"]["Error"]["Message"]
                    }
                return {
                    "success": True,
                    "text": result["Response"].get("Result", ""),
                    "error": ""
                }
            
            return {"success": False, "text": "", "error": "未知响应格式"}
            
        except FileNotFoundError:
            return {"success": False, "text": "", "error": f"音频文件不存在: {audio_path}"}
        except Exception as e:
            return {"success": False, "text": "", "error": str(e)}

    def recognize_url(self, audio_url: str, voice_format: str = "wav", engine: str = "16k_zh_en") -> dict:
        """
        识别网络音频文件
        
        Args:
            audio_url: 音频文件 URL
            voice_format: 音频格式
            engine: 引擎类型 (16k_zh_en=中英混合, 16k_zh=中文, 16k_en=英文)
        
        Returns:
            dict: {"success": bool, "text": str, "error": str}
        """
        try:
            params = {
                "ProjectId": 0,
                "SubServiceType": 2,
                "EngSerViceType": engine,
                "SourceType": 0,  # 语音 URL
                "VoiceFormat": voice_format,
                "Url": audio_url,
            }
            
            timestamp = int(time.time())
            date = datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d")
            signature, credential_scope, signed_headers, algorithm = self._get_signature(params, timestamp, date)
            
            authorization = (
                f"{algorithm} "
                f"Credential={self.secret_id}/{credential_scope}, "
                f"SignedHeaders={signed_headers}, "
                f"Signature={signature}"
            )
            
            headers = {
                "Authorization": authorization,
                "Content-Type": "application/json; charset=utf-8",
                "Host": self.host,
                "X-TC-Action": self.action,
                "X-TC-Timestamp": str(timestamp),
                "X-TC-Version": self.version,
            }
            
            url = f"https://{self.host}"
            response = requests.post(url, headers=headers, json=params, timeout=30)
            result = response.json()
            
            if "Response" in result:
                if "Error" in result["Response"]:
                    return {
                        "success": False,
                        "text": "",
                        "error": result["Response"]["Error"]["Message"]
                    }
                return {
                    "success": True,
                    "text": result["Response"].get("Result", ""),
                    "error": ""
                }
            
            return {"success": False, "text": "", "error": "未知响应格式"}
            
        except Exception as e:
            return {"success": False, "text": "", "error": str(e)}
