"""
微信公众号/小程序 API v1

注意: 此为 v1 API
"""

import os
import time
import hashlib
import tempfile
import subprocess
import xml.etree.ElementTree as ET
from flask import Blueprint, request, jsonify

from ...services.ai_service import get_ai_service
from ...services.asr_service import get_asr_service
from ...utils.logger import get_api_logger
from ...exceptions import ValidationError, ASRError, AIError, AudioError

logger = get_api_logger()

wechat_bp = Blueprint('wechat_v1', __name__, url_prefix='/wechat')

# 微信配置
WECHAT_TOKEN = os.environ.get("WECHAT_TOKEN", "your_wechat_token")

# 常量配置
MAX_AUDIO_SIZE = 10 * 1024 * 1024  # 10MB
MAX_MESSAGE_LENGTH = 2000  # 2000 字符


def verify_wechat_signature(signature: str, timestamp: str, nonce: str) -> bool:
    """验证微信签名"""
    tmp_list = sorted([WECHAT_TOKEN, timestamp, nonce])
    tmp_str = ''.join(tmp_list)
    tmp_str = hashlib.sha1(tmp_str.encode('utf-8')).hexdigest()
    return tmp_str == signature


def convert_amr_to_wav(amr_data: bytes) -> tuple:
    """将微信 AMR 音频转换为 WAV"""
    temp_amr = None
    temp_wav = None
    
    try:
        logger.debug(f"[AMR转换] 开始 | size={len(amr_data)}")
        
        temp_amr = tempfile.NamedTemporaryFile(suffix='.amr', delete=False)
        temp_amr.write(amr_data)
        temp_amr.close()
        
        temp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_wav.close()
        
        result = subprocess.run([
            "ffmpeg", "-i", temp_amr.name,
            "-ac", "1", "-ar", "16000", "-acodec", "pcm_s16le",
            "-y", temp_wav.name
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            with open(temp_wav.name, 'rb') as f:
                wav_data = f.read()
            logger.debug(f"[AMR转换] 成功 | wav_size={len(wav_data)}")
            return wav_data, None
        else:
            error_msg = f"AMR 转换失败: {result.stderr}"
            logger.error(f"[AMR转换] 失败 | error={error_msg}")
            return None, error_msg
            
    except subprocess.TimeoutExpired:
        error_msg = "AMR 转换超时"
        logger.error(f"[AMR转换] 超时")
        return None, error_msg
        
    except Exception as e:
        error_msg = f"AMR 转换异常: {str(e)}"
        logger.error(f"[AMR转换] 异常 | error={e}", exc_info=True)
        return None, error_msg
        
    finally:
        if temp_amr and os.path.exists(temp_amr.name):
            try:
                os.unlink(temp_amr.name)
            except:
                pass
        if temp_wav and os.path.exists(temp_wav.name):
            try:
                os.unlink(temp_wav.name)
            except:
                pass


def make_text_reply(from_user: str, to_user: str, content: str) -> str:
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
    start_time = time.time()
    
    try:
        # 解析 JSON
        try:
            data = request.get_json() or {}
        except Exception as e:
            logger.warning(f"[微信-文字] JSON 解析失败: {e}")
            raise ValidationError("请求格式错误，需要 JSON 格式")
        
        message = data.get('message', '')
        session_id = data.get('session_id', 'default')
        
        # 验证消息
        if not message or not message.strip():
            raise ValidationError("消息内容为空")
        
        message = message.strip()
        if len(message) > MAX_MESSAGE_LENGTH:
            raise ValidationError(f"消息过长，最大支持 {MAX_MESSAGE_LENGTH} 字符")
        
        logger.info(f"[微信-文字] 开始处理 | session={session_id} | message_length={len(message)}")
        
        # AI 问答
        ai_service = get_ai_service()
        try:
            answer = ai_service.ask(message, session_id=session_id, short=True)
        except AIError as e:
            logger.error(f"[微信-文字] AI 失败，返回兜底回复 | error={e}")
            answer = "AI 服务暂时不可用，请稍后再试。"
        
        duration = (time.time() - start_time) * 1000
        logger.info(f"[微信-文字] 处理完成 | answer_length={len(answer)} | duration={duration:.2f}ms")
        
        return jsonify({
            "success": True,
            "reply": answer,
            "session_id": session_id
        })
        
    except ValidationError as e:
        duration = (time.time() - start_time) * 1000
        logger.warning(f"[微信-文字] 验证失败 | error={e} | duration={duration:.2f}ms")
        raise
        
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        logger.error(f"[微信-文字] 未知错误 | error={e} | duration={duration:.2f}ms", exc_info=True)
        raise AIError(f"对话失败: {str(e)}")


@wechat_bp.route('/voice', methods=['POST'])
def wechat_voice():
    """微信小程序语音对话接口"""
    start_time = time.time()
    
    try:
        audio_format = request.args.get('format', 'amr')
        engine = request.args.get('engine', 'tencent')
        
        # 获取音频
        if request.content_type and 'multipart/form-data' in request.content_type:
            audio_file = request.files.get('audio') or request.files.get('file')
            if not audio_file:
                raise ValidationError("未找到音频文件")
            audio_data = audio_file.read()
        else:
            audio_data = request.get_data()
        
        # 验证音频
        if not audio_data:
            raise ValidationError("音频数据为空")
        
        if len(audio_data) > MAX_AUDIO_SIZE:
            raise ValidationError(f"音频文件过大，最大支持 {MAX_AUDIO_SIZE // 1024 // 1024}MB")
        
        logger.info(f"[微信-语音] 开始处理 | format={audio_format} | engine={engine} | size={len(audio_data)}")
        
        # 转换音频格式
        if audio_format in ['amr', 'silk']:
            wav_data, error = convert_amr_to_wav(audio_data)
            if error:
                raise AudioError(error)
        elif audio_data.startswith(b'RIFF'):
            wav_data = audio_data
        else:
            asr_service = get_asr_service()
            wav_data = asr_service.convert_to_wav(audio_data)
        
        # 语音识别
        asr_service = get_asr_service()
        question = asr_service.recognize(wav_data, engine=engine)
        
        if not question or not question.strip():
            raise ASRError("未识别到语音内容")
        
        logger.info(f"[微信-语音] ASR 完成 | question={question[:50]}...")
        
        # AI 回答
        ai_service = get_ai_service()
        answer = ai_service.ask(question, short=True)
        
        duration = (time.time() - start_time) * 1000
        logger.info(f"[微信-语音] 处理完成 | duration={duration:.2f}ms")
        
        return jsonify({
            "success": True,
            "question": question,
            "answer": answer
        })
        
    except ValidationError as e:
        duration = (time.time() - start_time) * 1000
        logger.warning(f"[微信-语音] 验证失败 | error={e} | duration={duration:.2f}ms")
        return jsonify({"success": False, "error": str(e)}), 400
        
    except (ASRError, AudioError) as e:
        duration = (time.time() - start_time) * 1000
        logger.warning(f"[微信-语音] 音频处理失败 | error={e} | duration={duration:.2f}ms")
        return jsonify({"success": False, "error": str(e)}), 400
        
    except AIError as e:
        duration = (time.time() - start_time) * 1000
        logger.error(f"[微信-语音] AI 失败 | error={e} | duration={duration:.2f}ms")
        return jsonify({"success": False, "error": str(e)}), 500
        
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        logger.error(f"[微信-语音] 未知错误 | error={e} | duration={duration:.2f}ms", exc_info=True)
        return jsonify({"success": False, "error": "服务器内部错误"}), 500


@wechat_bp.route('/stt', methods=['POST'])
def wechat_stt():
    """微信小程序语音转文字接口"""
    audio_format = request.args.get('format', 'amr')
    engine = request.args.get('engine', 'tencent')

    try:
        audio_data = request.get_data()
        if not audio_data:
            raise ValidationError("音频数据为空")

        # 转换格式
        if audio_format in ['amr', 'silk']:
            wav_data, error = convert_amr_to_wav(audio_data)
            if error:
                raise AudioError(error)
        elif audio_data.startswith(b'RIFF'):
            wav_data = audio_data
        else:
            asr_service = get_asr_service()
            wav_data = asr_service.convert_to_wav(audio_data)

        # 识别
        asr_service = get_asr_service()
        text = asr_service.recognize(wav_data, engine=engine)

        return jsonify({"success": True, "text": text or ""})

    except ValidationError as e:
        logger.warning(f"[微信-STT] 验证失败 | error={e}")
        return jsonify({"success": True, "text": ""}), 200
    except (ASRError, AudioError) as e:
        logger.warning(f"[微信-STT] 音频处理失败，返回空文本 | error={e}")
        return jsonify({"success": True, "text": ""}), 200
    except Exception as e:
        logger.error(f"[微信-STT] 未知错误，返回空文本 | error={e}", exc_info=True)
        return jsonify({"success": True, "text": ""}), 200
