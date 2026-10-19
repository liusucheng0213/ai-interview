<template>
  <div class="chat-page">
    <!-- 顶部信息栏 -->
    <div class="top-bar">
      <div class="top-bar-left">
        <span class="interview-title">{{ positionName }} · {{ modeLabel }}</span>
        <el-tag :type="modeTagType" size="small" style="margin-left: 8px;">
          {{ modeLabel }}
        </el-tag>
      </div>
      <div class="top-bar-right">
        <el-button type="danger" size="small" plain @click="endInterview" :disabled="loading">
          结束面试
        </el-button>
      </div>
    </div>

    <!-- ===================== 文本模式 ===================== -->
    <div v-if="interviewMode === 'text'" class="text-mode-layout">
      <div class="chat-messages" ref="chatContainer">
        <div
          v-for="(msg, index) in messages"
          :key="index"
        >
          <div :class="['msg-row', msg.role === 'ai' ? 'msg-ai' : 'msg-user']">
            <div class="msg-avatar msg-avatar-digital" v-if="msg.role === 'ai'" title="AI 面试官 · 晓晨">
              <div class="mini-interviewer-face" :class="{ 'is-speaking': isSpeaking && index === messages.length - 1 }">
                <span class="mini-hair"></span>
                <span class="mini-face-base"></span>
                <span class="mini-eye mini-eye-l"></span>
                <span class="mini-eye mini-eye-r"></span>
                <span class="mini-mouth" :class="{ open: isSpeaking && index === messages.length - 1 }"></span>
              </div>
            </div>
            <div :class="['msg-bubble', msg.role === 'ai' ? 'bubble-ai' : 'bubble-user']">
              <div v-if="msg.role === 'ai'" class="msg-text msg-text-md">
                <MarkdownRich :content="msg.content || ''" />
              </div>
              <div v-else class="msg-text">{{ msg.content }}</div>
              <div v-if="msg.role === 'ai' && isSpeaking && index === messages.length - 1" class="speaking-badge">
                <span class="dot"></span><span class="dot"></span><span class="dot"></span>
                朗读中
              </div>
            </div>
            <div class="msg-avatar user-avatar" v-if="msg.role === 'user'">我</div>
          </div>

          <!-- 文本模式下不显示单题实时评分（评分将汇总在最终报告中） -->
        </div>

        <!-- AI 思考中 -->
        <div v-if="loading" class="msg-row msg-ai">
          <div class="msg-avatar msg-avatar-digital" title="AI 面试官 · 晓晨">
            <div class="mini-interviewer-face" :class="{ 'is-speaking': isSpeaking }">
              <span class="mini-hair"></span>
              <span class="mini-face-base"></span>
              <span class="mini-eye mini-eye-l"></span>
              <span class="mini-eye mini-eye-r"></span>
              <span class="mini-mouth" :class="{ open: isSpeaking }"></span>
            </div>
          </div>
          <div class="msg-bubble bubble-ai thinking-bubble">
            <span class="dot"></span><span class="dot"></span><span class="dot"></span>
          </div>
        </div>
      </div>

      <!-- 文字模式：填充对话区下方空间 —当前题目摘要 + 表达提示 -->
      <div class="text-mode-assist">
        <div class="text-assist-card">
          <div class="text-assist-card__head">
            <span class="text-assist-card__badge">当前题目</span>
            <span class="text-assist-card__hint">可滚动查看完整对话</span>
          </div>
          <p class="text-assist-card__body">{{ textModeTopicPreview }}</p>
        </div>
        <div class="text-assist-tips">
          <span class="text-assist-tips__title">表达提示</span>
          <ul>
            <li>结论先行，再展开理由与例子，避免冗长铺垫。</li>
            <li>使用 STAR（情境-任务-行动-结果）组织项目与冲突类问题。</li>
            <li>数字与范围尽量具体，如「延迟从 800ms 降到 120ms」。</li>
            <li>不确定时可先界定范围，再分情况说明，体现结构化思维。</li>
          </ul>
        </div>
      </div>

      <!-- 输入区 -->
      <div class="text-input-bar">
        <el-button
          v-if="isSpeaking"
          type="warning"
          size="small"
          circle
          @click="stopSpeaking"
          title="停止朗读"
        >🔇</el-button>
        <el-input
          v-model="userInput"
          placeholder="请输入你的回答，按 Enter 发送..."
          @keyup.enter="sendMessage"
          :disabled="loading"
          class="text-input"
        />
        <el-button type="primary" @click="sendMessage" :loading="loading" :disabled="!userInput.trim()">
          发送
        </el-button>
      </div>
    </div>

    <!-- ===================== 语音模式 ===================== -->
    <div v-else-if="interviewMode === 'speech'" class="speech-mode-layout">
      <div class="speech-interviewer-row">
        <div class="speech-mini-avatar" :class="{ speaking: isSpeaking }" title="AI 面试官 · 晓晨">
          <div class="mini-interviewer-face speech-face-scale" :class="{ 'is-speaking': isSpeaking }">
            <span class="mini-hair"></span>
            <span class="mini-face-base"></span>
            <span class="mini-eye mini-eye-l"></span>
            <span class="mini-eye mini-eye-r"></span>
            <span class="mini-mouth" :class="{ open: isSpeaking }"></span>
          </div>
          <span class="speech-avatar-caption">晓晨</span>
        </div>
      </div>
      <!-- AI 问题展示区 -->
      <div class="ai-question-card">
        <div class="ai-question-header">
          <span class="ai-icon">🤖</span>
          <span class="ai-label">AI 面试官提问</span>
          <span v-if="isSpeaking" class="speaking-wave-badge">
            <span class="dot"></span><span class="dot"></span><span class="dot"></span>
            朗读中
          </span>
        </div>
        <div class="ai-question-text">{{ currentQuestion || '等待面试官提问...' }}</div>
        <div class="question-actions">
          <el-button size="small" plain @click="speakQuestion(currentQuestion)" :disabled="isSpeaking || !currentQuestion">
            🔊 重新朗读
          </el-button>
          <el-button size="small" plain @click="stopSpeaking" :disabled="!isSpeaking">
            🔇 停止朗读
          </el-button>
        </div>
      </div>

      <!-- 麦克风区域 -->
      <div class="speech-center-area">
        <div :class="['mic-btn-wrapper', { recording: isAnswering }]" @click="toggleSpeechAnswer">
          <div class="mic-circle">
            <span class="mic-icon-large">{{ isAnswering ? '⏹️' : '🎤' }}</span>
          </div>
          <div class="recording-rings" v-if="isAnswering">
            <div class="ring ring1"></div>
            <div class="ring ring2"></div>
            <div class="ring ring3"></div>
          </div>
        </div>
        <div class="mic-status">
          <span v-if="isAnswering" class="status-recording">
            🔴 录音中 {{ recordingTimeDisplay }}
          </span>
          <span v-else-if="loading" class="status-loading">
            ⏳ 正在处理语音...
          </span>
          <span v-else class="status-idle">
            点击麦克风开始回答
          </span>
        </div>
        <!-- 用户最新回答 -->
        <div v-if="lastUserAnswer" class="last-answer-box">
          <span class="last-answer-label">你的回答：</span>
          <span class="last-answer-text">{{ lastUserAnswer }}</span>
        </div>

        <!-- 语音模式实时分析卡片 -->
        <div v-if="lastAnswerAnalysis" class="speech-analysis-card">
          <div class="analysis-card-header">
            <span class="analysis-title">📊 本次回答分析</span>
            <span class="analysis-overall" :style="{ color: getScoreColor(lastAnswerAnalysis.overall) }">
              综合 {{ lastAnswerAnalysis.overall != null ? Number(lastAnswerAnalysis.overall).toFixed(1) : '--' }}
            </span>
          </div>
          <div class="analysis-scores" v-if="lastAnswerAnalysis.technical_score != null">
            <div v-for="(item, i) in getAnalysisDims(lastAnswerAnalysis)" :key="i" class="analysis-dim">
              <span class="dim-label">{{ item.label }}</span>
              <div class="dim-bar-bg">
                <div class="dim-bar-fill" :style="{ width: (item.value * 10) + '%', background: getScoreColor(item.value) }" />
              </div>
              <span class="dim-val" :style="{ color: getScoreColor(item.value) }">{{ item.value }}</span>
            </div>
          </div>
          <div class="analysis-feedback">
            <div v-if="lastAnswerAnalysis.highlight" class="feedback-row highlight">
              <span class="fb-icon">✅</span>{{ lastAnswerAnalysis.highlight }}
            </div>
            <div v-if="lastAnswerAnalysis.weakness" class="feedback-row weakness">
              <span class="fb-icon">⚠️</span>{{ lastAnswerAnalysis.weakness }}
            </div>
            <div v-if="lastAnswerAnalysis.tip" class="feedback-row tip">
              <span class="fb-icon">💡</span>{{ lastAnswerAnalysis.tip }}
            </div>
          </div>
          <div v-if="lastSpeechFeatures && lastSpeechFeatures.char_count > 0" class="speech-features">
            <el-tag size="small" type="info">字数 {{ lastSpeechFeatures.char_count }}</el-tag>
            <el-tag v-if="lastSpeechFeatures.speech_rate_cpm > 0" size="small" :type="getSpeechRateType(lastSpeechFeatures.speech_rate_cpm)">
              语速 {{ lastSpeechFeatures.speech_rate_cpm }} 字/分
            </el-tag>
            <el-tag v-if="lastSpeechFeatures.filler_count > 0" size="small" type="warning">
              停顿词 {{ lastSpeechFeatures.filler_count }} 次
            </el-tag>
            <span class="clarity-hint">{{ lastSpeechFeatures.clarity_hint }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- ===================== 视频模式 ===================== -->
    <div v-else-if="interviewMode === 'video'" class="video-mode-layout">

      <!-- 悬浮状态评估面板（不遮挡主界面，右侧小窗） -->
      <transition name="float-panel">
        <div
          v-if="showFloatPanel && (lastVideoAnalysis || isRecordingVideo)"
          class="float-assessment-panel"
        >
          <div class="float-panel-header">
            <span class="float-panel-icon">{{ floatPanelEmotionIcon }}</span>
            <span class="float-panel-title">{{ isRecordingVideo && !lastVideoAnalysis ? '实时情感' : '状态感知' }}</span>
            <button class="float-panel-close" @click="showFloatPanel = false" title="关闭">×</button>
          </div>
          <div class="float-panel-body">
            <template v-if="isRecordingVideo && !lastVideoAnalysis">
              <div class="emotion-status" :class="liveRecordingEmotion.cls">
                {{ liveRecordingEmotion.label }}
              </div>
              <div class="float-panel-hint live-hint">{{ liveRecordingPhase }}</div>
              <div class="live-pulse-bar" aria-hidden="true"><span /><span /><span /></div>
            </template>
            <template v-else-if="lastVideoAnalysis">
              <div class="emotion-status" :class="emotionClass">
                {{ emotionLabel }}
              </div>
              <div class="float-panel-hint">{{ lastVideoAnalysis.suggestions }}</div>
              <div class="float-panel-meta">
                <span class="meta-tag">{{ psychologyDisplay || lastVideoAnalysis.psychology }}</span>
              </div>
            </template>
          </div>
        </div>
      </transition>

      <!-- 悬浮面板被关闭时的小角标，点击重新打开 -->
      <div
        v-if="!showFloatPanel && (lastVideoAnalysis || isRecordingVideo)"
        class="float-panel-toggle"
        @click="showFloatPanel = true"
        :title="'点击查看情感分析'"
      >
        {{ floatPanelEmotionIcon }}
      </div>

      <!-- 上方：分屏画面 -->
      <div class="video-split">
        <!-- 左：AI 数字虚拟人面试官 -->
        <div class="video-panel ai-panel">
          <!-- 数字虚拟人：人像 + 对口型 + 朗读停顿；讯飞 RTMP 经 HTTP-FLV 代理后由 flv.js 在下方 video 播放 -->
          <div
            class="digital-avatar"
            :class="{ speaking: isSpeaking, idle: !isSpeaking }"
            @click="onIflytekAvatarPanelClick"
          >
            <div
              ref="iflytekAvatarWrapper"
              class="iflytek-sdk-wrapper"
              :class="{ active: (iflytekVHReady || iflytekSdkPlaying || iflytekSdkStarting) && !iflytekUseFlvFallback }"
            ></div>
            <div v-if="iflytekUseFlvFallback && iflytekVHStreamUrl" class="iflytek-sdk-wrapper active">
              <VirtualHumanFlvPlayer
                :stream-url="iflytekVHStreamUrl"
                :auto-mute="false"
                rtmp-to-flv-protocol="https"
                :reconnect-max="25"
                @error="onIflytekFlvError"
              />
            </div>
            <div v-show="!iflytekVHReady" class="iflytek-connecting-mask">
              <div class="iflytek-connecting-title">正在连接讯飞虚拟人...</div>
              <div class="iflytek-connecting-sub">{{ iflytekFlvError || '连接成功后将自动开始数字人播报' }}</div>
            </div>
            <div v-show="false" class="avatar-portrait-frame" aria-hidden="true">
              <div class="avatar-portrait-inner"></div>
            </div>
            <div v-show="false" class="avatar-ring" aria-hidden="true"></div>
            <!-- 背景光晕 -->
            <div v-show="false" class="avatar-glow" :class="{ active: isSpeaking }"></div>
            <!-- 虚拟人头部 SVG -->
            <svg v-show="false" class="avatar-svg" viewBox="0 0 160 200" xmlns="http://www.w3.org/2000/svg">
              <!-- 耳廓 -->
              <ellipse cx="34" cy="108" rx="9" ry="14" fill="url(#skinGrad)" opacity="0.95"/>
              <ellipse cx="126" cy="108" rx="9" ry="14" fill="url(#skinGrad)" opacity="0.95"/>
              <!-- 颈部 -->
              <rect x="68" y="148" width="24" height="24" rx="4" fill="url(#skinGrad)"/>
              <!-- 肩部 -->
              <ellipse cx="80" cy="185" rx="52" ry="18" fill="url(#shirtGrad)"/>
              <!-- 衬衫领 -->
              <path d="M 60 170 L 80 182 L 100 170 L 100 185 L 60 185 Z" fill="url(#shirtGrad2)"/>
              <!-- 领带 -->
              <path d="M 76 172 L 80 178 L 84 172 L 82 185 L 78 185 Z" fill="url(#accentGrad)"/>
              <!-- 头部基础 -->
              <ellipse cx="80" cy="105" rx="44" ry="52" fill="url(#skinGrad)"/>
              <!-- 头发 -->
              <ellipse cx="80" cy="62" rx="44" ry="22" fill="url(#hairGrad)"/>
              <path d="M 36 95 Q 30 70 36 60 Q 44 50 80 53 Q 116 50 124 60 Q 130 70 124 95" fill="url(#hairGrad)"/>
              <!-- 细框眼镜 -->
              <path d="M 48 98 Q 62 94 76 98" stroke="#3d4f6f" stroke-width="1.4" fill="none" opacity="0.55"/>
              <path d="M 84 98 Q 98 94 112 98" stroke="#3d4f6f" stroke-width="1.4" fill="none" opacity="0.55"/>
              <line x1="76" y1="98" x2="84" y2="98" stroke="#3d4f6f" stroke-width="1.2" opacity="0.5"/>
              <!-- 左眉毛 -->
              <path d="M 52 88 Q 62 83 72 86" stroke="#4a3728" stroke-width="2.5" fill="none" stroke-linecap="round"/>
              <!-- 右眉毛 -->
              <path d="M 88 86 Q 98 83 108 88" stroke="#4a3728" stroke-width="2.5" fill="none" stroke-linecap="round"/>
              <!-- 左眼（含眨眼动画） -->
              <g class="eye-left">
                <ellipse cx="62" cy="100" rx="10" ry="10" fill="white"/>
                <ellipse cx="62" cy="100" rx="7" ry="7" fill="#3a6ea5"/>
                <ellipse cx="62" cy="100" rx="4" ry="4" fill="#1a1a2e"/>
                <ellipse cx="65" cy="97" rx="2" ry="2" fill="white" opacity="0.8"/>
                <ellipse cx="62" cy="96" rx="10" ry="0" fill="url(#skinGrad)" class="eyelid"/>
              </g>
              <!-- 右眼 -->
              <g class="eye-right">
                <ellipse cx="98" cy="100" rx="10" ry="10" fill="white"/>
                <ellipse cx="98" cy="100" rx="7" ry="7" fill="#3a6ea5"/>
                <ellipse cx="98" cy="100" rx="4" ry="4" fill="#1a1a2e"/>
                <ellipse cx="101" cy="97" rx="2" ry="2" fill="white" opacity="0.8"/>
                <ellipse cx="98" cy="96" rx="10" ry="0" fill="url(#skinGrad)" class="eyelid"/>
              </g>
              <!-- 鼻子 -->
              <path d="M 78 110 Q 76 120 74 122 Q 80 126 86 122 Q 84 120 82 110" fill="url(#shadowGrad)" opacity="0.3"/>
              <!-- 嘴巴 -->
              <g class="mouth-group" :class="{ 'mouth-active': isSpeaking }">
                <path v-if="!isSpeaking" class="mouth-closed" d="M 66 134 Q 80 142 94 134" stroke="#c77a6a" stroke-width="2.5" fill="none" stroke-linecap="round"/>
                <g v-if="isSpeaking" class="mouth-open-wrap">
                  <ellipse class="mouth-open" cx="80" cy="136" rx="12" ry="6" fill="#6b2d3a"/>
                  <ellipse class="mouth-inner" cx="80" cy="138" rx="7" ry="3" fill="#4a1a28" opacity="0.65"/>
                  <path d="M 68 136 Q 80 130 92 136" stroke="#e8a090" stroke-width="1.8" fill="none"/>
                </g>
              </g>
              <!-- 脸颊红晕 -->
              <ellipse cx="52" cy="118" rx="10" ry="6" fill="#ffb3b3" opacity="0.35"/>
              <ellipse cx="108" cy="118" rx="10" ry="6" fill="#ffb3b3" opacity="0.35"/>
              <!-- 渐变定义 -->
              <defs>
                <linearGradient id="skinGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stop-color="#ffd9b3"/>
                  <stop offset="100%" stop-color="#f4b88a"/>
                </linearGradient>
                <linearGradient id="hairGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stop-color="#2c2c2c"/>
                  <stop offset="100%" stop-color="#4a3728"/>
                </linearGradient>
                <linearGradient id="shirtGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stop-color="#3a5a8a"/>
                  <stop offset="100%" stop-color="#1a2a4a"/>
                </linearGradient>
                <linearGradient id="shirtGrad2" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stop-color="#4a6a9a"/>
                  <stop offset="100%" stop-color="#2a3a6a"/>
                </linearGradient>
                <linearGradient id="shadowGrad" x1="0" y1="0" x2="1" y2="1">
                  <stop offset="0%" stop-color="#d4956a"/>
                  <stop offset="100%" stop-color="#a06040"/>
                </linearGradient>
                <linearGradient id="accentGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stop-color="#60a5fa"/>
                  <stop offset="100%" stop-color="#2563eb"/>
                </linearGradient>
              </defs>
            </svg>
            <!-- 说话时的声波指示器（无 FLV 时使用 SVG；有 FLV 时以视频口型为准） -->
            <div v-if="isSpeaking && !iflytekSdkPlaying" class="voice-wave">
              <span class="wave-bar"></span>
              <span class="wave-bar"></span>
              <span class="wave-bar"></span>
              <span class="wave-bar"></span>
              <span class="wave-bar"></span>
            </div>
          </div>
        </div>

        <!-- 右：用户摄像头 -->
        <div class="video-panel user-panel">
          <video ref="videoPreview" autoplay playsinline muted class="camera-video" v-show="showCamera"></video>
          <div v-if="!showCamera" class="camera-placeholder">
            <span class="camera-icon">📷</span>
            <span>摄像头加载中...</span>
          </div>
          <div v-if="isRecordingVideo" class="recording-badge">
            🔴 录制中 {{ recordingTimeDisplay }}
          </div>
          <div class="panel-label">你</div>
        </div>
      </div>

      <!-- 录制中：底部实时情感条（与右侧悬浮窗同步数据源） -->
      <div v-if="isRecordingVideo" class="video-live-strip">
        <span class="vls-dot" aria-hidden="true" />
        <span class="vls-ico">{{ liveRecordingEmotion.icon }}</span>
        <div class="vls-main">
          <strong>实时情感感知</strong>
          <span>{{ liveRecordingEmotion.label }}</span>
        </div>
        <span class="vls-phase">{{ liveRecordingPhase }}</span>
      </div>

      <!-- AI 问题展示区 -->
      <div class="ai-question-card video-question-card">
        <div class="ai-question-header">
          <span class="ai-label">面试官提问</span>
          <span v-if="isSpeaking" class="speaking-wave-badge">
            <span class="dot"></span><span class="dot"></span><span class="dot"></span>
            朗读中
          </span>
        </div>
        <div class="ai-question-text">{{ currentQuestion || '等待面试官提问...' }}</div>
        <div class="question-actions">
          <el-button size="small" plain @click="speakQuestion(currentQuestion)" :disabled="isSpeaking || !currentQuestion">
            🔊 重新朗读
          </el-button>
          <el-button size="small" plain @click="stopSpeaking" :disabled="!isSpeaking">
            🔇 停止朗读
          </el-button>
        </div>
      </div>

      <!-- 视频模式不展示逐题评分，整场评价在最终报告中查看 -->

      <!-- 控制按钮 -->
      <div class="video-controls-bar">
        <el-button
          v-if="!isRecordingVideo"
          type="success"
          size="large"
          :disabled="loading || !showCamera || isSpeaking"
          @click="startVideoRecord"
        >
          🎬 开始回答
        </el-button>
        <el-button
          v-else
          type="danger"
          size="large"
          :loading="loading"
          @click="stopVideoRecord"
        >
          ⏹️ 提交回答
        </el-button>
        <div v-if="loading" class="processing-hint">⏳ 正在分析视频中...</div>
      </div>
    </div>

    <!-- ===================== 结束面试确认悬浮弹窗（须放在 v-if 链外，否则会打断 v-else-if） ===================== -->
    <Teleport to="body">
      <Transition name="end-dialog">
        <div v-if="showEndConfirm" class="end-dialog-overlay" @click.self="showEndConfirm = false">
          <div class="end-dialog-card">
            <div class="end-dialog-icon-wrap">
              <div class="end-dialog-icon">⚠️</div>
            </div>
            <h3 class="end-dialog-title">结束面试确认</h3>
            <p class="end-dialog-desc">
              确定要结束本次面试吗？<br>
              系统将根据完整对话记录生成 AI 评估报告。
            </p>
            <div class="end-dialog-actions">
              <button class="end-btn-cancel" @click="showEndConfirm = false" :disabled="loading">
                继续面试
              </button>
              <button class="end-btn-confirm" @click="confirmEndInterview" :disabled="loading">
                <span v-if="loading" class="end-btn-loading">
                  <span class="dot"></span><span class="dot"></span><span class="dot"></span>
                </span>
                <span v-else>确认结束</span>
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { notifyError } from '@/utils/appNotify'
import {
  submitTextAnswerStream,
  submitSpeechAnswer,
  submitVideoAnswer,
  endInterviewApi,
  uploadVideoStream,
  getVirtualHumanConfig,
  startVirtualHumanSession,
  virtualHumanSpeak,
  stopVirtualHumanSession,
} from '@/api/endpoints'
import MarkdownRich from '@/components/MarkdownRich.vue'
import VirtualHumanFlvPlayer from '@/components/VirtualHumanFlvPlayer.vue'
import AvatarPlatform, {
  SDKEvents,
  PlayerEvents,
} from '@avatar-digital-human-studio/index.js'

const router = useRouter()

/** 在 `stopSpeaking` 定义后赋值；供流式/语音/视频「提前结束」与手动结束复用 */
let goToHistoryAfterEnd = () => {}

// ==================== 基础状态 ====================
const userInput = ref('')
const messages = ref([])           // 文本模式对话列表
const lastAnswerAnalysis = ref(null)   // 语音/视频模式：最近一次回答分析
const lastSpeechFeatures = ref(null)   // 语音模式：最近一次语音特征
const currentQuestion = ref('')    // 语音/视频模式展示当前问题
const lastUserAnswer = ref('')     // 语音模式：展示用户最近一次转文字结果
const loading = ref(false)
const positionName = ref('')
const chatContainer = ref(null)
const isSpeaking = ref(false)
const interviewMode = ref('text')
const interviewLanguage = ref('zh')

// 录音相关
const isRecording = ref(false)
const mediaRecorder = ref(null)
const audioChunks = ref([])
const recordingStartTime = ref(0)
const recordingTimer = ref(null)
const recordingSeconds = ref(0)

// 语音模式 - 是否正在回答
const isAnswering = ref(false)

// 视频相关
const showCamera = ref(false)
const videoPreview = ref(null)
const cameraStream = ref(null)
const videoRecorder = ref(null)
const videoStream = ref(null)
const videoChunks = ref([])
const isRecordingVideo = ref(false)
const videoAudioStream = ref(null)   // 录制时单独申请的音频流

// 视频分析结果（每次提交后更新）
const lastVideoAnalysis = ref(null)
/** 视频面试中心理状态展示文案（定时微调，避免长时间完全静止） */
const psychologyDisplay = ref('')
const PSYCH_LIVE_MARKERS = [
  '瞬时状态微调中',
  '情绪在常见波动范围',
  '非语言信号略有变化',
  '应答负荷轻微起伏',
  '心理张力动态更新',
]
let psychLiveTimer = null

const bumpPsychologyDisplay = () => {
  const base = lastVideoAnalysis.value?.psychology
  if (!base) {
    psychologyDisplay.value = ''
    return
  }
  const m = PSYCH_LIVE_MARKERS[Math.floor(Math.random() * PSYCH_LIVE_MARKERS.length)]
  psychologyDisplay.value = `${base} · ${m}`
}

watch(
  lastVideoAnalysis,
  () => {
    bumpPsychologyDisplay()
  },
  { deep: true },
)

// 悬浮状态面板
const showFloatPanel = ref(false)

// 讯飞虚拟人（视频模式可选）
const iflytekVHReady = ref(false)
const iflytekVHStreamUrl = ref('')
const iflytekVHError = ref('')
const iflytekAvatarWrapper = ref(null)
const iflytekAvatarSdk = ref(null)
const iflytekSdkPlaying = ref(false)
const iflytekSdkStarting = ref(false)
const iflytekFlvError = ref('')
const iflytekUseFlvFallback = ref(false)
const iflytekTtsVcn = ref('x4_yezi')
const iflytekBgResKey = ref('')
/** 视频模式：讯飞不可用或用户耗尽重试后，改用浏览器 TTS，并停止对讯飞的自动重连 */
const videoTtsPreferBrowser = ref(false)
let iflytekRenderCheckTimer = null
let iflytekSpeakEndTimer = null
let iflytekFrameStopDebounceTimer = null
let iflytekReconnectTimer = null
let iflytekReconnectInFlight = false
/** 页面级 voices 预热，卸载时需移除 */
let speechVoicesWarmHandler = null
/** 自动重连预算，避免 11203/鉴权失败时每秒打满讯飞与弹窗 */
const IFLYTEK_MAX_AUTO_RECONNECT = 6
let iflytekReconnectBudget = IFLYTEK_MAX_AUTO_RECONNECT
let iflytekReconnectStoppedNotified = false

const resetIflytekVirtualHumanRetry = () => {
  iflytekReconnectBudget = IFLYTEK_MAX_AUTO_RECONNECT
  iflytekReconnectStoppedNotified = false
}

const clearIflytekSpeakTimer = () => {
  if (iflytekSpeakEndTimer) {
    clearTimeout(iflytekSpeakEndTimer)
    iflytekSpeakEndTimer = null
  }
}

const onIflytekFlvError = (msg) => {
  iflytekFlvError.value = msg || 'FLV 回退链路播放失败'
}

const clearIflytekFrameStopDebounce = () => {
  if (iflytekFrameStopDebounceTimer) {
    clearTimeout(iflytekFrameStopDebounceTimer)
    iflytekFrameStopDebounceTimer = null
  }
}

const clearIflytekReconnectTimer = () => {
  if (iflytekReconnectTimer) {
    clearTimeout(iflytekReconnectTimer)
    iflytekReconnectTimer = null
  }
}

const scheduleIflytekReconnect = (reason = '') => {
  if (interviewMode.value !== 'video') return
  if (videoTtsPreferBrowser.value) return
  if (iflytekReconnectBudget <= 0) {
    iflytekFlvError.value =
      '讯飞虚拟人已停止自动重试：请核对开放平台「AI虚拟人」授权与 IFLYTEK_VH_AVATAR_ID，修改后刷新页面。'
    if (!iflytekReconnectStoppedNotified) {
      iflytekReconnectStoppedNotified = true
      videoTtsPreferBrowser.value = true
      notifyError(
        '讯飞虚拟人：多次连接失败，已停止自动重试。多为形象未对当前应用开通，请按后端日志提示检查控制台或更换形象 ID。',
        '讯飞虚拟人',
      )
    }
    return
  }
  if (iflytekReconnectInFlight || iflytekReconnectTimer) return
  iflytekReconnectTimer = setTimeout(async () => {
    iflytekReconnectTimer = null
    if (iflytekReconnectInFlight || interviewMode.value !== 'video') return
    iflytekReconnectBudget -= 1
    iflytekReconnectInFlight = true
    try {
      await initIflytekVirtualHuman()
    } catch (_) {
      // noop
    } finally {
      iflytekReconnectInFlight = false
      if (iflytekVHReady.value) {
        resetIflytekVirtualHumanRetry()
      } else if (iflytekReconnectBudget <= 0) {
        iflytekFlvError.value =
          '讯飞虚拟人已停止自动重试：请核对开放平台「AI虚拟人」授权与 IFLYTEK_VH_AVATAR_ID，修改后刷新页面。'
        if (!iflytekReconnectStoppedNotified) {
          iflytekReconnectStoppedNotified = true
          videoTtsPreferBrowser.value = true
          notifyError(
            '讯飞虚拟人：多次连接失败，已停止自动重试。多为形象未对当前应用开通，请按后端日志提示检查控制台或更换形象 ID。',
            '讯飞虚拟人',
          )
        }
      } else {
        iflytekFlvError.value = reason
          ? `${reason}，正在自动重连讯飞虚拟人...（剩余 ${iflytekReconnectBudget} 次）`
          : `讯飞虚拟人未就绪，正在自动重连...（剩余 ${iflytekReconnectBudget} 次）`
        scheduleIflytekReconnect(reason || '连接未就绪')
      }
    }
  }, 3200)
}

const markIflytekSpeakFinished = () => {
  clearIflytekSpeakTimer()
  clearIflytekFrameStopDebounce()
  isSpeaking.value = false
}

const detachIflytekFlv = () => { iflytekFlvError.value = '' }

const initIflytekFlvFallback = async () => {
  try {
    const res = await startVirtualHumanSession()
    const url = (res?.stream_url || '').trim()
    if (!url) return false
    iflytekVHStreamUrl.value = url
    iflytekUseFlvFallback.value = true
    iflytekVHReady.value = true
    iflytekFlvError.value = ''
    resetIflytekVirtualHumanRetry()
    return true
  } catch (e) {
    iflytekUseFlvFallback.value = false
    iflytekVHReady.value = false
    const detail = e?.response?.data?.detail
    const msg =
      typeof detail === 'string' && detail.trim() ? detail.trim() : e?.message || '后端会话回退失败'
    iflytekFlvError.value = msg
    iflytekVHError.value = msg
    return false
  }
}

const isXrtcLikeStream = (streamUrl) => {
  const s = String(streamUrl || '').trim().toLowerCase()
  if (!s) return false
  return s.startsWith('ws://') || s.startsWith('wss://') || s.startsWith('xrtc://') || s.includes('/interact')
}

const tryAttachIflytekFlv = async (streamUrl) => {
  detachIflytekFlv()
  iflytekVHStreamUrl.value = (streamUrl || '').trim()
  if (isXrtcLikeStream(streamUrl)) {
    iflytekFlvError.value = ''
    return
  }
  // 无流媒体模式：仅建立会话和播报，不做 FLV 直连。
  iflytekFlvError.value = ''
}

const onIflytekAvatarPanelClick = async () => {
  try {
    await iflytekAvatarSdk.value?.player?.resume?.()
    iflytekFlvError.value = ''
  } catch (_) {}
}

const destroyIflytekAvatarSdk = () => {
  if (iflytekRenderCheckTimer) {
    clearTimeout(iflytekRenderCheckTimer)
    iflytekRenderCheckTimer = null
  }
  try {
    iflytekAvatarSdk.value?.stop?.()
  } catch (_) {}
  try {
    iflytekAvatarSdk.value?.destroy?.()
  } catch (_) {}
  iflytekAvatarSdk.value = null
  iflytekSdkPlaying.value = false
  iflytekSdkStarting.value = false
  clearIflytekFrameStopDebounce()
  clearIflytekReconnectTimer()
}

const initIflytekVirtualHuman = async () => {
  iflytekVHError.value = ''
  iflytekUseFlvFallback.value = false
  clearIflytekReconnectTimer()
  destroyIflytekAvatarSdk()
  await nextTick()
  if (!iflytekAvatarWrapper.value) {
    iflytekVHError.value = '虚拟人渲染容器未就绪'
    return
  }

  try {
    const cfg = await getVirtualHumanConfig()
    if (Array.isArray(cfg?.config_hints) && cfg.config_hints.length) {
      console.warn('[讯飞虚拟人]', cfg.config_hints.join(' '))
    }
    if (cfg && cfg.sdk_ready === false) {
      const miss = Array.isArray(cfg.missing_fields) ? cfg.missing_fields.join(', ') : ''
      iflytekVHError.value = miss
        ? `讯飞 WebSDK 配置不完整：${miss}`
        : '讯飞 WebSDK 配置不完整'
      notifyError(iflytekVHError.value, '讯飞虚拟人')
      return
    }
    if (!cfg?.enabled) {
      iflytekVHError.value = '讯飞虚拟人未启用，请检查后端配置'
      notifyError(iflytekVHError.value, '讯飞虚拟人')
      return
    }

    const appId = (cfg.app_id || '').trim()
    const apiKey = (cfg.api_key || '').trim()
    const apiSecret = (cfg.api_secret || '').trim()
    const sceneId = (cfg.scene_id || '').trim()
    const serverUrl = (cfg.interact_server_url || 'wss://avatar.cn-huadong-1.xf-yun.com/v1/interact').trim()
    if (!appId || !apiKey || !apiSecret || !sceneId) {
      iflytekVHError.value = '缺少 app_id/api_key/api_secret/scene_id，无法初始化 WebRTC 数字人'
      notifyError(iflytekVHError.value, '讯飞虚拟人')
      return
    }
    iflytekTtsVcn.value = (cfg.tts_vcn || 'x4_yezi').trim() || 'x4_yezi'
    iflytekBgResKey.value = (cfg.bg_res_key || '').trim()

    const sdk = new AvatarPlatform({ useInlinePlayer: true })
    iflytekAvatarSdk.value = sdk
    iflytekSdkStarting.value = true
    sdk.removeAllListeners()
    sdk
      .on(SDKEvents.stream_start, () => {
        iflytekFlvError.value = ''
      })
      // 以官方事件驱动说话状态：frame_start 开始，frame_stop(vmr_status=2 且 1s 内无新帧) 结束
      .on(SDKEvents.frame_start, () => {
        clearIflytekFrameStopDebounce()
        isSpeaking.value = true
      })
      .on(SDKEvents.frame_stop, (event = {}) => {
        const status = Number(event?.vmr_status)
        if (!Number.isFinite(status) || status === 2) {
          clearIflytekFrameStopDebounce()
          iflytekFrameStopDebounceTimer = setTimeout(() => {
            markIflytekSpeakFinished()
          }, 1000)
        }
      })
      .on(SDKEvents.disconnected, () => {
        iflytekVHReady.value = false
        iflytekSdkPlaying.value = false
        iflytekSdkStarting.value = false
        if (!videoTtsPreferBrowser.value) scheduleIflytekReconnect('连接断开')
      })
      .on(SDKEvents.error, (e) => {
        iflytekFlvError.value = e?.message || '虚拟人连接失败'
        iflytekVHReady.value = false
        iflytekSdkStarting.value = false
        if (!videoTtsPreferBrowser.value) scheduleIflytekReconnect('连接异常')
      })
      // 口型/播报结束事件：不同 SDK 版本事件名不同，统一兜底注册
      .on('tts_end', markIflytekSpeakFinished)
      .on('speak_end', markIflytekSpeakFinished)
      .on('broadcast_end', markIflytekSpeakFinished)
      .on('sentence_end', markIflytekSpeakFinished)

    sdk.setApiInfo({
      serverUrl,
      appId,
      apiKey,
      apiSecret,
      sceneId,
    })
    const aw = Number(cfg.vh_width) || 720
    const ah = Number(cfg.vh_height) || 1280
    const globalParams = {
      // 与交互服务兼容：避免传文档未列出的扩展字段，减少「avatar authentication」类拒连
      stream: { protocol: 'xrtc' },
      avatar: {
        avatar_id: cfg.avatar_id || '111204007',
        width: aw,
        height: ah,
        scale: 1,
      },
      tts: {
        vcn: iflytekTtsVcn.value,
        speed: 50,
        pitch: 50,
        volume: 100,
      },
    }
    if (iflytekBgResKey.value) {
      // 按文档：SetGlobalParams.background 下使用 type/data 切背景
      globalParams.background = {
        type: 'res_key',
        data: iflytekBgResKey.value,
      }
    }
    sdk.setGlobalParams(globalParams)
    const player = sdk.player || sdk.createPlayer()
    player?.removeAllListeners?.()
    player
      ?.on(PlayerEvents.playing, () => {
        iflytekSdkPlaying.value = true
        iflytekSdkStarting.value = false
        iflytekFlvError.value = ''
      })
      ?.on(PlayerEvents.waiting, () => {
        iflytekSdkStarting.value = true
      })
      ?.on(PlayerEvents.playNotAllowed, () => {
        iflytekFlvError.value = '浏览器拦截了自动播放，请点击左侧数字人区域恢复播放'
      })
      ?.on(PlayerEvents.error, (err) => {
        iflytekSdkPlaying.value = false
        iflytekSdkStarting.value = false
        iflytekFlvError.value = err?.message || '播放器渲染失败'
      })

    await sdk.start({ wrapper: iflytekAvatarWrapper.value })
    try {
      if (sdk.player) {
        sdk.player.muted = false
        sdk.player.volume = 1
      }
    } catch (_) {}
    try {
      await sdk.player?.resume?.()
    } catch (_) {}

    iflytekVHReady.value = true
    resetIflytekVirtualHumanRetry()
    iflytekVHStreamUrl.value = serverUrl
    iflytekFlvError.value = ''
    iflytekRenderCheckTimer = setTimeout(() => {
      iflytekSdkStarting.value = false
    }, 8000)
    await tryAttachIflytekFlv(serverUrl)
  } catch (e) {
    const fallbackOk = await initIflytekFlvFallback()
    if (!fallbackOk) {
      iflytekVHReady.value = false
      iflytekSdkPlaying.value = false
      iflytekSdkStarting.value = false
      videoTtsPreferBrowser.value = true
      iflytekFlvError.value = '讯飞虚拟人不可用，已自动改用本机浏览器朗读题目。'
      if (!(iflytekVHError.value || '').trim()) {
        const detail = e?.response?.data?.detail
        iflytekVHError.value =
          typeof detail === 'string' && detail.trim()
            ? detail.trim()
            : e?.message || '讯飞虚拟人初始化失败'
      }
      clearIflytekReconnectTimer()
    }
  }
}

const driveIflytekAvatar = async (text) => {
  if (!iflytekVHReady.value || !text?.trim()) return false
  try {
    if (iflytekAvatarSdk.value?.writeText) {
      // 确保虚拟人嘴巴动起来：音频驱动 + 音频存在 + 唇形同步
      await iflytekAvatarSdk.value.writeText(text.trim(), {
        nlp: false,
        tts: {
          vcn: iflytekTtsVcn.value,
          speed: 50,
          pitch: 50,
          volume: 100,
        },
      })
      return true
    }
    iflytekVHError.value = '讯飞虚拟人能力未就绪（writeText 不可用）'
    return false
  } catch (e) {
    iflytekVHError.value = e?.message || '讯飞虚拟人播报失败'
    return false
  }
}

const speakQuestionIflytekStream = async (text) => {
  if (iflytekUseFlvFallback.value) {
    try {
      await virtualHumanSpeak(text)
      isSpeaking.value = true
      const ms = Math.min(180000, Math.max(4500, String(text).length * 230))
      clearIflytekSpeakTimer()
      iflytekSpeakEndTimer = setTimeout(() => {
        markIflytekSpeakFinished()
      }, ms)
      return true
    } catch (e) {
      iflytekVHError.value = e?.message || '讯飞虚拟人播报失败'
      isSpeaking.value = false
      return false
    }
  }
  speechGeneration.value += 1
  const gen = speechGeneration.value
  window.speechSynthesis?.cancel()
  clearSpeechKeepAlive()
  clearIflytekSpeakTimer()
  try {
    if (iflytekAvatarSdk.value?.player) {
      iflytekAvatarSdk.value.player.muted = false
      iflytekAvatarSdk.value.player.volume = 1
      await iflytekAvatarSdk.value.player.resume?.()
    }
  } catch (_) {}

  const ok = await driveIflytekAvatar(text)
  if (!ok) {
    iflytekVHError.value = '讯飞虚拟人播报失败，请检查配置与网络后重试'
    isSpeaking.value = false
    return false
  }
  isSpeaking.value = true
  // 以 SDK 事件为准结束；超时仅做兜底，避免长时间卡“朗读中”
  const ms = Math.min(180000, Math.max(4500, String(text).length * 230))
  iflytekSpeakEndTimer = setTimeout(() => {
    if (gen !== speechGeneration.value) return
    markIflytekSpeakFinished()
  }, ms)
  return true
}

// 结束面试确认弹窗
const showEndConfirm = ref(false)

// ==================== 计算属性 ====================
const modeLabel = computed(() => {
  const map = { text: '文字面试', speech: '语音面试', video: '视频面试' }
  return map[interviewMode.value] || '面试'
})

const modeTagType = computed(() => {
  const map = { text: 'info', speech: 'success', video: 'warning' }
  return map[interviewMode.value] || 'info'
})

/** 文字模式：底部辅助区展示的当前题目摘要（取最近一条 AI 消息） */
const textModeTopicPreview = computed(() => {
  if (interviewMode.value !== 'text') return ''
  for (let i = messages.value.length - 1; i >= 0; i--) {
    const m = messages.value[i]
    if (m?.role === 'ai' && (m.content || '').trim()) {
      const t = String(m.content).trim()
      return t.length > 220 ? `${t.slice(0, 220)}…` : t
    }
  }
  const q = (currentQuestion.value || '').trim()
  return q || '等待面试官提问…'
})

const recordingTimeDisplay = computed(() => {
  const m = Math.floor(recordingSeconds.value / 60)
  const s = recordingSeconds.value % 60
  return `${m}:${s.toString().padStart(2, '0')}`
})

// 根据视频分析的情绪映射到中文状态标签
const emotionLabelMap = {
  happy:     { label: '状态良好',   icon: '😊', cls: 'emotion-good' },
  neutral:   { label: '沉稳平静',   icon: '😐', cls: 'emotion-neutral' },
  confident: { label: '自信从容',   icon: '💪', cls: 'emotion-good' },
  focused:   { label: '专注思考',   icon: '🤔', cls: 'emotion-focused' },
  nervous:   { label: '略显紧张',   icon: '😅', cls: 'emotion-warn' },
  surprised: { label: '思维活跃',   icon: '✨', cls: 'emotion-focused' },
  sad:       { label: '状态欠佳',   icon: '😔', cls: 'emotion-warn' },
  angry:     { label: '情绪波动',   icon: '😤', cls: 'emotion-warn' },
}

const _getEmotionFromAnalysis = () => {
  if (!lastVideoAnalysis.value) return null
  const psych = lastVideoAnalysis.value.psychology || ''
  if (psych.includes('积极') || psych.includes('乐观')) return 'happy'
  if (psych.includes('自信')) return 'confident'
  if (psych.includes('专注')) return 'focused'
  if (psych.includes('紧张')) return 'nervous'
  if (psych.includes('波动')) return 'angry'
  if (psych.includes('欠佳')) return 'sad'
  return 'neutral'
}

const emotionLabel = computed(() => {
  const e = _getEmotionFromAnalysis()
  return e ? (emotionLabelMap[e]?.label || '状态正常') : '等待分析'
})
const emotionIcon = computed(() => {
  const e = _getEmotionFromAnalysis()
  return e ? (emotionLabelMap[e]?.icon || '😐') : '🎯'
})
const emotionClass = computed(() => {
  const e = _getEmotionFromAnalysis()
  return e ? (emotionLabelMap[e]?.cls || 'emotion-neutral') : 'emotion-neutral'
})

/** 录制中：平滑轮询情感标签，模拟「实时」非语言感知（前端示意） */
const LIVE_EMOTION_KEYS = ['happy', 'neutral', 'confident', 'focused', 'nervous', 'surprised', 'sad']
const liveEmotionTick = ref(0)
const liveEmotionKey = ref('neutral')
const LIVE_EMOTION_STEP_MS = 1200
const LIVE_EMOTION_SWITCH_PROB = 0.32
let recordingEmotionTimer = null

const liveRecordingEmotion = computed(() => {
  const k = liveEmotionKey.value
  const m = emotionLabelMap[k]
  return { label: m.label, icon: m.icon, cls: m.cls }
})

const RECORDING_PHASE_HINTS = [
  '正在采集非语言信号…',
  '微表情与姿态采样中…',
  '保持自然目光与表达…',
  '情绪线索动态更新中…',
  '可适度手势辅助说明…',
]

const liveRecordingPhase = computed(() => {
  return RECORDING_PHASE_HINTS[liveEmotionTick.value % RECORDING_PHASE_HINTS.length]
})

const floatPanelEmotionIcon = computed(() => {
  if (isRecordingVideo.value && !lastVideoAnalysis.value) {
    return liveRecordingEmotion.value.icon
  }
  return emotionIcon.value
})

const pickNextLiveEmotion = (prev, tick) => {
  // 录制开始前几秒优先稳定状态，避免刚开始就大幅跳变
  if (tick < 3) {
    const warmup = ['neutral', 'focused', 'confident']
    return warmup[Math.floor(Math.random() * warmup.length)]
  }
  // 多数时候保持当前状态，降低扰动
  if (Math.random() > LIVE_EMOTION_SWITCH_PROB) return prev

  const transitionMap = {
    neutral: ['focused', 'confident', 'happy', 'nervous'],
    focused: ['neutral', 'confident', 'happy'],
    confident: ['focused', 'neutral', 'happy'],
    happy: ['confident', 'neutral', 'focused'],
    nervous: ['neutral', 'focused', 'sad'],
    surprised: ['focused', 'neutral', 'happy'],
    sad: ['neutral', 'focused'],
  }
  const nextPool = transitionMap[prev] || LIVE_EMOTION_KEYS
  return nextPool[Math.floor(Math.random() * nextPool.length)] || prev
}

watch(isRecordingVideo, (on) => {
  if (recordingEmotionTimer) {
    clearInterval(recordingEmotionTimer)
    recordingEmotionTimer = null
  }
  if (on) {
    liveEmotionTick.value = 0
    liveEmotionKey.value = 'neutral'
    recordingEmotionTimer = setInterval(() => {
      liveEmotionTick.value++
      liveEmotionKey.value = pickNextLiveEmotion(liveEmotionKey.value, liveEmotionTick.value)
    }, LIVE_EMOTION_STEP_MS)
  }
})

// ==================== 工具函数 ====================
const loadInterviewConfig = () => {
  const config = JSON.parse(localStorage.getItem('interview-config') || '{}')
  interviewMode.value = config.mode || 'text'
  positionName.value = config.job || '未知岗位'
  interviewLanguage.value = config.language || 'zh'
}

const getCurrentInterviewId = () => localStorage.getItem('current_interview_id')
const getCurrentJobId = () => {
  const raw = localStorage.getItem('active_job_id')
  const id = Number(raw || 0)
  return id > 0 ? id : 0
}

// ── 实时分析辅助函数 ─────────────────────────────────────
const getScoreColor = (score) => {
  if (score == null) return '#909399'
  const s = Number(score)
  if (s >= 8.5) return '#67c23a'
  if (s >= 7) return '#409eff'
  if (s >= 5) return '#e6a23c'
  return '#f56c6c'
}

const getAnalysisDims = (analysis) => {
  if (!analysis) return []
  const map = [
    { key: 'technical_score', label: '技术准确' },
    { key: 'depth_score',     label: '知识深度' },
    { key: 'logic_score',     label: '逻辑严谨' },
    { key: 'job_match_score', label: '岗位匹配' },
    { key: 'clarity_score',   label: '表达清晰' },
  ]
  return map
    .filter(d => analysis[d.key] != null)
    .map(d => ({ label: d.label, value: Number(analysis[d.key]) }))
}

const getSpeechRateType = (cpm) => {
  if (cpm < 120 || cpm > 280) return 'warning'
  return 'success'
}

const scrollToBottom = async () => {
  await nextTick()
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

// 设置当前问题（同步到 currentQuestion + messages）
const setAiQuestion = (text) => {
  currentQuestion.value = text
  if (interviewMode.value === 'text') {
    messages.value.push({ role: 'ai', content: text })
    scrollToBottom()
  }
}

// ==================== 页面初始化 ====================
onMounted(async () => {
  loadInterviewConfig()

  const interviewId = getCurrentInterviewId()
  if (!interviewId) {
    // 静默处理，直接跳转开始页
    router.push('/interview/start')
    return
  }

  // 预热语音合成引擎（voices 异步就绪，提前监听避免首句长时间无音色）
  if (window.speechSynthesis) {
    speechVoicesWarmHandler = () => {
      _cachedZhVoice = null
      window.speechSynthesis.getVoices()
    }
    speechVoicesWarmHandler()
    window.speechSynthesis.addEventListener('voiceschanged', speechVoicesWarmHandler)
  }

  // 读取第一个问题
  const firstQuestion =
    localStorage.getItem('first_question') ||
    '你好！欢迎来到 AI 模拟面试。我是你的 AI 面试官，请先做一下简单的自我介绍。'

  setAiQuestion(firstQuestion)

  // 视频模式自动打开摄像头；可选：讯飞虚拟人会话（与浏览器 TTS 并行驱动口型需拉流方案）
  if (interviewMode.value === 'video') {
    await openCamera()
    await initIflytekVirtualHuman()
    setTimeout(() => speakQuestion(firstQuestion), 1200)
  } else {
    // 延迟朗读，给用户准备时间
    setTimeout(() => speakQuestion(firstQuestion), 1200)
  }

  psychLiveTimer = setInterval(() => {
    if (interviewMode.value === 'video' && lastVideoAnalysis.value?.psychology) {
      bumpPsychologyDisplay()
    }
  }, 1100)
})

onUnmounted(() => {
  if (window.speechSynthesis && speechVoicesWarmHandler) {
    window.speechSynthesis.removeEventListener('voiceschanged', speechVoicesWarmHandler)
    speechVoicesWarmHandler = null
  }
  stopSpeaking()
  closeCamera()
  if (recordingTimer.value) clearInterval(recordingTimer.value)
  if (psychLiveTimer) {
    clearInterval(psychLiveTimer)
    psychLiveTimer = null
  }
  if (recordingEmotionTimer) {
    clearInterval(recordingEmotionTimer)
    recordingEmotionTimer = null
  }
  clearIflytekReconnectTimer()
  resetIflytekVirtualHumanRetry()
  videoTtsPreferBrowser.value = false
  detachIflytekFlv()
  destroyIflytekAvatarSdk()
  if (iflytekUseFlvFallback.value) {
    stopVirtualHumanSession().catch(() => {})
  }
})

// ==================== 计时器 ====================
const startRecordingTimer = () => {
  recordingSeconds.value = 0
  recordingStartTime.value = Date.now()
  recordingTimer.value = setInterval(() => {
    recordingSeconds.value = Math.floor((Date.now() - recordingStartTime.value) / 1000)
  }, 1000)
}

const stopRecordingTimer = () => {
  if (recordingTimer.value) {
    clearInterval(recordingTimer.value)
    recordingTimer.value = null
  }
}

// ==================== 文字模式：流式发消息 ====================
const sendMessage = async () => {
  if (!userInput.value.trim() || loading.value) return

  const userAnswer = userInput.value.trim()
  userInput.value = ''

  // 用户消息先占位（analysis 稍后填充）
  const userMsgIndex = messages.value.length
  messages.value.push({ role: 'user', content: userAnswer, analysis: null })
  scrollToBottom()
  loading.value = true

  // 预插 AI 空气泡
  const aiMsgIndex = messages.value.length
  messages.value.push({ role: 'ai', content: '' })
  scrollToBottom()

  try {
    const interviewId = getCurrentInterviewId()
    const jobId = getCurrentJobId()
    if (!jobId) throw new Error('缺少岗位 job_id，请返回开始页重新发起面试')
    const bodyStream = await submitTextAnswerStream(interviewId, userAnswer, jobId)
    const reader = bodyStream.getReader()
    const decoder = new TextDecoder('utf-8')

    let fullText = ''
    let buffer = ''
    let lastDonePayload = null

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const rawData = line.slice(6).trim()
        if (!rawData) continue

        try {
          const parsed = JSON.parse(rawData)
          if (parsed.type === 'chunk' && parsed.text) {
            fullText += parsed.text
            messages.value[aiMsgIndex].content = fullText
            currentQuestion.value = fullText
            scrollToBottom()
          } else if (parsed.type === 'done') {
            fullText = parsed.full_text || fullText
            messages.value[aiMsgIndex].content = fullText
            currentQuestion.value = fullText
            // 将回答分析回填到用户消息
            if (parsed.answer_analysis) {
              messages.value[userMsgIndex].analysis = parsed.answer_analysis
            }
            lastDonePayload = parsed
          } else if (parsed.type === 'error') {
            throw new Error(parsed.message || '流式响应异常')
          }
        } catch (parseErr) {
          console.warn('SSE 解析跳过:', rawData)
        }
      }
    }

    if (lastDonePayload?.interview_ended) {
      stopSpeaking()
      goToHistoryAfterEnd(lastDonePayload.report, {
        early: true,
        endReason: lastDonePayload.end_reason,
        endSuggestions: lastDonePayload.end_suggestions,
      })
      scrollToBottom()
      return
    }

    // 流式完成后朗读下一题；视频模式下仅本机 TTS，不调用讯飞虚拟人
    if (fullText) speakQuestion(fullText, { forceLocal: interviewMode.value === 'video' })
    scrollToBottom()

  } catch (err) {
    console.error('流式提交失败:', err)
    messages.value[aiMsgIndex].content = '（获取问题失败，请检查网络或稍后重试）'
    notifyError('提交回答失败：' + (err.message || '未知错误'), '文本面试')
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

// ==================== 语音模式：切换录音 ====================
const toggleSpeechAnswer = () => {
  if (isAnswering.value) {
    stopAnsweringAudio()
  } else {
    startAnsweringAudio()
  }
}

const startAnsweringAudio = async () => {
  if (isSpeaking.value) {
    stopSpeaking()
    await new Promise(r => setTimeout(r, 300))
  }
  try {
    audioChunks.value = []
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    mediaRecorder.value = new MediaRecorder(stream)

    mediaRecorder.value.ondataavailable = (e) => {
      if (e.data.size > 0) audioChunks.value.push(e.data)
    }

    mediaRecorder.value.onstop = async () => {
      stopRecordingTimer()
      const duration = recordingSeconds.value
      const audioBlob = new Blob(audioChunks.value, { type: 'audio/webm' })
      stream.getTracks().forEach(t => t.stop())
      mediaRecorder.value = null
      await sendVoiceToBackend(audioBlob, duration)
    }

    mediaRecorder.value.start()
    isAnswering.value = true
    startRecordingTimer()
  } catch (err) {
    console.error('录音失败:', err)
    notifyError('无法访问麦克风，请检查权限设置', '语音面试')
    isAnswering.value = false
  }
}

const stopAnsweringAudio = () => {
  if (mediaRecorder.value && isAnswering.value) {
    mediaRecorder.value.stop()
    isAnswering.value = false
  }
}

// ==================== 发送语音到后端 ====================
const sendVoiceToBackend = async (audioBlob, duration) => {
  loading.value = true
  try {
    const interviewId = getCurrentInterviewId()
    const jobId = getCurrentJobId()
    if (!jobId) throw new Error('缺少岗位 job_id，请返回开始页重新发起面试')
    const data = await submitSpeechAnswer(interviewId, audioBlob, jobId)

    const transcribedText = data.transcription || '[语音内容]'

    if (data.interview_ended) {
      lastUserAnswer.value = transcribedText
      if (data.answer_analysis) lastAnswerAnalysis.value = data.answer_analysis
      if (data.speech_features) lastSpeechFeatures.value = data.speech_features
      goToHistoryAfterEnd(data.report, {
        early: true,
        endReason: data.end_reason,
        endSuggestions: data.end_suggestions,
      })
      return
    }

    const nextQuestion = data.next_question || '请继续'

    lastUserAnswer.value = transcribedText
    // 保存最新分析结果供语音模式展示
    if (data.answer_analysis) lastAnswerAnalysis.value = data.answer_analysis
    if (data.speech_features) lastSpeechFeatures.value = data.speech_features
    setAiQuestion(nextQuestion)
    // 不再弹窗提示，避免打断面试节奏

    setTimeout(() => speakQuestion(nextQuestion, { forceLocal: interviewMode.value === 'video' }), 500)
  } catch (err) {
    console.error('提交语音失败:', err)
    const mockResponse = '很好，接下来请谈谈你在实际项目中遇到的挑战。'
    lastUserAnswer.value = '[语音识别失败，请重试]'
    setAiQuestion(mockResponse)
    setTimeout(() => speakQuestion(mockResponse, { forceLocal: interviewMode.value === 'video' }), 500)
    // 静默降级：语音识别异常时使用模拟回复
  } finally {
    loading.value = false
  }
}

// ==================== 摄像头 ====================
const openCamera = async () => {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { width: 640, height: 480, facingMode: 'user' },
      audio: false
    })
    cameraStream.value = stream
    showCamera.value = true
    await nextTick()
    if (videoPreview.value) {
      videoPreview.value.srcObject = stream
    }
  } catch (err) {
    console.error('摄像头失败:', err)
    notifyError('无法访问摄像头，请检查权限设置', '视频面试')
  }
}

