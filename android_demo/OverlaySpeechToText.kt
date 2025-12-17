package com.ven.assists.simple.overlays

import android.annotation.SuppressLint
import android.view.LayoutInflater
import android.view.View
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.TextView
import androidx.core.content.ContextCompat
import com.blankj.utilcode.util.ScreenUtils
import com.ven.assists.service.AssistsService
import com.ven.assists.simple.R
import com.ven.assists.simple.common.AiApi
import com.ven.assists.simple.common.AudioRecorder
import com.ven.assists.simple.common.LogWrapper
import com.ven.assists.simple.databinding.SpeechToTextOverlayBinding
import com.ven.assists.window.AssistsWindowManager
import com.ven.assists.window.AssistsWindowWrapper
import java.io.File

@SuppressLint("StaticFieldLeak", "MissingPermission")
object OverlaySpeechToText {

    // 简化为3种模式
    enum class Mode(val displayName: String, val description: String) {
        VOICE_CHAT("语音对话", "录音 → 识别 → AI回答"),
        STT_ONLY("仅语音识别", "录音 → 识别结果"),
        ASK_ONLY("仅AI问答", "文字 → AI回答")
    }

    private var currentMode = Mode.VOICE_CHAT
    private var isRecording = false

    // 录音相关
    private var audioRecorder: AudioRecorder? = null
    private var audioFile: File? = null

    private var viewBinding: SpeechToTextOverlayBinding? = null
        get() {
            if (field == null) {
                val context = AssistsService.instance ?: return null
                field = SpeechToTextOverlayBinding.inflate(LayoutInflater.from(context))
                setupViews(field!!)
            }
            return field
        }

    var onClose: ((parent: View) -> Unit)? = null

    var showed = false
        private set
        get() {
            field = assistWindowWrapper?.let { AssistsWindowManager.isVisible(it.getView()) } ?: false
            return field
        }

    var assistWindowWrapper: AssistsWindowWrapper? = null
        private set
        get() {
            viewBinding?.let {
                if (field == null) {
                    val params = AssistsWindowManager.createLayoutParams().apply {
                        width = (ScreenUtils.getScreenWidth() * 0.85).toInt()
                        height = (ScreenUtils.getScreenHeight() * 0.55).toInt()
                    }
                    field = AssistsWindowWrapper(it.root, wmLayoutParams = params, onClose = {
                        hide()
                        onClose?.invoke(it)
                    }).apply {
                        minWidth = (ScreenUtils.getScreenWidth() * 0.6).toInt()
                        minHeight = (ScreenUtils.getScreenHeight() * 0.4).toInt()
                        initialCenter = true
                    }
                }
            }
            return field
        }

    fun show() {
        if (!AssistsWindowManager.contains(assistWindowWrapper?.getView())) {
            AssistsWindowManager.add(assistWindowWrapper)
            viewBinding?.llChatContainer?.removeAllViews()
            addAiMessage("选择模式后点击按钮开始")
        }
    }

    fun hide() {
        stopRecording()
        AssistsWindowManager.removeView(assistWindowWrapper?.getView())
    }

