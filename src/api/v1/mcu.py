"""
MCU API v1 路由
精简版 API，适用于嵌入式设备

注意: 此为 v1 API，建议迁移到 /v2/mcu/* (带认证和计费)
"""

import time
from flask import Blueprint, request, jsonify, Response, send_file

from ...services.ai_service import get_ai_service
from ...services.asr_service import get_asr_service
from ...services.tts_service import get_tts_service
from ...utils.logger import get_api_logger
from ...exceptions import ValidationError, ASRError, AIError, TTSError, AudioError

logger = get_api_logger()

mcu_bp = Blueprint('mcu_v1', __name__, url_prefix='/mcu')

# 常量配置
MAX_AUDIO_SIZE = 10 * 1024 * 1024  # 10MB
MAX_TEXT_LENGTH = 5000  # 5000 字符
MAX_QUESTION_LENGTH = 1000  # 1000 字符


# ==================== 基础接口 ====================

@mcu_bp.route('/ping', methods=['GET'])
def ping():
    """连接测试"""
    return "pong", 200


@mcu_bp.route('/status', methods=['GET'])
def status():
    """获取服务状态"""
    print("[MCU] status endpoint called", flush=True)
    asr_service = get_asr_service()
    engines = asr_service.get_available_engines()
    print(f"[MCU] asr_engines: {engines}", flush=True)
    
    return jsonify({
        "success": True,
        "asr_engines": engines,
        "ai": True,
        "tts": True,
    })


# ==================== 语音识别 ====================

@mcu_bp.route('/stt', methods=['POST'])
def stt():
    """语音转文字"""
    start_time = time.time()
    
    try:
        engine = request.args.get('engine', 'tencent')
        audio_format = request.args.get('format', 'wav')
        
        # 获取音频数据
        if request.content_type and 'multipart/form-data' in request.content_type:
            if 'audio' not in request.files:
                raise ValidationError("未找到音频文件")
            audio_data = request.files['audio'].read()
        else:
            audio_data = request.get_data()
        
        # 验证音频数据
        if not audio_data:
            raise ValidationError("音频数据为空")
        
        if len(audio_data) > MAX_AUDIO_SIZE:
            raise ValidationError(f"音频文件过大，最大支持 {MAX_AUDIO_SIZE // 1024 // 1024}MB")
        
        logger.info(f"[STT] 开始处理 | engine={engine} | format={audio_format} | size={len(audio_data)}")
        
        # 识别
        asr_service = get_asr_service()
        text = asr_service.recognize(audio_data, engine=engine, audio_format=audio_format)
        
        duration = (time.time() - start_time) * 1000
        logger.info(f"[STT] 处理完成 | text_length={len(text)} | duration={duration:.2f}ms")
        
        return text, 200, {'Content-Type': 'text/plain; charset=utf-8'}
        
    except ValidationError as e:
        duration = (time.time() - start_time) * 1000
        logger.warning(f"[STT] 验证失败 | error={e} | duration={duration:.2f}ms")
        raise
        
    except ASRError as e:
        duration = (time.time() - start_time) * 1000
        logger.error(f"[STT] 识别失败 | error={e} | duration={duration:.2f}ms")
        raise
        
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        logger.error(f"[STT] 未知错误 | error={e} | duration={duration:.2f}ms", exc_info=True)
        raise ASRError(f"语音识别失败: {str(e)}")


# ==================== AI 问答 ====================

@mcu_bp.route('/ask', methods=['POST'])
def ask():
    """AI 问答（非流式）"""
    start_time = time.time()
    
    try:
        session_id = request.args.get('session', 'default')
        
        # 获取问题
        if request.content_type and 'application/json' in request.content_type:
            try:
                data = request.get_json() or {}
                question = data.get('question', '')
                session_id = data.get('session', session_id)
            except Exception as e:
                logger.warning(f"[ASK] JSON 解析失败: {e}")
                raise ValidationError("请求格式错误，需要 JSON 格式")
        else:
            question = request.get_data(as_text=True)
        
        # 验证问题
        if not question or not question.strip():
            raise ValidationError("问题内容为空")
        
        question = question.strip()
        if len(question) > MAX_QUESTION_LENGTH:
            raise ValidationError(f"问题过长，最大支持 {MAX_QUESTION_LENGTH} 字符")
        
        logger.info(f"[ASK] 开始处理 | session={session_id} | question_length={len(question)}")
        
        # AI 问答
        ai_service = get_ai_service()
        answer = ai_service.ask(question, session_id=session_id)
        
        duration = (time.time() - start_time) * 1000
        logger.info(f"[ASK] 处理完成 | answer_length={len(answer)} | duration={duration:.2f}ms")
        
        return answer, 200, {'Content-Type': 'text/plain; charset=utf-8'}
        
    except ValidationError as e:
        duration = (time.time() - start_time) * 1000
        logger.warning(f"[ASK] 验证失败 | error={e} | duration={duration:.2f}ms")
        raise
        
    except AIError as e:
        duration = (time.time() - start_time) * 1000
        logger.error(f"[ASK] AI 服务失败 | error={e} | duration={duration:.2f}ms")
        raise
        
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        logger.error(f"[ASK] 未知错误 | error={e} | duration={duration:.2f}ms", exc_info=True)
        raise AIError(f"AI 问答失败: {str(e)}")


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
    start_time = time.time()
    
    try:
        # 获取参数
        if request.method == 'GET':
            text = request.args.get('text', '')
            voice = request.args.get('voice', 'xiaoxiao')
            output_format = request.args.get('format', 'wav')
        else:
            try:
                data = request.get_json() or {}
                text = data.get('text', '')
                voice = data.get('voice', 'xiaoxiao')
                output_format = data.get('format', 'wav')
            except Exception as e:
                logger.warning(f"[TTS] JSON 解析失败: {e}")
                raise ValidationError("请求格式错误，需要 JSON 格式")
        
        # 验证文本
        if not text or not text.strip():
            raise ValidationError("文字内容为空")
        
        text = text.strip()
        if len(text) > MAX_TEXT_LENGTH:
            raise ValidationError(f"文本过长，最大支持 {MAX_TEXT_LENGTH} 字符")
        
        # 验证格式
        if output_format not in ['wav', 'mp3']:
            raise ValidationError("不支持的音频格式，仅支持 wav 和 mp3")
        
        logger.info(f"[TTS] 开始处理 | text_length={len(text)} | voice={voice} | format={output_format}")
        
        # 语音合成
        tts_service = get_tts_service()
        file_path = tts_service.synthesize(text, voice=voice, output_format=output_format)
        
        duration = (time.time() - start_time) * 1000
        logger.info(f"[TTS] 处理完成 | file={file_path} | duration={duration:.2f}ms")
        
        mimetype = 'audio/wav' if output_format == 'wav' else 'audio/mpeg'
        return send_file(file_path, mimetype=mimetype)
        
    except ValidationError as e:
        duration = (time.time() - start_time) * 1000
        logger.warning(f"[TTS] 验证失败 | error={e} | duration={duration:.2f}ms")
        raise
        
    except TTSError as e:
        duration = (time.time() - start_time) * 1000
        logger.error(f"[TTS] 合成失败 | error={e} | duration={duration:.2f}ms")
        raise
        
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        logger.error(f"[TTS] 未知错误 | error={e} | duration={duration:.2f}ms", exc_info=True)
        raise TTSError(f"语音合成失败: {str(e)}")