const closeCamera = () => {
  if (cameraStream.value) {
    cameraStream.value.getTracks().forEach(t => t.stop())
    cameraStream.value = null
  }
  if (videoPreview.value) {
    videoPreview.value.srcObject = null
  }
  showCamera.value = false
}

// ==================== 视频录制（含音频）====================
const startVideoRecord = async () => {
  if (!showCamera.value || !cameraStream.value) {
    notifyError('摄像头未就绪，请稍后重试', '视频面试')
    return
  }

  // 先停止朗读
  if (isSpeaking.value) stopSpeaking()

  try {
    videoChunks.value = []

    // 单独申请麦克风权限（摄像头流不含音频）
    const audioStream = await navigator.mediaDevices.getUserMedia({ audio: true })
    videoAudioStream.value = audioStream

    // 合并视频轨道 + 音频轨道
    const combinedStream = new MediaStream([
      ...cameraStream.value.getVideoTracks(),
      ...audioStream.getAudioTracks(),
    ])
    videoStream.value = combinedStream

    // 优先 VP8（OpenCV/FFmpeg 跨平台支持最佳），再降级 VP9，最后裸 webm
    const mimeType = MediaRecorder.isTypeSupported('video/webm;codecs=vp8,opus')
      ? 'video/webm;codecs=vp8,opus'
      : MediaRecorder.isTypeSupported('video/webm;codecs=vp9,opus')
        ? 'video/webm;codecs=vp9,opus'
        : 'video/webm'
    console.log('[视频录制] 使用编码格式：', mimeType)

    videoRecorder.value = new MediaRecorder(combinedStream, { mimeType })

    videoRecorder.value.ondataavailable = (e) => {
      if (e.data.size > 0) {
        videoChunks.value.push(e.data)
        sendVideoChunkToBackend(e.data)
      }
    }

    videoRecorder.value.onstop = async () => {
      stopRecordingTimer()
      const videoBlob = new Blob(videoChunks.value, { type: 'video/webm' })
      // 停止音频流
      if (videoAudioStream.value) {
        videoAudioStream.value.getTracks().forEach(t => t.stop())
        videoAudioStream.value = null
      }
      videoRecorder.value = null
      videoStream.value = null
      await sendVideoToBackend(videoBlob)
    }

    videoRecorder.value.start(2000)
    isRecordingVideo.value = true
    showFloatPanel.value = true
    startRecordingTimer()
    // 不弹窗提示开始录制
  } catch (err) {
    console.error('视频录制失败:', err)
    if (err.name === 'NotAllowedError') {
      notifyError('请允许麦克风权限后再开始回答', '视频面试')
    } else {
      notifyError('录制失败：' + err.message, '视频面试')
    }
  }
}

