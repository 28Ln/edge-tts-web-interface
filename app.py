import os
import re
import logging
import subprocess
import shlex
import platform
import sys
import requests
import time
from flask import Flask, request, render_template, jsonify, url_for, send_from_directory, Response
from io import StringIO
from werkzeug.utils import secure_filename
from vosk import Model, KaldiRecognizer
import json
import wave
from openai import OpenAI

# 尝试导入 SocketIO (可选)
try:
    from flask_socketio import SocketIO
    SOCKETIO_AVAILABLE = True
except ImportError:
    SOCKETIO_AVAILABLE = False
    print("提示: 安装 flask-socketio 可启用实时语音识别 (pip install flask-socketio)")

app = Flask(__name__)

# 注册 MCU 专用 API
from api_mcu import mcu_api
app.register_blueprint(mcu_api)

# 注册微信 API
from api_wechat import wechat_api
app.register_blueprint(wechat_api)

# 初始化 SocketIO (如果可用)
if SOCKETIO_AVAILABLE:
    socketio = SocketIO(app, cors_allowed_origins="*")
    from api_websocket import register_websocket_handlers, create_websocket_test_page
    register_websocket_handlers(socketio)
    
    @app.route('/realtime')
    def realtime_page():
        """实时语音识别测试页面"""
        return create_websocket_test_page()
else:
    socketio = None

app.config['TTS_FOLDER'] = 'tts'
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['TTS_FOLDER'], exist_ok=True)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

log_stream = StringIO()
logging.basicConfig(level=logging.DEBUG, stream=log_stream)
logger = logging.getLogger(__name__)

VOSK_MODEL_PATH = "vosk-model-small-cn-0.22"

# 初始化 ModelScope AI 客户端
# This part was already present, but the import was missing.
# No change needed here, just ensuring the context is correct.
ai_client = OpenAI(
    base_url='https://api-inference.modelscope.cn/v1',
    api_key='ms-4e627bfb-2613-415d-a81a-3c5b6a97495f', # ModelScope Token
)

voiceMap = {
    "xiaoxiao": "zh-CN-XiaoxiaoNeural",
    "xiaoyi": "zh-CN-XiaoyiNeural",
    "yunjian": "zh-CN-YunjianNeural",
    "yunxi": "zh-CN-YunxiNeural",
    "yunxia": "zh-CN-YunxiaNeural",
    "yunyang": "zh-CN-YunyangNeural",
    "xiaobei": "zh-CN-liaoning-XiaobeiNeural",
    "xiaoni": "zh-CN-shaanxi-XiaoniNeural",
    "hiugaai": "zh-HK-HiuGaaiNeural",
    "hiumaan": "zh-HK-HiuMaanNeural",
    "wanlung": "zh-HK-WanLungNeural",
    "hsiaochen": "zh-TW-HsiaoChenNeural",
    "hsioayu": "zh-TW-HsiaoYuNeural",
    "yunjhe": "zh-TW-YunJheNeural",
    "amy": "en-US-AmyNeural",
    "nanami": "ja-JP-NanamiNeural",
    "luna": "es-ES-LunaNeural",
}

def getVoiceById(voiceId):
    return voiceMap.get(voiceId)

def remove_html(string):
    regex = re.compile(r'<[^>]+>')
    return regex.sub('', string)

def check_ffmpeg_installed():
    # 先检查本地 ffmpeg 目录
    local_ffmpeg = os.path.join(os.path.dirname(__file__), "ffmpeg", "ffmpeg-master-latest-win64-gpl", "bin")
    if os.path.exists(local_ffmpeg):
        os.environ["PATH"] = local_ffmpeg + os.pathsep + os.environ.get("PATH", "")
        logger.info(f"使用本地 FFmpeg: {local_ffmpeg}")
    
    try:
        subprocess.run(["ffmpeg", "-version"], check=True, capture_output=True, text=True)
        logger.info("FFmpeg 已安装")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.warning("FFmpeg 未安装")
        return False

