"""
微信公众号/小程序 语音助手 API
支持微信语音消息处理、文字对话、语音回复

接口设计：
1. 接收微信语音消息 (AMR/SILK 格式)
2. 语音识别 + AI 回答
3. 返回文字或语音回复
"""

import os
import io
import time
import hashlib
import tempfile
import subprocess
import logging
import xml.etree.ElementTree as ET
from flask import Blueprint, request, jsonify, Response, send_file

logger = logging.getLogger(__name__)

# 创建蓝图
wechat_api = Blueprint('wechat_api', __name__, url_prefix='/wechat')

# 导入共用模块
from api_mcu import (
    ai_client, AI_MODEL, VOICE_MAP, TTS_FOLDER,
    speech_to_text_from_wav, convert_to_wav_16k
)

# 微信配置 (请修改为你的配置)
WECHAT_TOKEN = "your_wechat_token"  # 微信公众号 Token
WECHAT_APPID = "your_appid"
WECHAT_APPSECRET = "your_appsecret"


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


@wechat_api.route('/callback', methods=['GET', 'POST'])
def wechat_callback():
    """
    微信公众号回调接口
    
    GET: 验证服务器配置
    POST: 接收消息
    """
    if request.method == 'GET':
        # 验证服务器配置
        signature = request.args.get('signature', '')
        timestamp = request.args.get('timestamp', '')
        nonce = request.args.get('nonce', '')
        echostr = request.args.get('echostr', '')
        
        if verify_wechat_signature(signature, timestamp, nonce):
            return echostr
        return 'Invalid signature', 403
    
    # POST: 处理消息
    try:
        xml_data = request.data.decode('utf-8')
        root = ET.fromstring(xml_data)
        
        msg_type = root.find('MsgType').text
        from_user = root.find('FromUserName').text
        to_user = root.find('ToUserName').text
        
        if msg_type == 'text':
            # 文字消息 -> AI 回答
            content = root.find('Content').text
            
            response = ai_client.chat.completions.create(
                model=AI_MODEL,
                messages=[
                    {'role': 'system', 'content': '你是一个有帮助的助手，请简洁回答，不超过500字。'},
                    {'role': 'user', 'content': content}
                ],
                stream=False
            )
            answer = response.choices[0].message.content
            
            return make_text_reply(from_user, to_user, answer)
        
        elif msg_type == 'voice':
            # 语音消息
            # 注意：需要在公众号后台开启"接收语音识别结果"
            recognition = root.find('Recognition')
            if recognition is not None:
                # 微信已识别的文字
                content = recognition.text
            else:
                # 需要自己识别 (需要下载语音文件)
                content = "收到语音消息，请开启语音识别功能"
            
            if content:
                response = ai_client.chat.completions.create(
                    model=AI_MODEL,
                    messages=[
                        {'role': 'system', 'content': '你是一个有帮助的助手，请简洁回答，不超过500字。'},
                        {'role': 'user', 'content': content}
                    ],
                    stream=False
                )
                answer = response.choices[0].message.content
                return make_text_reply(from_user, to_user, f"【语音识别】{content}\n\n【AI回答】{answer}")
            
            return make_text_reply(from_user, to_user, "语音识别失败")
        
        else:
            return make_text_reply(from_user, to_user, "暂不支持此类型消息")
    
    except Exception as e:
        logger.error(f"微信消息处理错误: {e}")
        return 'success'


@wechat_api.route('/chat', methods=['POST'])
def wechat_chat():
    """
    微信小程序/H5 文字对话接口
    
    请求:
        POST /wechat/chat
        Content-Type: application/json
        {"message": "你好", "session_id": "xxx"}
    
    返回:
        {"success": true, "reply": "AI回答", "session_id": "xxx"}
    """
    data = request.get_json() or {}
    message = data.get('message', '')
    session_id = data.get('session_id', '')
    
    if not message:
        return jsonify({"success": False, "error": "消息内容为空"}), 400
    
    try:
        response = ai_client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {'role': 'system', 'content': '你是一个有帮助的助手，请简洁回答。'},
                {'role': 'user', 'content': message}
            ],
            stream=False
        )
        answer = response.choices[0].message.content
        
        return jsonify({
            "success": True,
            "reply": answer,
            "session_id": session_id
        })
    except Exception as e:
        logger.error(f"微信对话错误: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@wechat_api.route('/voice', methods=['POST'])
def wechat_voice():
    """
    微信小程序语音对话接口
    
    请求:
        POST /wechat/voice
        Content-Type: application/octet-stream 或 multipart/form-data
        
        URL 参数:
            - format: 音频格式 (amr/wav/mp3/silk), 默认 amr
            - engine: 识别引擎 (vosk/tencent), 默认 tencent
    
    返回:
        {
            "success": true,
            "question": "识别的文字",
            "answer": "AI回答"
        }
    """
    audio_format = request.args.get('format', 'amr')
    engine = request.args.get('engine', 'tencent')
    
    try:
        # 获取音频数据
        if request.content_type and 'multipart/form-data' in request.content_type:
            if 'audio' not in request.files and 'file' not in request.files:
                return jsonify({"success": False, "error": "未找到音频文件"}), 400
            audio_file = request.files.get('audio') or request.files.get('file')
            audio_data = audio_file.read()
        else:
            audio_data = request.get_data()
        
        if not audio_data:
            return jsonify({"success": False, "error": "音频数据为空"}), 400
        
        # 转换音频格式
        if audio_format in ['amr', 'silk']:
            wav_data, error = convert_amr_to_wav(audio_data)
            if error:
                return jsonify({"success": False, "error": error}), 500
        else:
            wav_data, error = convert_to_wav_16k(audio_data)
            if error:
                return jsonify({"success": False, "error": error}), 500
        
        # 语音识别
        question, error = speech_to_text_from_wav(wav_data, engine=engine)
        if error:
            return jsonify({"success": False, "error": error}), 500
        
        if not question:
            return jsonify({"success": False, "error": "未识别到语音"}), 400
        
        # AI 回答
        response = ai_client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {'role': 'system', 'content': '你是一个有帮助的助手，请简洁回答，不超过200字。'},
                {'role': 'user', 'content': question}
            ],
            stream=False
        )
        answer = response.choices[0].message.content
        
        return jsonify({
            "success": True,
            "question": question,
            "answer": answer
        })
    
    except Exception as e:
        logger.error(f"微信语音对话错误: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@wechat_api.route('/stt', methods=['POST'])
def wechat_stt():
    """
    微信小程序语音转文字接口
    
    请求:
        POST /wechat/stt?format=amr&engine=tencent
        Content-Type: application/octet-stream
        [音频数据]
    
    返回:
        {"success": true, "text": "识别结果"}
    """
    audio_format = request.args.get('format', 'amr')
    engine = request.args.get('engine', 'tencent')
    
    try:
        audio_data = request.get_data()
        if not audio_data:
            return jsonify({"success": False, "error": "音频数据为空"}), 400
        
        # 转换格式
        if audio_format in ['amr', 'silk']:
            wav_data, error = convert_amr_to_wav(audio_data)
        else:
            wav_data, error = convert_to_wav_16k(audio_data)
        
        if error:
            return jsonify({"success": False, "error": error}), 500
        
        # 识别
        text, error = speech_to_text_from_wav(wav_data, engine=engine)
        if error:
            return jsonify({"success": False, "error": error}), 500
        
        return jsonify({"success": True, "text": text or ""})
    
    except Exception as e:
        logger.error(f"微信 STT 错误: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