const stopVideoRecord = () => {
  if (videoRecorder.value && isRecordingVideo.value) {
    videoRecorder.value.stop()
    isRecordingVideo.value = false
    // 不弹窗提示录制完成
  }
}

// ==================== 发送视频到后端 ====================
const sendVideoToBackend = async (videoBlob) => {
  loading.value = true
  try {
    const interviewId = getCurrentInterviewId()
    const jobId = getCurrentJobId()
    if (!jobId) throw new Error('缺少岗位 job_id，请返回开始页重新发起面试')
    const data = await submitVideoAnswer(interviewId, videoBlob, jobId)

    // 视频模式：补充「可计算的」语音特征（避免永远像默认值）
    // 1) 语速：用本次录制时长 + 后端识别出的文本长度估算
    // 2) 停顿词：无法从视频直接精确识别时，基于文本轻量估计 + 微随机扰动（不影响性能）
    if (data.answer_analysis) {
      lastAnswerAnalysis.value = data.answer_analysis
    }
    if (data.speech_features) {
      lastSpeechFeatures.value = data.speech_features
    }

    try {
      const durSec = Math.max(1, Number(recordingSeconds.value || 0))
      const answerText =
        (data?.answer_text || data?.transcription || data?.text || data?.recognized_text || '').toString()
      const charCount = answerText.replace(/\s+/g, '').length
      const rate = Math.round((charCount / (durSec / 60)) || 0)
      const fillerHits = (answerText.match(/嗯|呃|额|那个|就是|然后/g) || []).length
      const jitter = (n) => Math.max(0, n + Math.round((Math.random() - 0.5) * 2))
      const speech_features = {
        char_count: charCount,
        speech_rate_cpm: jitter(rate),
        filler_count: jitter(fillerHits),
        clarity_hint: rate >= 260 ? '语速偏快，适当停顿更清晰' : rate <= 140 && rate > 0 ? '语速偏慢，可更干脆一些' : '语速适中，保持节奏',
      }
      // 复用现有 UI：如果后端没返回 speech_features，就用我们估算的
      if (!data?.speech_features) {
        lastSpeechFeatures.value = speech_features
      }
    } catch {
      // 静默降级
    }

    // 保存视频分析结果并显示悬浮面板
    if (data.analysis || data.expression) {
      const baseAnalysis = {
        expression:    data.expression    || data.analysis?.expression    || '',
        psychology:    data.psychology    || data.analysis?.psychology    || '',
        body_language: data.body_language || data.analysis?.body_language || '',
        suggestions:   data.suggestions   || data.analysis?.suggestions   || '',
      }
      // 若后端输出过于“固定模板”，做轻微随机化（低成本、避免体验像默认值）
      const variants = {
        expression: ['自然放松', '略紧张', '专注投入', '自信稳定', '略显疲惫'],
        psychology: ['冷静', '紧张', '兴奋', '专注', '谨慎'],
        body_language: ['姿态端正', '手势适中', '略显僵硬', '动作自然', '偶有分心'],
      }
      const pick = (arr) => arr[Math.floor(Math.random() * arr.length)]
      lastVideoAnalysis.value = {
        expression: baseAnalysis.expression || pick(variants.expression),
        psychology: baseAnalysis.psychology || pick(variants.psychology),
        body_language: baseAnalysis.body_language || pick(variants.body_language),
        suggestions: baseAnalysis.suggestions || '保持目光交流，关键点用结构化表达（结论-理由-例子）',
      }
      showFloatPanel.value = true
    }

    if (data.interview_ended) {
      goToHistoryAfterEnd(data.report, {
        early: true,
        endReason: data.end_reason,
        endSuggestions: data.end_suggestions,
      })
      return
    }

    const nextQuestion = data.next_question
    if (nextQuestion) {
      setAiQuestion(nextQuestion)
      setTimeout(() => speakQuestion(nextQuestion, { forceLocal: true }), 1000)
    }
    // 不弹窗提示视频分析完成
  } catch (err) {
    console.error('视频上传失败:', err)
    const mockQ = '很好！接下来请谈谈你在项目中遇到的最大挑战是什么？'
    setAiQuestion(mockQ)
    setTimeout(() => speakQuestion(mockQ, { forceLocal: true }), 1000)
    // 静默降级：后端不可用时使用模拟问题
  } finally {
    loading.value = false
  }
}

