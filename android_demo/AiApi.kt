package com.ven.assists.simple.common

import android.os.Handler
import android.os.Looper
import com.google.gson.Gson
import com.google.gson.annotations.SerializedName
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.File
import java.io.IOException
import java.util.concurrent.TimeUnit

/**
 * AI API 客户端
 * 
 * 核心接口：
 * - speechToText: 语音识别（立即返回）
 * - askAiStream: AI流式问答
 * - textToSpeech: 文字转语音
 */
object AiApi {
    private const val BASE_URL = "http://192.168.1.117:3003"

    // MCU API 接口
    private const val STT_URL = "$BASE_URL/mcu/stt"
    private const val TTS_URL = "$BASE_URL/mcu/tts"
    private const val ASK_STREAM_URL = "$BASE_URL/mcu/ask_stream"
    private const val PING_URL = "$BASE_URL/mcu/ping"
    private const val STATUS_URL = "$BASE_URL/mcu/status"

    private val client = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .build()

    private val gson = Gson()
    private val handler = Handler(Looper.getMainLooper())

    // ==================== 核心接口 ====================

    /**
     * 语音识别 - 立即返回结果
     * 
     * @param audioFile WAV音频文件
     * @param engine 识别引擎: "tencent"(推荐) 或 "vosk"(本地)
     * @param onResult 回调，返回识别文本（失败返回null）
     */
    fun speechToText(
        audioFile: File,
        engine: String = "tencent",
        onResult: (String?) -> Unit
    ) {
        Thread {
            try {
                val url = "$STT_URL?engine=$engine&format=wav"
                val requestBody = audioFile.asRequestBody("application/octet-stream".toMediaTypeOrNull())
                val request = Request.Builder().url(url).post(requestBody).build()

                client.newCall(request).execute().use { response ->
                    val text = response.body?.string()
                    // 检查是否是错误响应
                    val result = if (text?.startsWith("错误:") == true) null else text
                    handler.post { onResult(result) }
                }
            } catch (e: Exception) {
                handler.post { onResult(null) }
            }
        }.start()
    }

    /**
     * AI流式问答 - 实时返回回答内容
     * 
     * @param question 问题文本
     * @param onResponse 每收到一段回答时回调
     * @param onComplete 回答完成时回调
     * @param onError 出错时回调
     */
    fun askAiStream(
        question: String,
        onResponse: (String) -> Unit,
        onComplete: () -> Unit,
        onError: (Exception) -> Unit
    ) {
        Thread {
            try {
                val requestBody = question.toRequestBody("text/plain; charset=utf-8".toMediaTypeOrNull())
                val request = Request.Builder().url(ASK_STREAM_URL).post(requestBody).build()

                client.newCall(request).execute().use { response ->
                    if (!response.isSuccessful) throw IOException("请求失败: $response")

                    val source = response.body!!.source()
                    while (!source.exhausted()) {
                        val line = source.readUtf8Line() ?: break
                        if (line.startsWith("data: ")) {
                            val data = line.substring(6)
                            if (data != "[DONE]" && !data.startsWith("[ERROR]")) {
                                handler.post { onResponse(data) }
                            }
                        }
                    }
                    handler.post { onComplete() }
                }
            } catch (e: Exception) {
                handler.post { onError(e) }
            }
        }.start()
    }

    /**
     * 文字转语音
     * 
     * @param text 要转换的文字
     * @param voice 语音: "xiaoxiao" 或 "yunxi"
     * @param onResult 回调，返回音频数据（失败返回null）
     */
    fun textToSpeech(
        text: String,
        voice: String = "xiaoxiao",
        onResult: (ByteArray?) -> Unit
    ) {
        Thread {
            try {
                val url = "$TTS_URL?text=${java.net.URLEncoder.encode(text, "UTF-8")}&voice=$voice&format=wav"
                val request = Request.Builder().url(url).get().build()

                client.newCall(request).execute().use { response ->
                    val bytes = response.body?.bytes()
                    handler.post { onResult(bytes) }
                }
            } catch (e: Exception) {
                handler.post { onResult(null) }
            }
        }.start()
    }

    // ==================== 辅助接口 ====================

    /** 连接测试 */
    fun ping(onResult: (Boolean) -> Unit) {
        Thread {
            try {
                val request = Request.Builder().url(PING_URL).get().build()
                client.newCall(request).execute().use { response ->
                    val result = response.body?.string() == "pong"
                    handler.post { onResult(result) }
                }
            } catch (e: Exception) {
                handler.post { onResult(false) }
            }
        }.start()
    }

    /** 获取服务状态 */
    data class StatusResponse(
        val vosk: Boolean = false,
        val tencent: Boolean = false,
        val ai: Boolean = false,
        val tts: Boolean = false
    )

    fun getStatus(onResult: (StatusResponse?) -> Unit) {
        Thread {
            try {
                val request = Request.Builder().url(STATUS_URL).get().build()
                client.newCall(request).execute().use { response ->
                    val json = response.body?.string() ?: "{}"
                    val status = gson.fromJson(json, StatusResponse::class.java)
                    handler.post { onResult(status) }
                }
            } catch (e: Exception) {
                handler.post { onResult(null) }
            }
        }.start()
    }

    // ==================== 兼容旧接口 ====================

    /**
     * 语音问答（兼容旧实现）
     * 先识别语音，再流式AI回答
     */
    fun askAiWithAudio(
        audioFile: File,
        onResponse: (String) -> Unit,
        onComplete: () -> Unit,
        onError: (Exception) -> Unit
    ) {
        // 先进行语音识别
        speechToText(audioFile, engine = "tencent") { recognizedText ->
            if (recognizedText.isNullOrBlank()) {
                onError(Exception("语音识别失败"))
                return@speechToText
            }

            // 显示识别结果
            onResponse("【识别】$recognizedText\n\n【回答】")

            // 再进行流式AI问答
            askAiStream(
                question = recognizedText,
                onResponse = onResponse,
                onComplete = onComplete,
                onError = onError
            )
        }
    }
}