# ==================== 语音对话 ====================

@mcu_bp.route('/voice_chat', methods=['POST'])
def voice_chat():
    """一站式语音对话"""
    start_time = time.time()
    
    try:
        engine = request.args.get('engine', 'tencent')
        audio_format = request.args.get('format', 'wav')
        output_type = request.args.get('out', 'text')  # text 或 audio
        session_id = request.args.get('session', 'default')
        
        # 验证输出类型
        if output_type not in ['text', 'audio']:
            raise ValidationError("不支持的输出类型，仅支持 text 和 audio")
        
        # 获取音频
        if request.content_type and 'multipart/form-data' in request.content_type:
            if 'audio' not in request.files:
                raise ValidationError("未找到音频文件")
            audio_data = request.files['audio'].read()
        else:
            audio_data = request.get_data()
        
        # 验证音频
        if not audio_data:
            raise ValidationError("音频数据为空")
        
        if len(audio_data) > MAX_AUDIO_SIZE:
            raise ValidationError(f"音频文件过大，最大支持 {MAX_AUDIO_SIZE // 1024 // 1024}MB")
        
        logger.info(f"[VOICE_CHAT] 开始处理 | engine={engine} | out={output_type} | audio_size={len(audio_data)}")
        
        # 1. 语音识别
        asr_start = time.time()
        asr_service = get_asr_service()
        question = asr_service.recognize(audio_data, engine=engine, audio_format=audio_format)
        asr_duration = (time.time() - asr_start) * 1000
        
        if not question or not question.strip():
            raise ASRError("未识别到语音内容")
        
        logger.info(f"[VOICE_CHAT] ASR 完成 | question={question[:50]}... | duration={asr_duration:.2f}ms")
        
        # 2. AI 回答
        ai_start = time.time()
        ai_service = get_ai_service()
        answer = ai_service.ask(question, session_id=session_id, short=True)
        ai_duration = (time.time() - ai_start) * 1000
        
        logger.info(f"[VOICE_CHAT] AI 完成 | answer_length={len(answer)} | duration={ai_duration:.2f}ms")
        
        # 3. 返回结果
        if output_type == 'text':
            total_duration = (time.time() - start_time) * 1000
            logger.info(f"[VOICE_CHAT] 处理完成 | total_duration={total_duration:.2f}ms")
            
            return jsonify({
                "success": True,
                "question": question,
                "answer": answer,
            })
        else:
            # 生成语音
            tts_start = time.time()
            tts_service = get_tts_service()
            file_path = tts_service.synthesize(answer, output_format='wav')
            tts_duration = (time.time() - tts_start) * 1000
            
            total_duration = (time.time() - start_time) * 1000
            logger.info(f"[VOICE_CHAT] 处理完成 | tts_duration={tts_duration:.2f}ms | total_duration={total_duration:.2f}ms")
            
            return send_file(file_path, mimetype='audio/wav')
            
    except ValidationError as e:
        duration = (time.time() - start_time) * 1000
        logger.warning(f"[VOICE_CHAT] 验证失败 | error={e} | duration={duration:.2f}ms")
        raise
        
    except ASRError as e:
        duration = (time.time() - start_time) * 1000
        logger.error(f"[VOICE_CHAT] ASR 失败 | error={e} | duration={duration:.2f}ms")
        raise
        
    except AIError as e:
        duration = (time.time() - start_time) * 1000
        logger.error(f"[VOICE_CHAT] AI 失败 | error={e} | duration={duration:.2f}ms")
        raise
        
    except TTSError as e:
        duration = (time.time() - start_time) * 1000
        logger.error(f"[VOICE_CHAT] TTS 失败 | error={e} | duration={duration:.2f}ms")
        raise
        
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        logger.error(f"[VOICE_CHAT] 未知错误 | error={e} | duration={duration:.2f}ms", exc_info=True)
        raise Exception(f"语音对话失败: {str(e)}")