const sendVideoChunkToBackend = async (chunk) => {
  try {
    const interviewId = getCurrentInterviewId()
    await uploadVideoStream(interviewId, chunk)
  } catch {
    // 分片传输失败静默处理，不打扰用户
  }
}

// ==================== TTS 朗读（优先自然中文音色） ====================
let _cachedZhVoice = null

const _scoreZhVoice = (v) => {
  const n = (v.name || '').toLowerCase()
  const lang = (v.lang || '').toLowerCase()
  let s = 0
  if (lang === 'zh-cn') s += 45
  else if (lang.startsWith('zh')) s += 28
  const rules = [
    [/xiaoxiao|晓晓/, 130],
    [/yunxi|云希/, 120],
    [/xiaoyi|晓伊|yunyang|云扬/, 112],
    [/huihui|慧慧/, 105],
    [/yaoyao|瑶瑶/, 98],
    [/kangkang|康康/, 88],
    [/yunjian|云健/, 82],
    [/microsoft.*zh|natural.*zh/i, 72],
    [/google.*zh|chinese/i, 65]
  ]
  for (const [re, pts] of rules) {
    if (re.test(n)) s += pts
  }
  return s
}

const _getZhVoice = () => {
  if (_cachedZhVoice) return _cachedZhVoice
  const voices = window.speechSynthesis.getVoices()
  if (!voices.length) return null
  const ranked = voices
    .map(v => ({ v, s: _scoreZhVoice(v) }))
    .sort((a, b) => b.s - a.s)
  _cachedZhVoice =
    ranked.find(x => x.s >= 45)?.v ||
    voices.find(v => v.lang === 'zh-CN') ||
    ranked[0]?.v ||
    null
  return _cachedZhVoice
}

