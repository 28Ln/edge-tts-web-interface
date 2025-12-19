"""
腾讯云一句话语音识别客户端
"""

import os
import base64
import hashlib
import hmac
import json
import time
import requests
from datetime import datetime

from ...config import get_config
from ...utils.logger import get_asr_logger

logger = get_asr_logger()


class TencentASR:
    """腾讯云一句话语音识别"""
    
    def __init__(self):
        # 直接从环境变量读取，避免配置缓存问题
        import os
        self.secret_id = os.environ.get("TENCENT_SECRET_ID", "")
        self.secret_key = os.environ.get("TENCENT_SECRET_KEY", "")
        self.appid = os.environ.get("TENCENT_APPID", "")
        self.host = "asr.tencentcloudapi.com"
        self.service = "asr"
        self.version = "2019-06-14"
        self.action = "SentenceRecognition"
        logger.info(f"[TencentASR] 初始化: secret_id={self.secret_id[:10] if self.secret_id else 'EMPTY'}..., appid={self.appid}")
    
    def is_available(self) -> bool:
        """检查是否可用"""
        available = bool(self.secret_id and self.secret_key and self.appid)
        print(f"[TencentASR] is_available: secret_id={bool(self.secret_id)}, secret_key={bool(self.secret_key)}, appid={bool(self.appid)} => {available}", flush=True)
        return available
    
    def _get_signature(self, params, timestamp, date):
        """生成签名"""
        http_request_method = "POST"
        canonical_uri = "/"
        canonical_querystring = ""
        canonical_headers = f"content-type:application/json; charset=utf-8\nhost:{self.host}\nx-tc-action:{self.action.lower()}\n"
        signed_headers = "content-type;host;x-tc-action"
        payload = json.dumps(params)
        hashed_payload = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        canonical_request = f"{http_request_method}\n{canonical_uri}\n{canonical_querystring}\n{canonical_headers}\n{signed_headers}\n{hashed_payload}"
        
        algorithm = "TC3-HMAC-SHA256"
        credential_scope = f"{date}/{self.service}/tc3_request"
        hashed_canonical_request = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
        string_to_sign = f"{algorithm}\n{timestamp}\n{credential_scope}\n{hashed_canonical_request}"
        
        def sign(key, msg):
            return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()
        
        secret_date = sign(("TC3" + self.secret_key).encode("utf-8"), date)
        secret_service = sign(secret_date, self.service)
        secret_signing = sign(secret_service, "tc3_request")
        signature = hmac.new(secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
        
        return signature, credential_scope, signed_headers, algorithm

    def recognize(self, audio_path: str, voice_format: str = "wav", engine: str = "16k_zh") -> dict:
        """
        识别音频文件
        
        Args:
            audio_path: 音频文件路径
            voice_format: 音频格式 (wav, mp3, m4a, flac, ogg, amr 等)
            engine: 引擎类型 (16k_zh, 16k_zh_en, 16k_en)
        
        Returns:
            dict: {"success": bool, "text": str, "error": str}
        """
        if not self.is_available():
            return {"success": False, "text": "", "error": "腾讯云 ASR 未配置"}
        
        try:
            with open(audio_path, "rb") as f:
                audio_data = base64.b64encode(f.read()).decode("utf-8")
            
            params = {
                "ProjectId": 0,
                "SubServiceType": 2,
                "EngSerViceType": engine,
                "SourceType": 1,
                "VoiceFormat": voice_format,
                "Data": audio_data,
                "DataLen": len(audio_data),
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
                    error_msg = result["Response"]["Error"]["Message"]
                    logger.error(f"腾讯云 ASR 错误: {error_msg}")
                    return {"success": False, "text": "", "error": error_msg}
                text = result["Response"].get("Result", "")
                logger.info(f"腾讯云 ASR 识别成功: {text[:50]}...")
                return {"success": True, "text": text, "error": ""}
            
            return {"success": False, "text": "", "error": "未知响应格式"}
            
        except FileNotFoundError:
            return {"success": False, "text": "", "error": f"音频文件不存在: {audio_path}"}
        except Exception as e:
            logger.error(f"腾讯云 ASR 异常: {e}")
            return {"success": False, "text": "", "error": str(e)}
