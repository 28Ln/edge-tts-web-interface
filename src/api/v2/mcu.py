"""
MCU API v2
带认证、计费和结构化响应的版本
"""

from flask import Blueprint, request, jsonify, Response, send_file, g

from ...services.ai_service import get_ai_service
from ...services.asr_service import get_asr_service
from ...services.tts_service import get_tts_service
from ...utils.logger import get_api_logger
from ...exceptions import ValidationError, ASRError
from ...auth.api_key import require_api_key, optional_api_key
from ...auth.quota import check_quota, record_usage
from ...models.schemas import make_response, make_error

logger = get_api_logger()


def register_mcu_routes(parent_bp: Blueprint):
    """注册 MCU v2 路由到父蓝图"""
    
    mcu_bp = Blueprint('mcu_v2', __name__, url_prefix='/mcu')

    # ==================== 基础接口 ====================

    @mcu_bp.route('/ping', methods=['GET'])
    def ping():
        """连接测试"""
        return jsonify(make_response({"message": "pong"}))

    @mcu_bp.route('/status', methods=['GET'])
    @optional_api_key()
    def status():
        """获取服务状态"""
        asr_service = get_asr_service()
        
        user = getattr(g, 'current_user', None)
        
        response_data = {
            "asr_engines": asr_service.get_available_engines(),
            "ai": True,
            "tts": True,
            "version": "2.0.0",
            "authenticated": user is not None,
        }
        
        if user:
            from ...auth.quota import get_quota_manager
            manager = get_quota_manager()
            response_data["quota"] = manager.get_usage_summary(user.id)
        
        return jsonify(make_response(response_data))

    # ==================== 语音识别 ====================

    @mcu_bp.route('/stt', methods=['POST'])
    @require_api_key('stt')
    @check_quota('requests')
    def stt():
        """语音转文字 v2"""
        import time
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
            
            if not audio_data:
                raise ValidationError("音频数据为空")
            
            # 验证音频大小
            MAX_AUDIO_SIZE = 10 * 1024 * 1024  # 10MB
            if len(audio_data) > MAX_AUDIO_SIZE:
                raise ValidationError(f"音频文件过大，最大支持 {MAX_AUDIO_SIZE // 1024 // 1024}MB")
            
            logger.info(f"[STT v2] 开始处理 | user={g.current_user.username} | engine={engine} | format={audio_format} | size={len(audio_data)}")
            
            # 识别
            asr_service = get_asr_service()
            text = asr_service.recognize(audio_data, engine=engine, audio_format=audio_format)
            
            # 记录用量
            audio_seconds = len(audio_data) / (16000 * 2)
            record_usage('/v2/mcu/stt', audio_seconds=audio_seconds)
            
            duration = (time.time() - start_time) * 1000
            logger.info(f"[STT v2] 处理完成 | user={g.current_user.username} | text_length={len(text)} | duration={duration:.2f}ms")
            
            return jsonify(make_response({
                "text": text,
                "engine": engine,
                "audio_duration": round(audio_seconds, 2),
            }))
            
        except ValidationError as e:
            duration = (time.time() - start_time) * 1000
            logger.warning(f"[STT v2] 验证失败 | user={g.current_user.username} | error={e} | duration={duration:.2f}ms")
            raise
        except ASRError as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"[STT v2] ASR 错误 | user={g.current_user.username} | error={e} | duration={duration:.2f}ms")
            raise
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"[STT v2] 未知错误 | user={g.current_user.username} | error={e} | duration={duration:.2f}ms", exc_info=True)
            raise

    # ==================== AI 问答 ====================

    @mcu_bp.route('/ask', methods=['POST'])
    @require_api_key('ai')
    @check_quota('requests')
    def ask():
        """AI 问答 v2"""
        import time
        start_time = time.time()
        
        try:
            session_id = request.args.get('session', 'default')
            
            # 解析请求
            if request.content_type and 'application/json' in request.content_type:
                try:
                    data = request.get_json() or {}
                    question = data.get('question', '')
                    session_id = data.get('session', session_id)
                except Exception as e:
                    raise ValidationError(f"JSON 解析失败: {e}")
            else:
                question = request.get_data(as_text=True)
            
            if not question or not question.strip():
                raise ValidationError("问题内容为空")
            
            question = question.strip()
            
            # 验证问题长度
            MAX_QUESTION_LENGTH = 1000
            if len(question) > MAX_QUESTION_LENGTH:
                raise ValidationError(f"问题过长，最大支持 {MAX_QUESTION_LENGTH} 字符")
            
            logger.info(f"[ASK v2] 开始处理 | user={g.current_user.username} | session={session_id} | question_length={len(question)}")
            
            ai_service = get_ai_service()
            answer = ai_service.ask(question, session_id=session_id)
            
            # 记录用量
            tokens = len(question) + len(answer)
            record_usage('/v2/mcu/ask', tokens=tokens)
            
            duration = (time.time() - start_time) * 1000
            logger.info(f"[ASK v2] 处理完成 | user={g.current_user.username} | answer_length={len(answer)} | duration={duration:.2f}ms")
            
            return jsonify(make_response({
                "answer": answer,
                "session": session_id,
                "tokens_used": tokens,
            }))
            
        except ValidationError as e:
            duration = (time.time() - start_time) * 1000
            logger.warning(f"[ASK v2] 验证失败 | user={g.current_user.username} | error={e} | duration={duration:.2f}ms")
            raise
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"[ASK v2] 未知错误 | user={g.current_user.username} | error={e} | duration={duration:.2f}ms", exc_info=True)
            raise

    @mcu_bp.route('/ask_stream', methods=['POST'])
    @require_api_key('ai')
    @check_quota('requests')
    def ask_stream():
        """AI 流式问答 v2"""
        session_id = request.args.get('session', 'default')
        
        if request.content_type and 'application/json' in request.content_type:
            data = request.get_json() or {}
            question = data.get('question', '')
            session_id = data.get('session', session_id)
        else:
            question = request.get_data(as_text=True)
        
        if not question:
            raise ValidationError("问题内容为空")
        
        logger.info(f"[ASK_STREAM v2] 请求 | user={g.current_user.username}")
        
        def generate():
            ai_service = get_ai_service()
            try:
                for chunk in ai_service.ask_stream(question, session_id=session_id):
                    yield f"data: {chunk}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                logger.error(f"[ASK_STREAM v2] 错误: {e}")
                yield f"data: [ERROR] {str(e)}\n\n"
        
        return Response(generate(), mimetype='text/event-stream')

    # ==================== 语音合成 ====================

    @mcu_bp.route('/tts', methods=['GET', 'POST'])
    @require_api_key('tts')
    @check_quota('requests')
    def tts():
        """文字转语音 v2"""
        import time
        start_time = time.time()
        
        try:
            if request.method == 'GET':
                text = request.args.get('text', '')
                voice = request.args.get('voice', 'xiaoxiao')
                output_format = request.args.get('format', 'wav')
            else:
                data = request.get_json() or {}
                text = data.get('text', '')
                voice = data.get('voice', 'xiaoxiao')
                output_format = data.get('format', 'wav')
            
            if not text or not text.strip():
                raise ValidationError("文字内容为空")
            
            text = text.strip()
            
            # 验证文本长度
            MAX_TEXT_LENGTH = 5000
            if len(text) > MAX_TEXT_LENGTH:
                raise ValidationError(f"文本过长，最大支持 {MAX_TEXT_LENGTH} 字符")
            
            # 验证格式
            if output_format not in ['wav', 'mp3']:
                raise ValidationError(f"不支持的格式: {output_format}，仅支持 wav 或 mp3")
            
            logger.info(f"[TTS v2] 开始处理 | user={g.current_user.username} | voice={voice} | format={output_format} | text_length={len(text)}")
            
            tts_service = get_tts_service()
            file_path = tts_service.synthesize(text, voice=voice, output_format=output_format)
            
            # 记录用量
            record_usage('/v2/mcu/tts', characters=len(text))
            
            duration = (time.time() - start_time) * 1000
            logger.info(f"[TTS v2] 处理完成 | user={g.current_user.username} | duration={duration:.2f}ms")
            
            mimetype = 'audio/wav' if output_format == 'wav' else 'audio/mpeg'
            return send_file(file_path, mimetype=mimetype)
            
        except ValidationError as e:
            duration = (time.time() - start_time) * 1000
            logger.warning(f"[TTS v2] 验证失败 | user={g.current_user.username} | error={e} | duration={duration:.2f}ms")
            raise
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"[TTS v2] 未知错误 | user={g.current_user.username} | error={e} | duration={duration:.2f}ms", exc_info=True)
            raise

    # ==================== 语音对话 ====================

    @mcu_bp.route('/voice_chat', methods=['POST'])
    @require_api_key('voice_chat')
    @check_quota('requests')
    def voice_chat():
        """一站式语音对话 v2"""
        import time
        start_time = time.time()
        
        try:
            engine = request.args.get('engine', 'tencent')
            audio_format = request.args.get('format', 'wav')
            output_type = request.args.get('out', 'text')
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
            
            # 验证音频大小
            MAX_AUDIO_SIZE = 10 * 1024 * 1024  # 10MB
            if len(audio_data) > MAX_AUDIO_SIZE:
                raise ValidationError(f"音频文件过大，最大支持 {MAX_AUDIO_SIZE // 1024 // 1024}MB")
            
            logger.info(f"[VOICE_CHAT v2] 开始处理 | user={g.current_user.username} | engine={engine} | out={output_type} | size={len(audio_data)}")

            try:
                save_dir = os.environ.get("VOICE_CHAT_RECORDINGS_DIR") or os.path.join(os.getcwd(), "recordings", "voice_chat")
                os.makedirs(save_dir, exist_ok=True)
                ts = time.strftime("%Y%m%d_%H%M%S")
                safe_engine = "".join([c for c in (engine or "") if c.isalnum() or c in ("-", "_")]) or "engine"
                safe_session = "".join([c for c in (session_id or "") if c.isalnum() or c in ("-", "_")]) or "default"
                ext = (audio_format or "wav").lower()
                if ext not in ("wav", "mp3", "pcm", "m4a", "aac", "ogg"):
                    ext = "bin"
                save_path = os.path.join(save_dir, f"{ts}_{safe_engine}_{safe_session}.{ext}")
                with open(save_path, "wb") as f:
                    f.write(audio_data)
                logger.info(f"[VOICE_CHAT v2] audio saved: {save_path}")
            except Exception as e:
                logger.warning(f"[VOICE_CHAT v2] audio save failed: {e}")
            
            # 1. 语音识别
            asr_start = time.time()
            asr_service = get_asr_service()
            question = asr_service.recognize(audio_data, engine=engine, audio_format=audio_format)
            asr_duration = (time.time() - asr_start) * 1000
            
            if not question or not question.strip():
                fallback = "我没听清，请再说一遍。"
                logger.warning(f"[VOICE_CHAT v2] ASR 为空 | user={g.current_user.username} | duration={asr_duration:.2f}ms")
                if output_type == 'text':
                    total_duration = (time.time() - start_time) * 1000
                    logger.info(f"[VOICE_CHAT v2] 处理完成 | user={g.current_user.username} | total_duration={total_duration:.2f}ms")
                    return jsonify(make_response({
                        "question": "",
                        "answer": fallback,
                        "session": session_id,
                    }))
                else:
                    tts_start = time.time()
                    tts_service = get_tts_service()
                    file_path = tts_service.synthesize(fallback, output_format='wav')
                    tts_duration = (time.time() - tts_start) * 1000
                    total_duration = (time.time() - start_time) * 1000
                    logger.info(f"[VOICE_CHAT v2] 处理完成 | user={g.current_user.username} | tts_duration={tts_duration:.2f}ms | total_duration={total_duration:.2f}ms")
                    return send_file(file_path, mimetype='audio/wav')
            
            logger.info(f"[VOICE_CHAT v2] ASR 完成 | user={g.current_user.username} | question={question[:50]} | duration={asr_duration:.2f}ms")
            
            # 2. AI 回答
            ai_start = time.time()
            ai_service = get_ai_service()
            answer = ai_service.ask(question, session_id=session_id, short=True)
            ai_duration = (time.time() - ai_start) * 1000
            
            logger.info(f"[VOICE_CHAT v2] AI 完成 | user={g.current_user.username} | answer_length={len(answer)} | duration={ai_duration:.2f}ms")
            
            # 记录用量
            audio_seconds = len(audio_data) / (16000 * 2)
            record_usage('/v2/mcu/voice_chat', audio_seconds=audio_seconds, tokens=len(question)+len(answer))
            
            # 3. 返回结果
            if output_type == 'text':
                total_duration = (time.time() - start_time) * 1000
                logger.info(f"[VOICE_CHAT v2] 处理完成 | user={g.current_user.username} | total_duration={total_duration:.2f}ms")
                
                return jsonify(make_response({
                    "question": question,
                    "answer": answer,
                    "session": session_id,
                }))
            else:
                tts_start = time.time()
                tts_service = get_tts_service()
                file_path = tts_service.synthesize(answer, output_format='wav')
                tts_duration = (time.time() - tts_start) * 1000
                
                total_duration = (time.time() - start_time) * 1000
                logger.info(f"[VOICE_CHAT v2] 处理完成 | user={g.current_user.username} | tts_duration={tts_duration:.2f}ms | total_duration={total_duration:.2f}ms")
                
                return send_file(file_path, mimetype='audio/wav')
                
        except ValidationError as e:
            duration = (time.time() - start_time) * 1000
            logger.warning(f"[VOICE_CHAT v2] 验证失败 | user={g.current_user.username} | error={e} | duration={duration:.2f}ms")
            raise
        except ASRError as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"[VOICE_CHAT v2] ASR 错误 | user={g.current_user.username} | error={e} | duration={duration:.2f}ms")
            raise
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"[VOICE_CHAT v2] 未知错误 | user={g.current_user.username} | error={e} | duration={duration:.2f}ms", exc_info=True)
            raise

    # 注册到父蓝图
    parent_bp.register_blueprint(mcu_bp)