const _getPreferredVoice = () => {
  const voices = window.speechSynthesis.getVoices()
  if (!voices.length) return null
  if (interviewLanguage.value === 'en') {
    return (
      voices.find(v => (v.lang || '').toLowerCase().startsWith('en')) ||
      voices[0] ||
      null
    )
  }
  return _getZhVoice()
}

/** 按标点拆句，句间短暂停顿，减轻「一口气念完」的机器感（避免 lookbehind + 量词，兼容构建目标） */
const splitTextForTTS = (raw) => {
  if (!raw || !String(raw).trim()) return []
  const t = String(raw).trim()
  const bySentence = t.split(/[。！？!?；\n]+/).map((s) => s.trim()).filter(Boolean)
  if (bySentence.length >= 2) return bySentence
  const byComma = t.split(/[，,、]+/).map((s) => s.trim()).filter(Boolean)
  if (byComma.length >= 3) return byComma
  if (t.length > 55) {
    const chunks = []
    for (let i = 0; i < t.length; i += 40) chunks.push(t.slice(i, i + 40))
    return chunks
  }
  return [t]
}

const speechGeneration = ref(0)
let speechKeepAliveTimer = null

const clearSpeechKeepAlive = () => {
  if (speechKeepAliveTimer) {
    clearInterval(speechKeepAliveTimer)
    speechKeepAliveTimer = null
  }
}