    private fun setupViews(binding: SpeechToTextOverlayBinding) {
        val context = binding.root.context

        // 设置模式选择器
        val adapter = ArrayAdapter(
            context,
            android.R.layout.simple_spinner_item,
            Mode.values().map { it.displayName }
        )
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
        binding.spinnerMode.adapter = adapter

        binding.spinnerMode.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                currentMode = Mode.values()[position]
                updateUI()
                LogWrapper.logAppend("切换模式: ${currentMode.displayName}")
            }
            override fun onNothingSelected(parent: AdapterView<*>?) {}
        }

        binding.btnRecord.setOnClickListener {
            if (isRecording) {
                stopAndProcess()
            } else {
                startAction()
            }
        }

        updateUI()
    }

    private fun updateUI() {
        viewBinding?.tvModeInfo?.text = currentMode.description
        viewBinding?.btnRecord?.text = when (currentMode) {
            Mode.ASK_ONLY -> "发送测试问题"
            else -> "开始录音"
        }
    }


    private fun startAction() {
        when (currentMode) {
            Mode.ASK_ONLY -> testAskOnly()
            else -> startRecording()
        }
    }

    private fun stopAndProcess() {
        when (currentMode) {
            Mode.VOICE_CHAT -> stopAndVoiceChat()
            Mode.STT_ONLY -> stopAndSttOnly()
            Mode.ASK_ONLY -> {}
        }
    }

    // ==================== 录音 ====================

    private fun startRecording() {
        if (!com.blankj.utilcode.util.PermissionUtils.isGranted(android.Manifest.permission.RECORD_AUDIO)) {
            addAiMessage("没有录音权限，请在主应用中授权")
            return
        }

        val context = viewBinding?.root?.context ?: return
        audioFile = File(context.cacheDir, "voice_${System.currentTimeMillis()}.wav")
        audioRecorder = AudioRecorder(audioFile!!)
        audioRecorder?.startRecording()
        isRecording = true
        viewBinding?.btnRecord?.text = "停止录音"
        addUserMessage("正在录音...")
    }

    private fun stopRecording(): File? {
        audioRecorder?.stopRecording()
        audioRecorder = null
        isRecording = false
        updateUI()
        return audioFile
    }

    // ==================== 语音对话模式 ====================

    private fun stopAndVoiceChat() {
        val file = stopRecording() ?: return
        viewBinding?.btnRecord?.isEnabled = false
        
        // 创建用户消息，后续更新
        val userMsgView = addUserMessage("识别中...")

        // 第一步：语音识别（立即返回结果）
        AiApi.speechToText(file, engine = "tencent") { text ->
            if (text.isNullOrBlank()) {
                userMsgView.text = "识别失败"
                viewBinding?.btnRecord?.isEnabled = true
                cleanup(file)
                return@speechToText
            }
            
            // 立即显示识别结果
            userMsgView.text = text
            scrollToBottom()
            
            // 第二步：AI回答（流式）
            askAiStream(text) { cleanup(file) }
        }
    }

    // ==================== 仅语音识别模式 ====================

    private fun stopAndSttOnly() {
        val file = stopRecording() ?: return
        viewBinding?.btnRecord?.isEnabled = false
        val userMsgView = addUserMessage("识别中...")

        AiApi.speechToText(file, engine = "tencent") { text ->
            // 立即显示结果
            userMsgView.text = text ?: "识别失败"
            viewBinding?.btnRecord?.isEnabled = true
            cleanup(file)
        }
    }

    // ==================== 仅AI问答模式 ====================

    private fun testAskOnly() {
        val testQuestion = "你好，请简单介绍一下你自己"
        addUserMessage(testQuestion)
        viewBinding?.btnRecord?.isEnabled = false
        askAiStream(testQuestion) {
            viewBinding?.btnRecord?.isEnabled = true
        }
    }

    // ==================== 通用方法 ====================

    private fun askAiStream(question: String, onDone: (() -> Unit)? = null) {
        val aiView = addAiMessage("AI思考中...")
        val response = StringBuilder()

        AiApi.askAiStream(
            question = question,
            onResponse = { chunk ->
                if (response.isEmpty()) aiView.text = ""
                response.append(chunk)
                aiView.text = response.toString()
                scrollToBottom()
            },
            onComplete = {
                viewBinding?.btnRecord?.isEnabled = true
                onDone?.invoke()
            },
            onError = { e ->
                aiView.text = "错误: ${e.message}"
                viewBinding?.btnRecord?.isEnabled = true
                onDone?.invoke()
            }
        )
    }

    private fun scrollToBottom() {
        viewBinding?.scrollView?.post {
            viewBinding?.scrollView?.fullScroll(View.FOCUS_DOWN)
        }
    }

    private fun addUserMessage(message: String): TextView {
        val context = viewBinding?.root?.context ?: throw IllegalStateException()
        val textView = TextView(context).apply {
            text = message
            background = ContextCompat.getDrawable(context, R.drawable.bg_2)
            setTextColor(ContextCompat.getColor(context, android.R.color.white))
            val p = (ScreenUtils.getScreenDensity() * 8).toInt()
            setPadding(p, p, p, p)
        }
        val lp = android.widget.LinearLayout.LayoutParams(
            android.widget.LinearLayout.LayoutParams.WRAP_CONTENT,
            android.widget.LinearLayout.LayoutParams.WRAP_CONTENT
        ).apply {
            gravity = android.view.Gravity.END
            topMargin = (ScreenUtils.getScreenDensity() * 8).toInt()
        }
        viewBinding?.llChatContainer?.addView(textView, lp)
        scrollToBottom()
        return textView
    }

    private fun addAiMessage(message: String): TextView {
        val context = viewBinding?.root?.context ?: throw IllegalStateException()
        val textView = TextView(context).apply {
            text = message
            background = ContextCompat.getDrawable(context, R.drawable.bg_3)
            setTextColor(ContextCompat.getColor(context, android.R.color.white))
            val p = (ScreenUtils.getScreenDensity() * 8).toInt()
            setPadding(p, p, p, p)
        }
        val lp = android.widget.LinearLayout.LayoutParams(
            android.widget.LinearLayout.LayoutParams.WRAP_CONTENT,
            android.widget.LinearLayout.LayoutParams.WRAP_CONTENT
        ).apply {
            gravity = android.view.Gravity.START
            topMargin = (ScreenUtils.getScreenDensity() * 8).toInt()
        }
        viewBinding?.llChatContainer?.addView(textView, lp)
        scrollToBottom()
        return textView
    }

    private fun cleanup(file: File?) {
        file?.delete()
    }
}