def install_ffmpeg():
    system = platform.system().lower()
    logger.info(f"检测到操作系统: {system}")
    if system == "linux":
        try:
            if subprocess.call(["apt-get", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE) == 0:
                subprocess.run(["sudo", "apt-get", "update"], check=True)
                subprocess.run(["sudo", "apt-get", "install", "-y", "ffmpeg"], check=True)
                logger.info("FFmpeg 已通过 apt-get 安装")
            else:
                logger.error("不支持的 Linux 包管理器，请手动安装 FFmpeg")
                return False
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg 安装失败: {e}")
            return False
    elif system == "darwin":
        try:
            if subprocess.call(["brew", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE) != 0:
                logger.info("Homebrew 未安装，正在安装...")
                subprocess.run(['/bin/bash', '-c', '$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)'], check=True)
            subprocess.run(["brew", "install", "ffmpeg"], check=True)
            logger.info("FFmpeg 已通过 Homebrew 安装")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg 安装失败: {e}")
            return False
    elif system == "windows":
        try:
            ffmpeg_url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
            ffmpeg_zip = "ffmpeg.zip"
            ffmpeg_dir = "ffmpeg"
            logger.info("正在下载 FFmpeg...")
            print("正在下载 FFmpeg，这可能需要几分钟时间，请耐心等待...")
            
            retries = 3
            for i in range(retries):
                try:
                    with requests.get(ffmpeg_url, stream=True) as r:
                        r.raise_for_status()
                        total_size = int(r.headers.get('content-length', 0))
                        downloaded_size = 0
                        with open(ffmpeg_zip, 'wb') as f:
                            for chunk in r.iter_content(chunk_size=8192):
                                f.write(chunk)
                                downloaded_size += len(chunk)
                                progress = (downloaded_size / total_size) * 100
                                sys.stdout.write(f"\r下载进度: {progress:.2f}%")
                                sys.stdout.flush()
                    print("\nFFmpeg 下载完成。")
                    break
                except (requests.exceptions.RequestException, IOError) as e:
                    print(f"\n下载失败 (尝试 {i+1}/{retries}): {e}")
                    if i < retries - 1:
                        print("正在重试...")
                        time.sleep(5)
                    else:
                        print("已达到最大重试次数，下载失败。")
                        return False
            import zipfile
            print("正在解压 FFmpeg...")
            with zipfile.ZipFile(ffmpeg_zip, 'r') as zip_ref:
                zip_ref.extractall(ffmpeg_dir)
            print("FFmpeg 解压完成。")
            os.remove(ffmpeg_zip)
            ffmpeg_path = os.path.abspath(os.path.join(ffmpeg_dir, "ffmpeg-master-latest-win64-gpl", "bin"))
            os.environ["PATH"] += os.pathsep + ffmpeg_path
            logger.info(f"FFmpeg 已安装到 {ffmpeg_path}")
            print("FFmpeg 已成功安装并配置。")
            return True
        except Exception as e:
            logger.error(f"FFmpeg 安装失败: {e}")
            print(f"FFmpeg 安装失败: {e}")
            return False
    else:
        logger.error(f"不支持的操作系统: {system}")
        return False

def ensure_ffmpeg():
    if not check_ffmpeg_installed():
        logger.info("正在尝试自动安装 FFmpeg...")
        if install_ffmpeg():
            logger.info("FFmpeg 安装成功")
        else:
            logger.error("FFmpeg 安装失败，请手动安装")
            sys.exit(1)

def generate_srt(text, audio_file, file_name):
    srt_path = os.path.join(app.config['TTS_FOLDER'], f"{file_name}.srt")
    lines = text.split('\n')
    duration = 5
    with open(srt_path, 'w', encoding='utf-8') as f:
        for i, line in enumerate(lines, 1):
            if line.strip():
                start_time = f"00:00:{(i-1)*2:02d},000"
                end_time = f"00:00:{i*2:02d},000"
                f.write(f"{i}\n{start_time} --> {end_time}\n{line.strip()}\n\n")
    return srt_path

def convert_audio_format(input_file, output_format):
    output_file = input_file.replace('.mp3', f'.{output_format}')
    command = ["ffmpeg", "-i", input_file, "-y", output_file]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        return output_file
    except subprocess.CalledProcessError as e:
        logger.error(f"Audio conversion failed: {e}")
        return None

def createAudio(text, file_path, voiceId, rate=None, pitch=None, volume=None, ssml=None, output_format="mp3"):
    voice = getVoiceById(voiceId)
    if not voice:
        logger.error("Invalid voice ID")
        return "error params"

    for filename in os.listdir(app.config['TTS_FOLDER']):
        if filename.endswith((".mp3", ".wav", ".srt")):
            os.remove(os.path.join(app.config['TTS_FOLDER'], filename))

    command = ["edge-tts", "--voice", voice]
    if ssml:
        command.extend(["--ssml", ssml])
    else:
        new_text = remove_html(text)
        command.extend(["--text", new_text])
    if rate:
        command.extend(["--rate", str(rate)])
    if pitch:
        command.extend(["--pitch", str(pitch)])
    if volume:
        command.extend(["--volume", str(volume)])
    temp_file = file_path if output_format == "mp3" else file_path.replace(f".{output_format}", ".mp3")
    command.extend(["--write-media", temp_file])
    logger.debug(f"Running command: {' '.join(map(shlex.quote, command))}")

    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        if os.path.exists(temp_file):
            logger.debug(f"File created successfully: {temp_file}")
            if output_format != "mp3":
                final_file = convert_audio_format(temp_file, output_format)
                if final_file and os.path.exists(final_file):
                    os.remove(temp_file)
                    return "success", final_file
                return "conversion failed", temp_file
            return "success", temp_file
        else:
            logger.error(f"File not created: {temp_file}")
            return "file not created", temp_file
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with exit code {e.returncode}")
        return "command failed", temp_file
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")
        return "unexpected error", temp_file

def speech_to_text(audio_file):
    if not os.path.exists(VOSK_MODEL_PATH):
        logger.error("Vosk 模型未找到，请确保 vosk-model-small-cn-0.22 已解压到项目根目录")
        return "模型未找到"

    model = Model(VOSK_MODEL_PATH)
    rec = KaldiRecognizer(model, 16000)

    with wave.open(audio_file, "rb") as wf:
        if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getframerate() != 16000:
            logger.error("音频格式必须为单声道 16kHz WAV")
            return "音频格式错误"
        
        transcription = ""
        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result()).get("text", "")
                transcription += result + " "
            else:
                partial = json.loads(rec.PartialResult()).get("partial", "")
                logger.debug(f"部分结果: {partial}")
        
        final_result = json.loads(rec.FinalResult()).get("text", "")
        transcription += final_result
        return transcription.strip()

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        text = request.form.get('text', '')
        file_name = request.form.get('file_name', 'output')
        voice = request.form['voice']
        rate = request.form.get('rate')
        pitch = request.form.get('pitch')
        volume = request.form.get('volume')
        ssml = request.form.get('ssml')
        output_format = request.form.get('output_format', 'mp3')
        generate_subtitles = 'generate_subtitles' in request.form

        file_name = secure_filename(file_name)
        file_path = os.path.join(app.config['TTS_FOLDER'], f"{file_name}.{output_format}")

        if 'text_file' in request.files:
            file = request.files['text_file']
            if file and file.filename.endswith('.txt'):
                text = file.read().decode('utf-8')

        result, final_file = createAudio(text, file_path, voice, rate, pitch, volume, ssml, output_format)
        log_stream.seek(0)
        logs = log_stream.read()

        base_url = request.host_url.rstrip('/')
        response_data = {"result": result, "console": logs}

        if result == "success":
            file_url = f"{base_url}{url_for('download_file', filename=os.path.basename(final_file))}"
            response_data["file_url"] = file_url
            if generate_subtitles:
                srt_path = generate_srt(text, final_file, file_name)
                srt_url = f"{base_url}{url_for('download_file', filename=f'{file_name}.srt')}"
                response_data["srt_url"] = srt_url

        return jsonify(response_data)

    return render_template('index.html', voiceMap=voiceMap)

@app.route('/api/tts', methods=['POST'])
def tts():
    data = request.get_json()
    text = data.get('text', '')
    file_name = data.get('file_name', 'output')
    voice = data.get('voice', 'xiaoxiao')
    output_format = data.get('output_format', 'mp3')

    file_name = secure_filename(file_name)
    file_path = os.path.join(app.config['TTS_FOLDER'], f"{file_name}.{output_format}")
    result, final_file = createAudio(text, file_path, voice)
    
    if result == "success":
        file_url = url_for('download_file', filename=os.path.basename(final_file), _external=True)
        return jsonify({"result": "success", "file_url": file_url})
    else:
        return jsonify({"result": "error", "message": result}), 500

@app.route('/stt', methods=['POST'])
def stt():
    if 'audio_file' not in request.files:
        return jsonify({"result": "error", "message": "未上传音频文件"}), 400
    
    audio_file = request.files['audio_file']
    if audio_file.filename == '':
        return jsonify({"result": "error", "message": "文件名为空"}), 400
    
    original_filename = secure_filename(audio_file.filename)
    audio_path = os.path.join(app.config['UPLOAD_FOLDER'], original_filename)
    wav_path = None  # 初始化 wav_path

    try:
        audio_file.save(audio_path)

        base_name, _ = os.path.splitext(original_filename)
        wav_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{base_name}_converted.wav")
        
        try:
            # 强制将所有上传的音频转换为单声道、16kHz 的 WAV 格式
            subprocess.run(["ffmpeg", "-i", audio_path, "-ac", "1", "-ar", "16000", wav_path, "-y"], check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg 转换失败: {e.stderr}")
            return jsonify({"result": "error", "message": "音频转换失败", "console": log_stream.getvalue()}), 500

        transcription = speech_to_text(wav_path)
        log_stream.seek(0)
        logs = log_stream.read()

        if transcription.startswith("模型未找到") or transcription.startswith("音频格式错误"):
            return jsonify({"result": "error", "message": transcription, "console": logs}), 400
        
        return jsonify({"result": "success", "transcription": transcription, "console": logs})

    except Exception as e:
        logger.error(f"处理 STT 请求时出错: {e}")
        return jsonify({"result": "error", "message": "服务器内部错误", "console": str(e)}), 500
    finally:
        # 清理所有临时文件
        if os.path.exists(audio_path):
            os.remove(audio_path)
        if wav_path and os.path.exists(wav_path):
            os.remove(wav_path)

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['TTS_FOLDER'], filename, as_attachment=True)

# This part was already present.
# No change needed here, just ensuring the context is correct.
@app.route('/api/ask_ai', methods=['POST'])
def ask_ai():
    if 'audio_file' not in request.files:
        return jsonify({"result": "error", "message": "未上传音频文件"}), 400
    
    audio_file = request.files['audio_file']
    if audio_file.filename == '':
        return jsonify({"result": "error", "message": "文件名为空"}), 400
    
    original_filename = secure_filename(audio_file.filename)
    audio_path = os.path.join(app.config['UPLOAD_FOLDER'], original_filename)
    wav_path = None

    try:
        audio_file.save(audio_path)

        base_name, _ = os.path.splitext(original_filename)
        wav_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{base_name}_converted.wav")
        
        try:
            subprocess.run(["ffmpeg", "-i", audio_path, "-ac", "1", "-ar", "16000", wav_path, "-y"], check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg 转换失败: {e.stderr}")
            return jsonify({"result": "error", "message": "音频转换失败"}), 500

        # 语音转文本
        transcription = speech_to_text(wav_path)
        if transcription.startswith("模型未找到") or transcription.startswith("音频格式错误"):
            return jsonify({"result": "error", "message": transcription}), 400
        
        logger.info(f"语音转文本结果: {transcription}")

        # 调用 AI 模型并返回 multipart 响应
        def generate_multipart():
            # Part 1: STT 结果
            stt_json = json.dumps({"type": "stt_result", "transcription": transcription})
            yield (b'--frame\r\n'
                   b'Content-Type: application/json\r\n\r\n' + stt_json.encode('utf-8') + b'\r\n')

            # Part 2: AI 流式响应
            try:
                ai_response = ai_client.chat.completions.create(
                    model='Qwen/Qwen3-Coder-480B-A35B-Instruct',
                    messages=[
                        {'role': 'system', 'content': 'You are a helpful assistant.'},
                        {'role': 'user', 'content': transcription}
                    ],
                    stream=True
                )
                for chunk in ai_response:
                    content = chunk.choices[0].delta.content
                    if content:
                        yield (b'--frame\r\n'
                               b'Content-Type: text/plain; charset=utf-8\r\n\r\n' + content.encode('utf-8') + b'\r\n')
            except Exception as e:
                logger.error(f"调用 AI 模型时出错: {e}")
                error_message = "调用 AI 模型时出错。"
                yield (b'--frame\r\n'
                       b'Content-Type: text/plain; charset=utf-8\r\n\r\n' + error_message.encode('utf-8') + b'\r\n')

        return Response(generate_multipart(), mimetype='multipart/x-mixed-replace; boundary=frame')

    except Exception as e:
        logger.error(f"处理 AI 请求时出错: {e}")
        return jsonify({"result": "error", "message": "服务器内部错误"}), 500
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)
        if wav_path and os.path.exists(wav_path):
            os.remove(wav_path)

if __name__ == "__main__":
    ensure_ffmpeg()
    if not os.path.exists(VOSK_MODEL_PATH):
        print(f"请下载 vosk-model-small-cn-0.22.zip 并解压到 {VOSK_MODEL_PATH}")
        print("下载地址: https://alphacephei.com/vosk/models/vosk-model-small-cn-0.22.zip")
        sys.exit(1)
    
    # 服务端口配置
    PORT = int(os.environ.get('PORT', 3003))
    
    print("=" * 50)
    print("服务器正在运行")
    print("=" * 50)
    print(f"端口: {PORT}")
    print(f"本地访问: http://127.0.0.1:{PORT}")
    print(f"外网访问: http://你的IP:{PORT}")
    print(f"MCU API:  /mcu/...")
    print(f"微信 API: /wechat/...")
    if SOCKETIO_AVAILABLE:
        print(f"实时语音: /realtime")
        print("=" * 50)
        socketio.run(app, port=PORT, host="0.0.0.0", debug=False, allow_unsafe_werkzeug=True)
    else:
        print("提示: pip install flask-socketio 可启用实时语音")
        print("=" * 50)
        app.run(port=PORT, host="0.0.0.0", debug=False)