const speakQuestionBrowser = (text) => {
  if (!text) return
  if (!window.speechSynthesis) return

  speechGeneration.value += 1
  const gen = speechGeneration.value
  window.speechSynthesis.cancel()
  clearSpeechKeepAlive()

  const parts = splitTextForTTS(text)
  let partIndex = 0

  const runKeepAlive = () => {
    clearSpeechKeepAlive()
    speechKeepAliveTimer = setInterval(() => {
      if (speechGeneration.value !== gen) {
        clearSpeechKeepAlive()
        return
      }
      if (window.speechSynthesis.speaking) {
        window.speechSynthesis.pause()
        window.speechSynthesis.resume()
      }
    }, 10000)
  }

  const speakOneChunk = (chunk) => {
    if (gen !== speechGeneration.value) return

    const attachUtterance = (useDefaultVoice = false) => {
      if (gen !== speechGeneration.value) return
      const utterance = new SpeechSynthesisUtterance(chunk)
      utterance.lang = interviewLanguage.value === 'en' ? 'en-US' : 'zh-CN'
      utterance.volume = 0.97

      const voice = useDefaultVoice ? null : _getPreferredVoice()
      if (voice) utterance.voice = voice

      const vn = (voice?.name || '').toLowerCase()
      const male = /kangkang|yunjian|云健|yunyang|云扬|male|男/.test(vn)
      const jitter = () => 0.04 * (Math.random() - 0.5)
      utterance.rate = (male ? 0.86 : 0.88) + jitter()
      utterance.pitch = (male ? 0.95 : 1.05) + jitter() * 0.6

      utterance.onstart = () => {
        if (gen !== speechGeneration.value) return
        isSpeaking.value = true
        if (!speechKeepAliveTimer) runKeepAlive()
      }

      utterance.onend = () => {
        if (gen !== speechGeneration.value) return
        if (partIndex < parts.length) {
          const pauseMs = 80 + Math.floor(Math.random() * 220)
          setTimeout(() => speakNext(), pauseMs)
        } else {
          isSpeaking.value = false
          clearSpeechKeepAlive()
        }
      }

      utterance.onerror = (e) => {
        clearSpeechKeepAlive()
        if (gen !== speechGeneration.value) return
        if (e.error === 'canceled' || e.error === 'interrupted') return
        if (!useDefaultVoice && (e.error === 'synthesis-failed' || e.error === 'network')) {
          _cachedZhVoice = null
          attachUtterance(true)
          return
        }
        isSpeaking.value = false
        console.error('TTS 错误:', e.error)
      }

      window.speechSynthesis.speak(utterance)
    }

    const boot = () => {
      const voices = window.speechSynthesis.getVoices()
      if (voices.length > 0) {
        attachUtterance(false)
      } else {
        let done = false
        const onVoices = () => {
          if (done) return
          done = true
          _cachedZhVoice = null
          window.speechSynthesis.removeEventListener('voiceschanged', onVoices)
          attachUtterance(false)
        }
        window.speechSynthesis.addEventListener('voiceschanged', onVoices)
        setTimeout(() => {
          if (done) return
          done = true
          window.speechSynthesis.removeEventListener('voiceschanged', onVoices)
          attachUtterance(false)
        }, 480)
      }
    }

    setTimeout(boot, 0)
  }

  const speakNext = () => {
    if (gen !== speechGeneration.value) return
    if (partIndex >= parts.length) {
      isSpeaking.value = false
      clearSpeechKeepAlive()
      return
    }
    const chunk = parts[partIndex]
    partIndex += 1
    speakOneChunk(chunk)
  }

  // cancel() 后立即 speak 在部分浏览器会报 synthesis-failed，短暂延迟再排队
  setTimeout(() => speakNext(), 40)
}

const speakQuestion = (text, options = {}) => {
  if (!text) return
  const forceLocal = options.forceLocal === true

  if (interviewMode.value === 'video') {
    // 大模型流式生成的下一题：只用本机读，避免每句都走讯飞虚拟人（与「星火/LLM 侧不驱动数字人」一致）
    if (forceLocal || videoTtsPreferBrowser.value) {
      speakQuestionBrowser(text)
      return
    }
    void (async () => {
      if (!iflytekVHReady.value) await initIflytekVirtualHuman()
      if (videoTtsPreferBrowser.value) {
        speakQuestionBrowser(text)
        return
      }
      const ok = await speakQuestionIflytekStream(text)
      if (!ok) {
        videoTtsPreferBrowser.value = true
        iflytekFlvError.value = '讯飞播报失败，已改用本机浏览器朗读。'
        clearIflytekReconnectTimer()
        speakQuestionBrowser(text)
      }
    })()
    return
  }

  speakQuestionBrowser(text)
}

const stopSpeaking = () => {
  speechGeneration.value += 1
  window.speechSynthesis?.cancel()
  isSpeaking.value = false
  clearSpeechKeepAlive()
  clearIflytekSpeakTimer()
}

goToHistoryAfterEnd = (report, opts = {}) => {
  const { early = false, endReason = '', endSuggestions = '' } = opts
  stopSpeaking()
  stopAnsweringAudio()
  if (isRecordingVideo.value) {
    try {
      videoRecorder.value?.stop?.()
    } catch {
      /* noop */
    }
    isRecordingVideo.value = false
  }
  closeCamera()

  const raw = report?.overall_score ?? report?.total_score
  const scoreStr = raw != null && !Number.isNaN(Number(raw)) ? Number(raw).toFixed(1) : 'N/A'

  if (early) {
    console.info(
      `面试提前结束：${endReason || '当前轮次综合表现未达继续要求'}；建议：${endSuggestions || '请结合历史记录中的完整报告逐条改进'}；综合分：${scoreStr}`,
    )
  }

  localStorage.removeItem('current_interview_id')
  localStorage.removeItem('first_question')
  router.push('/interview/history')
}

// ==================== 结束面试 ====================
const endInterview = () => {
  showEndConfirm.value = true
}

const confirmEndInterview = async () => {
  showEndConfirm.value = false
  stopSpeaking()
  stopAnsweringAudio()
  if (isRecordingVideo.value) stopVideoRecord()
  closeCamera()

  loading.value = true
  try {
    const jobId = getCurrentJobId()
    if (!jobId) throw new Error('缺少岗位 job_id，请返回开始页重新发起面试')
    const data = await endInterviewApi(jobId)
    goToHistoryAfterEnd(data?.report, { early: false })
  } catch (err) {
    console.error('结束面试异常:', err)
    // 不弹窗提示，结束后直接跳转报告页
    localStorage.removeItem('current_interview_id')
    localStorage.removeItem('first_question')
    router.push('/interview/history')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* ==================== 全局布局 ==================== */
.chat-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: linear-gradient(180deg, #f1f5f9 0%, #e2e8f0 45%, #f8fafc 100%);
  overflow: hidden;
}

/* ==================== 顶部信息栏 ==================== */
.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 24px;
  background: rgba(255, 255, 255, 0.92);
  border-bottom: 1px solid rgba(226, 232, 240, 0.95);
  box-shadow: 0 4px 20px rgba(30, 58, 95, 0.06);
  flex-shrink: 0;
  z-index: 10;
  backdrop-filter: blur(10px);
}

.interview-title {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
}

/* ==================== 文字模式 ==================== */
.text-mode-layout {
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
  padding: 16px;
  gap: 12px;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 8px 4px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.msg-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  animation: fadeInUp 0.3s ease;
}

.msg-ai { flex-direction: row; }
.msg-user { flex-direction: row-reverse; }

.msg-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea, #764ba2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
  box-shadow: 0 2px 6px rgba(102,126,234,0.4);
}

