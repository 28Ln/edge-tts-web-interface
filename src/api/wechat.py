"""
微信公众号/小程序 API
"""

import os
import time
import hashlib
import tempfile
import subprocess
import xml.etree.ElementTree as ET
from flask import Blueprint, request, jsonify

from ..services.ai_service import get_ai_service
from ..services.asr_service import get_asr_service
from ..utils.logger import get_api_logger
from ..exceptions import ValidationError

logger = get_api_logger()

wechat_bp = Blueprint('wechat', __name__, url_prefix='/wechat')

# 微信配置
WECHAT_TOKEN = os.environ.get("WECHAT_TOKEN", "your_wechat_token")


def verify_wechat_signature(signature, timestamp, nonce):
    """验证微信签名"""
    tmp_list = sorted([WECHAT_TOKEN, timestamp, nonce])
    tmp_str = ''.join(tmp_list)
    tmp_str = hashlib.sha1(tmp_str.encode('utf-8')).hexdigest()
    return tmp_str == signature


def convert_amr_to_wav(amr_data):
    """将微信 AMR 音频转换为 WAV"""
    temp_amr = None
    temp_wav = None
    try:
        temp_amr = tempfile.NamedTemporaryFile(suffix='.amr', delete=False)
        temp_amr.write(amr_data)
        temp_amr.close()
        
        temp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_wav.close()
        
        result = subprocess.run([
            "ffmpeg", "-i", temp_amr.name,
            "-ac", "1", "-ar", "16000", "-acodec", "pcm_s16le",
            "-y", temp_wav.name
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            with open(temp_wav.name, 'rb') as f:
                return f.read(), None
        else:
            return None, f"AMR 转换失败: {result.stderr}"
    except Exception as e:
        return None, str(e)
    finally:
        if temp_amr and os.path.exists(temp_amr.name):
            os.unlink(temp_amr.name)
        if temp_wav and os.path.exists(temp_wav.name):
            os.unlink(temp_wav.name)


def make_text_reply(from_user, to_user, content):
    """生成微信文本回复 XML"""
    return f"""<xml>
<ToUserName><![CDATA[{from_user}]]></ToUserName>
<FromUserName><![CDATA[{to_user}]]></FromUserName>
<CreateTime>{int(time.time())}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[{content}]]></Content>
</xml>"""


@wechat_bp.route('/callback', methods=['GET', 'POST'])
def wechat_callback():
    """微信公众号回调接口"""
    if request.method == 'GET':
        signature = request.args.get('signature', '')
        timestamp = request.args.get('timestamp', '')
        nonce = request.args.get('nonce', '')
        echostr = request.args.get('echostr', '')
        
        if verify_wechat_signature(signature, timestamp, nonce):
            return echostr
        return 'Invalid signature', 403
    
    try:
        xml_data = request.data.decode('utf-8')
        root = ET.fromstring(xml_data)
        
        msg_type = root.find('MsgType').text
        from_user = root.find('FromUserName').text
        to_user = root.find('ToUserName').text
        
        if msg_type == 'text':
            content = root.find('Content').text
            ai_service = get_ai_service()
            answer = ai_service.ask(content, session_id=from_user, short=True)
            return make_text_reply(from_user, to_user, answer)
        
        elif msg_type == 'voice':
            recognition = root.find('Recognition')
            if recognition is not None:
                content = recognition.text
                ai_service = get_ai_service()
                answer = ai_service.ask(content, session_id=from_user, short=True)
                return make_text_reply(from_user, to_user, f"【语音】{content}\n\n【回答】{answer}")
            return make_text_reply(from_user, to_user, "语音识别失败")
        
        else:
            return make_text_reply(from_user, to_user, "暂不支持此类型消息")
    
    except Exception as e:
        logger.error(f"微信消息处理错误: {e}")
        return 'success'


@wechat_bp.route('/chat', methods=['POST'])
def wechat_chat():
    """微信小程序文字对话接口"""
    data = request.get_json() or {}
    message = data.get('message', '')
    session_id = data.get('session_id', 'default')
    
    if not message:
        raise ValidationError("消息内容为空")
    
    logger.info(f"[微信-文字] session={session_id} | message={message[:50]}...")
    
    ai_service = get_ai_service()
    answer = ai_service.ask(message, session_id=session_id, short=True)
    
    return jsonify({
        "success": True,
        "reply": answer,
        "session_id": session_id
    })


@wechat_bp.route('/voice', methods=['POST'])
def wechat_voice():
    """微信小程序语音对话接口"""
    audio_format = request.args.get('format', 'amr')
    engine = request.args.get('engine', 'tencent')
    
    if request.content_type and 'multipart/form-data' in request.content_type:
        audio_file = request.files.get('audio') or request.files.get('file')
        if not audio_file:
            raise ValidationError("未找到音频文件")
        audio_data = audio_file.read()
    else:
        audio_data = request.get_data()
    
    if not audio_data:
        raise ValidationError("音频数据为空")
    
    # 转换音频格式
    if audio_format in ['amr', 'silk']:
        wav_data, error = convert_amr_to_wav(audio_data)
        if error:
            return jsonify({"success": False, "error": error}), 500
    else:
        asr_service = get_asr_service()
        wav_data = asr_service.convert_to_wav(audio_data)
    
    # 语音识别
    asr_service = get_asr_service()
    question = asr_service.recognize(wav_data, engine=engine)
    
    if not question:
        return jsonify({"success": False, "error": "未识别到语音"}), 400
    
    # AI 回答
    ai_service = get_ai_service()
    answer = ai_service.ask(question, short=True)
    
    return jsonify({
        "success": True,
        "question": question,
        "answer": answer
    })


@wechat_bp.route('/stt', methods=['POST'])
def wechat_stt():
    """微信小程序语音转文字接口"""
    audio_format = request.args.get('format', 'amr')
    engine = request.args.get('engine', 'tencent')
    
    audio_data = request.get_data()
    if not audio_data:
        raise ValidationError("音频数据为空")
    
    # 转换格式
    if audio_format in ['amr', 'silk']:
        wav_data, error = convert_amr_to_wav(audio_data)
        if error:
            return jsonify({"success": False, "error": error}), 500
    else:
        asr_service = get_asr_service()
        wav_data = asr_service.convert_to_wav(audio_data)
    
    # 识别
    asr_service = get_asr_service()
    text = asr_service.recognize(wav_data, engine=engine)
    
    return jsonify({"success": True, "text": text or ""})
