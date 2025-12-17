"""
MCU API 路由
精简版 API，适用于嵌入式设备
"""

from flask import Blueprint, request, jsonify, Response, send_file

from ..services.ai_service import get_ai_service
from ..services.asr_service import get_asr_service
from ..services.tts_service import get_tts_service
from ..utils.logger import get_api_logger
from ..exceptions import ValidationError, ASRError

logger = get_api_logger()

mcu_bp = Blueprint('mcu', __name__, url_prefix='/mcu')


# ==================== 基础接口 ====================

@mcu_bp.route('/ping', methods=['GET'])
def ping():
    """连接测试"""
    return "pong", 200


@mcu_bp.route('/status', methods=['GET'])
def status():
    """获取服务状态"""
    asr_service = get_asr_service()
    
    return jsonify({
        "success": True,
        "asr_engines": asr_service.get_available_engines(),
        "ai": True,
        "tts": True,
    })


# ==================== 语音识别 ====================

@mcu_bp.route('/stt', methods=['POST'])
def stt():
    """语音转文字"""
    engine = request.args.get('engine', 'tencent')
    audio_format = request.args.get('format', 'wav')
    
    # 获取音频数据
    if request.content_type and 'multipart/form-data' in request.content_type:
        if 'audio' not in request.files:
            raise ValidationError("未找到音频文件")
        audio_data = request.files['audio'].read()
    else:
        audio_data = request.get_data()
    
    if not audio_data:
        raise ValidationError("音频数据为空")
    
    logger.info(f"[STT] 请求 | engine={engine} | format={audio_format} | size={len(audio_data)}")
    
    # 识别
    asr_service = get_asr_service()
    text = asr_service.recognize(audio_data, engine=engine, audio_format=audio_format)
    
    return text, 200, {'Content-Type': 'text/plain; charset=utf-8'}


# ==================== AI 问答 ====================

@mcu_bp.route('/ask', methods=['POST'])
def ask():
    """AI 问答（非流式）"""
    session_id = request.args.get('session', 'default')
    
    if request.content_type and 'application/json' in request.content_type:
        data = request.get_json() or {}
        question = data.get('question', '')
        session_id = data.get('session', session_id)
    else:
        question = request.get_data(as_text=True)
    
    if not question:
        raise ValidationError("问题内容为空")
    
    logger.info(f"[ASK] 请求 | session={session_id} | question={question[:50]}...")
    
    ai_service = get_ai_service()
    answer = ai_service.ask(question, session_id=session_id)
    
    return answer, 200, {'Content-Type': 'text/plain; charset=utf-8'}


@mcu_bp.route('/ask_stream', methods=['POST'])
def ask_stream():
    """AI 流式问答"""
    session_id = request.args.get('session', 'default')
    
    if request.content_type and 'application/json' in request.content_type:
        data = request.get_json() or {}
        question = data.get('question', '')
        session_id = data.get('session', session_id)
    else:
        question = request.get_data(as_text=True)
    
    if not question:
        raise ValidationError("问题内容为空")
    
    logger.info(f"[ASK_STREAM] 请求 | session={session_id} | question={question[:50]}...")
    
    def generate():
        ai_service = get_ai_service()
        try:
            for chunk in ai_service.ask_stream(question, session_id=session_id):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"[ASK_STREAM] 错误: {e}")
            yield f"data: [ERROR] {str(e)}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')


# ==================== 语音合成 ====================

@mcu_bp.route('/tts', methods=['GET', 'POST'])
def tts():
    """文字转语音"""
    if request.method == 'GET':
        text = request.args.get('text', '')
        voice = request.args.get('voice', 'xiaoxiao')
        output_format = request.args.get('format', 'wav')
    else:
        data = request.get_json() or {}
        text = data.get('text', '')
        voice = data.get('voice', 'xiaoxiao')
        output_format = data.get('format', 'wav')
    
    if not text:
        raise ValidationError("文字内容为空")
    
    logger.info(f"[TTS] 请求 | text={text[:30]}... | voice={voice}")
    
    tts_service = get_tts_service()
    file_path = tts_service.synthesize(text, voice=voice, output_format=output_format)
    
    mimetype = 'audio/wav' if output_format == 'wav' else 'audio/mpeg'
    return send_file(file_path, mimetype=mimetype)


# ==================== 语音对话 ====================

@mcu_bp.route('/voice_chat', methods=['POST'])
def voice_chat():
    """一站式语音对话"""
    engine = request.args.get('engine', 'tencent')
    audio_format = request.args.get('format', 'wav')
    output_type = request.args.get('out', 'text')  # text 或 audio
    session_id = request.args.get('session', 'default')
    
    # 获取音频
    if request.content_type and 'multipart/form-data' in request.content_type:
        if 'audio' not in request.files:
            raise ValidationError("未找到音频文件")
        audio_data = request.files['audio'].read()
    else:
        audio_data = request.get_data()
    
    if not audio_data:
        raise ValidationError("音频数据为空")
    
    logger.info(f"[VOICE_CHAT] 请求 | engine={engine} | out={output_type}")
    
    # 1. 语音识别
    asr_service = get_asr_service()
    question = asr_service.recognize(audio_data, engine=engine, audio_format=audio_format)
    
    if not question:
        raise ASRError("未识别到语音内容")
    
    # 2. AI 回答
    ai_service = get_ai_service()
    answer = ai_service.ask(question, session_id=session_id, short=True)
    
    # 3. 返回结果
    if output_type == 'text':
        return jsonify({
            "success": True,
            "question": question,
            "answer": answer,
        })
    else:
        # 生成语音
        tts_service = get_tts_service()
        file_path = tts_service.synthesize(answer, output_format='wav')
        return send_file(file_path, mimetype='audio/wav')