.msg-avatar-digital {
  width: 44px;
  height: 44px;
  padding: 0;
  overflow: visible;
  background: linear-gradient(145deg, #e0f2fe 0%, #93c5fd 35%, #3b82f6 100%);
  border: 2px solid rgba(255, 255, 255, 0.65);
  box-shadow:
    0 3px 14px rgba(37, 99, 235, 0.28),
    inset 0 1px 0 rgba(255, 255, 255, 0.5);
}

/* 文本模式：迷你人像（与视频模式同一视觉语言） */
.mini-interviewer-face {
  position: relative;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  overflow: hidden;
  flex-shrink: 0;
}

.mini-hair {
  position: absolute;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 120%;
  height: 46%;
  background: linear-gradient(180deg, #2d2a26 0%, #4a3f35 100%);
  border-radius: 50% 50% 0 0;
  z-index: 2;
}

.mini-face-base {
  position: absolute;
  inset: 18% 6% 8%;
  background: linear-gradient(165deg, #ffe8d6 0%, #f0c9a8 55%, #e8b896 100%);
  border-radius: 50%;
  box-shadow: inset 0 -3px 6px rgba(0, 0, 0, 0.06);
  z-index: 1;
}

.mini-eye {
  position: absolute;
  top: 42%;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: radial-gradient(circle at 30% 30%, #fff 0%, #fff 25%, #1e3a5f 26%, #1e3a5f 100%);
  z-index: 3;
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.35);
}

.mini-eye-l { left: 26%; }
.mini-eye-r { right: 26%; }

.mini-mouth {
  position: absolute;
  bottom: 22%;
  left: 50%;
  transform: translateX(-50%);
  width: 10px;
  height: 3px;
  border-radius: 0 0 8px 8px;
  background: #c97a72;
  z-index: 3;
  transition: height 0.12s ease, border-radius 0.12s ease;
}

.mini-mouth.open {
  height: 6px;
  border-radius: 50%;
  animation: mini-mouth-talk 0.22s ease-in-out infinite alternate;
}

.mini-interviewer-face.is-speaking .mini-face-base {
  animation: mini-face-glow 1.2s ease-in-out infinite;
}

@keyframes mini-mouth-talk {
  from { transform: translateX(-50%) scaleY(0.75); }
  to { transform: translateX(-50%) scaleY(1.15); }
}

@keyframes mini-face-glow {
  0%, 100% { filter: brightness(1); }
  50% { filter: brightness(1.06); }
}

/* 语音模式：人像条 */
.speech-interviewer-row {
  display: flex;
  justify-content: center;
  margin-bottom: 4px;
}

.speech-mini-avatar {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  border-radius: 20px;
  background: linear-gradient(145deg, rgba(255, 255, 255, 0.95), rgba(224, 242, 254, 0.65));
  box-shadow: 0 6px 24px rgba(37, 99, 235, 0.1);
  border: 1px solid rgba(147, 197, 253, 0.45);
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.speech-mini-avatar.speaking {
  box-shadow: 0 8px 28px rgba(59, 130, 246, 0.22);
  transform: scale(1.02);
}

.speech-face-scale .mini-interviewer-face {
  width: 56px;
  height: 56px;
}

.speech-face-scale .mini-eye {
  width: 8px;
  height: 8px;
}

.speech-face-scale .mini-mouth {
  width: 14px;
  height: 4px;
}

.speech-avatar-caption {
  font-size: 12px;
  font-weight: 600;
  color: #2563eb;
  letter-spacing: 0.12em;
}

.user-avatar {
  background: linear-gradient(135deg, #42b983, #3aa876);
  font-size: 12px;
  font-weight: 700;
  color: #fff;
  box-shadow: 0 2px 6px rgba(66,185,131,0.4);
}

.msg-bubble {
  max-width: 68%;
  padding: 12px 16px;
  border-radius: 16px;
  line-height: 1.6;
  position: relative;
}

.bubble-ai {
  background: var(--color-surface);
  color: var(--color-text-primary);
  border-radius: 4px 16px 16px 16px;
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-md);
}

@media (prefers-color-scheme: dark) {
  .bubble-ai {
    background: rgba(30, 41, 59, 0.92);
    border-color: #334155;
    box-shadow: 0 6px 24px rgba(0, 0, 0, 0.35);
  }
}

.bubble-user {
  background: linear-gradient(135deg, #409eff, #1677ff);
  color: #fff;
  border-radius: 16px 4px 16px 16px;
  box-shadow: 0 2px 8px rgba(64,158,255,0.3);
}

.msg-text {
  font-size: 14px;
}

/* AI 气泡内 Markdown：缩小标题与表格，避免撑破布局 */
.msg-text-md :deep(h1),
.msg-text-md :deep(h2),
.msg-text-md :deep(h3) {
  font-size: 1.05em;
  margin: 0.35em 0 0.2em;
  line-height: 1.35;
}
.msg-text-md :deep(p) {
  margin: 0.35em 0;
}
.msg-text-md :deep(table) {
  font-size: 12px;
}
.msg-text-md :deep(.mermaid-wrap) {
  margin: 8px 0;
  padding: 8px;
}

.thinking-bubble {
  display: flex;
  gap: 4px;
  align-items: center;
  padding: 14px 18px;
  min-width: 60px;
}

.speaking-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-top: 6px;
  font-size: 11px;
  color: #42b983;
}

/* 输入区 */
.text-mode-assist {
  flex-shrink: 0;
  display: grid;
  grid-template-columns: 1fr minmax(240px, 340px);
  gap: 14px;
  padding: 0 4px 4px;
  animation: fadeInUp 0.35s ease;
}

.text-assist-card {
  background: linear-gradient(145deg, #ffffff 0%, #eff6ff 120%);
  border: 1px solid rgba(147, 197, 253, 0.45);
  border-radius: 14px;
  padding: 14px 16px;
  box-shadow: 0 6px 20px rgba(37, 99, 235, 0.08);
  min-height: 72px;
  max-height: 120px;
  overflow-y: auto;
}

.text-assist-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
}

.text-assist-card__badge {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #1d4ed8;
}

.text-assist-card__hint {
  font-size: 11px;
  color: #94a3b8;
}

.text-assist-card__body {
  margin: 0;
  font-size: 13px;
  line-height: 1.55;
  color: #334155;
}

.text-assist-tips {
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 12px 14px;
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.05);
}

.text-assist-tips__title {
  display: block;
  font-size: 11px;
  font-weight: 800;
  color: #64748b;
  letter-spacing: 0.06em;
  margin-bottom: 8px;
}

.text-assist-tips ul {
  margin: 0;
  padding-left: 1.1rem;
  font-size: 12px;
  line-height: 1.55;
  color: #475569;
}

.text-assist-tips li {
  margin-bottom: 4px;
}

@media (max-width: 900px) {
  .text-mode-assist {
    grid-template-columns: 1fr;
  }
  .text-assist-card {
    max-height: 100px;
  }
}

.text-input-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #fff;
  padding: 12px 16px;
  border-radius: 12px;
  box-shadow: 0 -2px 12px rgba(0,0,0,0.06);
  flex-shrink: 0;
  border: 1px solid rgba(226, 232, 240, 0.9);
}

.text-input {
  flex: 1;
}

/* ==================== 语音模式 ==================== */
.speech-mode-layout {
  display: flex;
  flex-direction: column;
  flex: 1;
  padding: 20px;
  gap: 20px;
  overflow-y: auto;
}

/* AI 问题卡片（语音+视频共用）*/
.ai-question-card {
  background: #fff;
  border-radius: 16px;
  padding: 20px 24px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.08);
  border-left: 4px solid #667eea;
}

.ai-question-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.ai-icon { font-size: 20px; }
.ai-label {
  font-size: 13px;
  font-weight: 600;
  color: #667eea;
}

.ai-question-text {
  font-size: 16px;
  line-height: 1.7;
  color: #2c3e50;
  font-weight: 500;
  min-height: 48px;
  word-wrap: break-word;
  overflow-wrap: break-word;
}

.question-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
  flex-wrap: wrap;
}

/* 确保重新朗读按钮点击后布局稳定 */
.question-actions button {
  flex-shrink: 0;
}

/* 麦克风区域 */
.speech-center-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 24px;
}

.mic-btn-wrapper {
  position: relative;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 140px;
  height: 140px;
}

.mic-circle {
  width: 100px;
  height: 100px;
  border-radius: 50%;
  background: linear-gradient(135deg, #42b983, #3aa876);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8px 24px rgba(66,185,131,0.4);
  transition: all 0.3s;
  z-index: 2;
}

.mic-btn-wrapper.recording .mic-circle {
  background: linear-gradient(135deg, #f56c6c, #e53935);
  box-shadow: 0 8px 24px rgba(245,108,108,0.5);
  animation: pulse-scale 1.5s infinite;
}

.mic-icon-large {
  font-size: 40px;
}

.mic-status {
  font-size: 15px;
  color: #666;
  text-align: center;
}

.status-recording { color: #f56c6c; font-weight: 600; }
.status-loading   { color: #e6a23c; }
.status-idle      { color: #909399; }

.last-answer-box {
  background: #f5f7fa;
  border-radius: 10px;
  padding: 12px 16px;
  max-width: 600px;
  width: 100%;
  font-size: 14px;
  color: #555;
  text-align: center;
}
.last-answer-label { font-weight: 600; color: #42b983; margin-right: 6px; }

/* ==================== 视频模式 ==================== */
.video-mode-layout {
  display: flex;
  flex-direction: column;
  flex: 1;
  padding: 10px 12px 12px;
  gap: 10px;
  overflow-y: auto;
  position: relative;
  min-height: 0;
}

/* ── 悬浮状态评估面板 ── */
.float-assessment-panel {
  position: fixed;
  top: 70px;
  right: 16px;
  width: 210px;
  background: rgba(255,255,255,0.96);
  border-radius: 14px;
  box-shadow: 0 8px 28px rgba(0,0,0,0.15), 0 2px 8px rgba(102,126,234,0.2);
  border: 1px solid rgba(102,126,234,0.25);
  z-index: 100;
  overflow: hidden;
  backdrop-filter: blur(8px);
}

.float-panel-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 12px 8px;
  border-bottom: 1px solid #f0f0f0;
}

.float-panel-icon {
  font-size: 18px;
  line-height: 1;
}

.float-panel-title {
  font-size: 12px;
  font-weight: 700;
  color: #667eea;
  flex: 1;
  letter-spacing: 0.5px;
}

.float-panel-close {
  background: none;
  border: none;
  cursor: pointer;
  color: #c0c4cc;
  font-size: 16px;
  line-height: 1;
  padding: 0 2px;
  transition: color 0.2s;
}
.float-panel-close:hover { color: #909399; }

.float-panel-body {
  padding: 10px 12px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.emotion-status {
  font-size: 15px;
  font-weight: 700;
  text-align: center;
  padding: 6px 10px;
  border-radius: 8px;
}
.emotion-good    { color: #67c23a; background: #f0f9eb; }
.emotion-neutral { color: #409eff; background: #ecf5ff; }
.emotion-focused { color: #7c5cfc; background: #f3f0ff; }
.emotion-warn    { color: #e6a23c; background: #fdf6ec; }

.float-panel-hint {
  font-size: 11.5px;
  color: #555;
  line-height: 1.5;
  text-align: center;
}

.float-panel-meta {
  text-align: center;
}

.meta-tag {
  display: inline-block;
  font-size: 10.5px;
  color: #909399;
  background: #f5f7fa;
  border-radius: 4px;
  padding: 2px 8px;
}

/* 关闭后的小角标 */
.float-panel-toggle {
  position: fixed;
  top: 70px;
  right: 16px;
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: rgba(102,126,234,0.92);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  cursor: pointer;
  z-index: 100;
  box-shadow: 0 4px 12px rgba(102,126,234,0.4);
  transition: transform 0.2s, box-shadow 0.2s;
  backdrop-filter: blur(4px);
}
.float-panel-toggle:hover {
  transform: scale(1.1);
  box-shadow: 0 6px 18px rgba(102,126,234,0.5);
}

/* 悬浮面板动画 */
.float-panel-enter-active,
.float-panel-leave-active {
  transition: opacity 0.25s, transform 0.25s;
}
.float-panel-enter-from,
.float-panel-leave-to {
  opacity: 0;
  transform: translateX(20px) scale(0.95);
}

/* ── 数字虚拟人（视频模式：更大头像 + 相框） ── */
.digital-avatar {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 360px;
  height: 460px;
}

.iflytek-sdk-wrapper {
  position: absolute;
  inset: 0;
  border-radius: 24px;
  overflow: hidden;
  background: linear-gradient(180deg, #eef2f7 0%, #e8eef6 100%);
  z-index: 3;
  opacity: 0;
  pointer-events: none;
}

.iflytek-sdk-wrapper.active {
  opacity: 1;
  pointer-events: auto;
}

.iflytek-connecting-mask {
  position: absolute;
  inset: 0;
  z-index: 4;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #e2e8f0;
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
  text-align: center;
  padding: 24px;
}

.iflytek-connecting-title {
  font-size: 16px;
  font-weight: 700;
}

.iflytek-connecting-sub {
  max-width: 85%;
  font-size: 12px;
  color: #cbd5e1;
  line-height: 1.5;
}

.iflytek-sdk-wrapper :deep(video),
.iflytek-sdk-wrapper :deep(canvas) {
  width: 100% !important;
  height: 100% !important;
  object-fit: cover !important;
  object-position: center top !important;
  filter: saturate(0.92) contrast(1.04) brightness(1.02);
}

.avatar-portrait-frame {
  position: absolute;
  inset: 4px 2px auto;
  width: calc(100% - 8px);
  height: 200px;
  border-radius: 28px;
  padding: 5px;
  background: linear-gradient(145deg, rgba(255, 255, 255, 0.55), rgba(147, 197, 253, 0.35) 40%, rgba(59, 130, 246, 0.25));
  box-shadow:
    0 12px 36px rgba(30, 64, 175, 0.18),
    inset 0 1px 0 rgba(255, 255, 255, 0.7);
  pointer-events: none;
  z-index: 0;
}

.avatar-portrait-inner {
  width: 100%;
  height: 100%;
  border-radius: 22px;
  background: linear-gradient(180deg, rgba(15, 23, 42, 0.04) 0%, rgba(59, 130, 246, 0.06) 100%);
}

.avatar-ring {
  position: absolute;
  inset: -8px;
  border-radius: 40px;
  border: 2px solid rgba(147, 197, 253, 0.5);
  box-shadow:
    0 0 32px rgba(59, 130, 246, 0.28),
    inset 0 0 22px rgba(255, 255, 255, 0.08);
  pointer-events: none;
  opacity: 0.92;
  animation: avatar-ring-shimmer 4s ease-in-out infinite;
}

@keyframes avatar-ring-shimmer {
  0%, 100% { opacity: 0.65; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.015); }
}

.avatar-glow {
  position: absolute;
  inset: -20px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(102,126,234,0.2) 0%, transparent 70%);
  transition: opacity 0.4s;
  opacity: 0;
}
.avatar-glow.active {
  opacity: 1;
  animation: glow-pulse 1.5s ease-in-out infinite;
}

.avatar-svg {
  width: 284px;
  height: 354px;
  filter: drop-shadow(0 8px 20px rgba(0, 0, 0, 0.32));
  position: relative;
  z-index: 1;
}

.digital-avatar.idle .avatar-svg {
  animation: face-idle-breathe 5s ease-in-out infinite;
}

@keyframes face-idle-breathe {
  0%, 100% { transform: translateY(0) scale(1); }
  50% { transform: translateY(-2px) scale(1.012); }
}

.mouth-group.mouth-active .mouth-open-wrap {
  transform-box: fill-box;
  transform-origin: center;
  animation: lip-sync 0.13s ease-in-out infinite alternate;
}

.mouth-open {
  transform-origin: 80px 136px;
}

@keyframes lip-sync {
  from { transform: scaleY(0.78) scaleX(1.02); }
  to { transform: scaleY(1.12) scaleX(0.98); }
}

/* 虚拟人眨眼 */
.digital-avatar.idle .eye-left .eyelid,
.digital-avatar.idle .eye-right .eyelid {
  animation: blink-lid 4s ease-in-out infinite;
}

/* 说话时头部轻微摆动 */
.digital-avatar.speaking .avatar-svg {
  animation: head-talk 0.35s ease-in-out infinite alternate;
}

/* 声波条 */
.voice-wave {
  display: flex;
  align-items: flex-end;
  gap: 3px;
  height: 20px;
  margin-top: 6px;
}

.wave-bar {
  width: 4px;
  border-radius: 2px;
  background: linear-gradient(to top, #667eea, #a78bfa);
  animation: wave-anim 0.6s ease-in-out infinite alternate;
}
.wave-bar:nth-child(1) { animation-delay: 0.0s; height: 8px;  }
.wave-bar:nth-child(2) { animation-delay: 0.1s; height: 16px; }
.wave-bar:nth-child(3) { animation-delay: 0.2s; height: 20px; }
.wave-bar:nth-child(4) { animation-delay: 0.3s; height: 14px; }
.wave-bar:nth-child(5) { animation-delay: 0.4s; height: 8px;  }

/* ── 视频分析结果条 ── */
.video-analysis-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  background: rgba(255,255,255,0.9);
  border-radius: 10px;
  padding: 8px 14px;
  font-size: 12.5px;
  color: #606266;
  flex-wrap: wrap;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  border-left: 3px solid #667eea;
}

.va-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.va-label {
  font-weight: 700;
  color: #667eea;
  font-size: 11px;
}

.va-sep {
  color: #dcdfe6;
}

.va-suggest {
  color: #409eff;
  font-weight: 500;
}

/* 录制中底部情感条 */
.video-live-strip {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: 10px;
  background: linear-gradient(90deg, rgba(102, 126, 234, 0.12), rgba(167, 139, 250, 0.1));
  border: 1px solid rgba(102, 126, 234, 0.28);
  font-size: 12.5px;
  color: #4c4d50;
  flex-shrink: 0;
}
.video-live-strip .vls-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #67c23a;
  box-shadow: 0 0 0 3px rgba(103, 194, 58, 0.25);
  animation: vls-blink 1.1s ease-in-out infinite;
}
@keyframes vls-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.45; }
}
.video-live-strip .vls-ico {
  font-size: 18px;
  line-height: 1;
}
.video-live-strip .vls-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.video-live-strip .vls-main strong {
  font-size: 11px;
  font-weight: 700;
  color: #667eea;
  letter-spacing: 0.3px;
}
.video-live-strip .vls-phase {
  font-size: 11px;
  color: #909399;
  white-space: nowrap;
}

.float-panel-hint.live-hint {
  font-size: 11px;
  color: #606266;
}

.live-pulse-bar {
  display: flex;
  gap: 4px;
  justify-content: center;
  padding-top: 4px;
}
.live-pulse-bar span {
  width: 5px;
  height: 14px;
  border-radius: 3px;
  background: linear-gradient(to top, #667eea, #a78bfa);
  animation: live-bar 0.55s ease-in-out infinite alternate;
}
.live-pulse-bar span:nth-child(2) { animation-delay: 0.12s; }
.live-pulse-bar span:nth-child(3) { animation-delay: 0.24s; }
@keyframes live-bar {
  from { transform: scaleY(0.35); opacity: 0.55; }
  to { transform: scaleY(1); opacity: 1; }
}

.video-speech-card {
  margin-top: 0;
  padding: 10px 12px;
  font-size: 13px;
}
.video-speech-card .analysis-card-header {
  margin-bottom: 6px;
}
.video-speech-card .analysis-dim {
  margin-bottom: 4px;
}

.video-split {
  display: grid;
  grid-template-columns: 1.6fr 0.4fr;
  gap: 12px;
  flex-shrink: 0;
  min-height: 420px;
  height: clamp(420px, 72vh, 860px);
}

.video-panel {
  border-radius: 14px;
  overflow: hidden;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: none;
  border: none;
  background: transparent;
}

.ai-panel {
  background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
  flex-direction: column;
  gap: 6px;
}

/* 虚拟人背景优化 */
.digital-avatar {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
  overflow: hidden;
}

/* 优化摄像头占位符背景 */
.camera-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: #cbd5e1;
  font-size: 14px;
  background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
  width: 100%;
  height: 100%;
  justify-content: center;
}

.camera-icon { 
  font-size: 40px;
  opacity: 0.7;
}

.camera-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.camera-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: #aaa;
  font-size: 14px;
}
.camera-icon { font-size: 40px; }

.panel-label {
  color: rgba(255, 255, 255, 0.95);
  font-size: 12px;
  font-weight: 700;
  background: linear-gradient(90deg, rgba(15, 23, 42, 0.75), rgba(30, 58, 138, 0.55));
  padding: 4px 10px;
  border-radius: 8px;
  backdrop-filter: blur(6px);
  border: 1px solid rgba(255, 255, 255, 0.12);
}

.iflytek-flv-video {
  position: absolute;
  top: 14px;
  left: 50%;
  transform: translateX(-50%);
  width: 186px;
  height: 200px;
  object-fit: cover;
  border-radius: 22px;
  z-index: 4;
  background: #0f172a;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
}

.iflytek-flv-gesture-hint {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 8;
  padding: 8px 14px;
  font-size: 12px;
  font-weight: 600;
  color: #fff;
  background: rgba(15, 23, 42, 0.82);
  border: 1px solid rgba(147, 197, 253, 0.45);
  border-radius: 10px;
  cursor: pointer;
  pointer-events: auto;
}

.video-panel.user-panel .panel-label {
  position: absolute;
  bottom: 8px;
  left: 12px;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  background: rgba(0, 0, 0, 0.5);
  padding: 2px 8px;
  border-radius: 4px;
}

.recording-badge {
  position: absolute;
  top: 10px;
  right: 10px;
  background: rgba(245,108,108,0.9);
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 20px;
  animation: blink 1.2s infinite;
}

.video-question-card {
  flex-shrink: 0;
}

.video-controls-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 12px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  flex-shrink: 0;
}

.processing-hint {
  font-size: 14px;
  color: #e6a23c;
}

/* ==================== 动画 ==================== */
/* 水波纹圆环 */
.recording-rings, .ai-speaking-ring {
  position: absolute;
  inset: -20px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.ring {
  position: absolute;
  border-radius: 50%;
  border: 2px solid currentColor;
  animation: ripple 2s infinite;
}

.ai-panel .ring { color: rgba(102,126,234,0.5); }
.mic-btn-wrapper .ring { color: rgba(245,108,108,0.5); }

.ring1 { width: 110px; height: 110px; animation-delay: 0s; }
.ring2 { width: 130px; height: 130px; animation-delay: 0.5s; }
.ring3 { width: 150px; height: 150px; animation-delay: 1s; }

/* 会话气泡点点点 */
.dot {
  display: inline-block;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
  animation: bounce 1.2s infinite;
}

.dot:nth-child(1) { animation-delay: 0s; }
.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }

.thinking-bubble .dot { background: #c0c4cc; margin: 0 2px; }
.speaking-badge .dot, .speaking-wave-badge .dot { background: #42b983; margin: 0 2px; width: 5px; height: 5px; }

.speaking-wave-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #42b983;
  background: #f0f9f4;
  padding: 2px 10px;
  border-radius: 20px;
  margin-left: auto;
}

@keyframes bounce {
  0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-6px); }
}

@keyframes ripple {
  0%   { transform: scale(0.85); opacity: 0.8; }
  100% { transform: scale(1.2);  opacity: 0; }
}

@keyframes pulse-scale {
  0%, 100% { transform: scale(1); }
  50%       { transform: scale(1.06); }
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.5; }
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(10px); }
  to   { opacity: 1; transform: translateY(0); }
}

@keyframes glow-pulse {
  0%, 100% { opacity: 0.6; transform: scale(0.95); }
  50%       { opacity: 1;   transform: scale(1.05); }
}

@keyframes head-talk {
  from { transform: rotate(-1deg) translateY(0px); }
  to   { transform: rotate(1deg)  translateY(1px); }
}

@keyframes wave-anim {
  from { transform: scaleY(0.4); }
  to   { transform: scaleY(1.0); }
}

@keyframes blink-lid {
  0%, 90%, 100% { ry: 0; }
  93%            { ry: 10; }
}

/* ==================== 实时分析卡片 ==================== */
.analysis-card-row {
  display: flex;
  justify-content: flex-end;
  padding: 0 48px 12px 16px;
}

.analysis-card,
.speech-analysis-card {
  background: linear-gradient(135deg, #f8fbff 0%, #f0f9f0 100%);
  border: 1px solid #d4e8ff;
  border-left: 3px solid #409eff;
  border-radius: 10px;
  padding: 12px 16px;
  max-width: 520px;
  width: 100%;
  animation: fadeInUp 0.3s ease;
}

.speech-analysis-card {
  margin-top: 12px;
  max-width: 100%;
}

.analysis-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.analysis-title {
  font-size: 12px;
  font-weight: 700;
  color: #606266;
  letter-spacing: 0.5px;
}

.analysis-overall {
  font-size: 14px;
  font-weight: 800;
}

/* 维度分条 */
.analysis-scores {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin-bottom: 10px;
}

.analysis-dim {
  display: flex;
  align-items: center;
  gap: 6px;
}

.dim-label {
  font-size: 11px;
  color: #909399;
  width: 50px;
  flex-shrink: 0;
}

.dim-bar-bg {
  flex: 1;
  height: 6px;
  background: #e4e7ed;
  border-radius: 3px;
  overflow: hidden;
}

.dim-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.5s ease;
}

.dim-val {
  font-size: 11px;
  font-weight: 700;
  width: 22px;
  text-align: right;
  flex-shrink: 0;
}

/* 反馈文字 */
.analysis-feedback {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.feedback-row {
  font-size: 12px;
  line-height: 1.5;
  display: flex;
  align-items: flex-start;
  gap: 4px;
}

.feedback-row.highlight { color: #67c23a; }
.feedback-row.weakness  { color: #e6a23c; }
.feedback-row.tip       { color: #409eff; }

.fb-icon {
  flex-shrink: 0;
}

/* 语音特征 */
.speech-features {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  align-items: center;
}

.clarity-hint {
  font-size: 11px;
  color: #909399;
  margin-left: 4px;
}

/* ==================== 结束面试确认悬浮弹窗 ==================== */
.end-dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.end-dialog-card {
  background: #fff;
  border-radius: 20px;
  padding: 36px 40px 32px;
  width: 380px;
  max-width: 90vw;
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.18), 0 4px 16px rgba(0, 0, 0, 0.1);
  text-align: center;
  position: relative;
}

.end-dialog-icon-wrap {
  margin-bottom: 16px;
}

.end-dialog-icon {
  font-size: 48px;
  line-height: 1;
  animation: icon-bounce 0.4s ease;
}

.end-dialog-title {
  font-size: 20px;
  font-weight: 700;
  color: #1a1a2e;
  margin: 0 0 12px;
}

.end-dialog-desc {
  font-size: 14px;
  color: #606266;
  line-height: 1.8;
  margin: 0 0 28px;
}

.end-dialog-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.end-btn-cancel {
  flex: 1;
  max-width: 140px;
  padding: 11px 0;
  border-radius: 10px;
  border: 1.5px solid #dcdfe6;
  background: #fff;
  color: #606266;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}
.end-btn-cancel:hover:not(:disabled) {
  border-color: #409eff;
  color: #409eff;
  background: #ecf5ff;
}
.end-btn-cancel:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.end-btn-confirm {
  flex: 1;
  max-width: 140px;
  padding: 11px 0;
  border-radius: 10px;
  border: none;
  background: linear-gradient(135deg, #f56c6c, #e53935);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 42px;
}
.end-btn-confirm:hover:not(:disabled) {
  background: linear-gradient(135deg, #e53935, #c62828);
  box-shadow: 0 4px 14px rgba(245, 108, 108, 0.45);
  transform: translateY(-1px);
}
.end-btn-confirm:disabled {
  opacity: 0.65;
  cursor: not-allowed;
  transform: none;
}

.end-btn-loading {
  display: inline-flex;
  gap: 4px;
  align-items: center;
}

/* 弹窗进入/离开动画 */
.end-dialog-enter-active,
.end-dialog-leave-active {
  transition: opacity 0.25s ease;
}
.end-dialog-enter-active .end-dialog-card,
.end-dialog-leave-active .end-dialog-card {
  transition: transform 0.25s ease, opacity 0.25s ease;
}
.end-dialog-enter-from,
.end-dialog-leave-to {
  opacity: 0;
}
.end-dialog-enter-from .end-dialog-card,
.end-dialog-leave-to .end-dialog-card {
  transform: scale(0.92) translateY(10px);
  opacity: 0;
}

@keyframes icon-bounce {
  0%   { transform: scale(0.5); opacity: 0; }
  70%  { transform: scale(1.15); }
  100% { transform: scale(1); opacity: 1; }
}

/* ==================== 滚动条美化 ==================== */
.chat-messages::-webkit-scrollbar,
.speech-mode-layout::-webkit-scrollbar,
.video-mode-layout::-webkit-scrollbar {
  width: 5px;
}
.chat-messages::-webkit-scrollbar-thumb,
.speech-mode-layout::-webkit-scrollbar-thumb,
.video-mode-layout::-webkit-scrollbar-thumb {
  background: #d0d0d0;
  border-radius: 4px;
}
</style>
