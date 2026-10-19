<template>
  <div class="vh-player" @click="unlockAudio">
    <video ref="videoRef" class="vh-video" playsinline autoplay :muted="muted" />
    <div v-if="loading" class="vh-mask">正在连接虚拟面试官...</div>
    <div v-else-if="errorText" class="vh-mask err">{{ errorText }}</div>
    <button v-if="needGesture" class="vh-unlock" @click.stop="unlockAudio">点击开启声音</button>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { attachFlvLivePlayer } from '@/utils/iflytekFlvPlayer'
import { normalizeFlvPlayableUrl } from '@/utils/iflytekSrsFlv'

const props = defineProps({
  streamUrl: { type: String, default: '' },
  autoMute: { type: Boolean, default: true },
  rtmpToFlvProtocol: { type: String, default: 'https' },
  reconnectMax: { type: Number, default: 20 },
})

const emit = defineEmits(['playing', 'error'])

const videoRef = ref(null)
const loading = ref(true)
const errorText = ref('')
const needGesture = ref(false)
const muted = ref(props.autoMute)
let destroyPlayer = null
let retryCount = 0
let retryTimer = null

const cleanup = () => {
  if (retryTimer) {
    clearTimeout(retryTimer)
    retryTimer = null
  }
  if (destroyPlayer) {
    try {
      destroyPlayer()
    } catch (_) {}
    destroyPlayer = null
  }
}

const reconnect = (reason) => {
  cleanup()
  if (retryCount >= props.reconnectMax) {
    loading.value = false
    errorText.value = `直播连接失败：${reason}`
    emit('error', errorText.value)
    return
  }
  const delay = Math.min(10000, 1500 * Math.pow(1.4, retryCount))
  retryCount += 1
  loading.value = true
  errorText.value = `连接中断，${Math.round(delay)}ms 后重试...`
  retryTimer = setTimeout(start, delay)
}

const start = async () => {
  const playable = normalizeFlvPlayableUrl(props.streamUrl, props.rtmpToFlvProtocol)
  if (!playable) {
    loading.value = false
    errorText.value = '未配置可播放的流地址（请设置 HTTP-FLV 或 RTMP 地址）'
    emit('error', errorText.value)
    return
  }
  if (!videoRef.value) return

  loading.value = true
  errorText.value = ''
  needGesture.value = false

  try {
    destroyPlayer = attachFlvLivePlayer(videoRef.value, playable)
    videoRef.value.muted = muted.value
    videoRef.value.preload = 'auto'
    // 低延迟目标：让浏览器尽快消费音视频帧，避免口型滞后
    videoRef.value.autoplay = true
    videoRef.value.playsInline = true
    await videoRef.value.play().catch(() => {
      needGesture.value = true
    })
    retryCount = 0
    loading.value = false
    emit('playing', playable)
  } catch (e) {
    reconnect(e?.message || '播放器初始化失败')
  }
}

const unlockAudio = async () => {
  if (!videoRef.value) return
  muted.value = false
  videoRef.value.muted = false
  try {
    await videoRef.value.play()
    needGesture.value = false
  } catch (_) {}
}

watch(
  () => props.streamUrl,
  () => {
    retryCount = 0
    start()
  },
)

onMounted(() => {
  start()
})

onUnmounted(() => {
  cleanup()
})
</script>

<style scoped>
.vh-player {
  position: relative;
  width: 100%;
  height: 100%;
  border-radius: 14px;
  overflow: hidden;
  background: #0f172a;
}
.vh-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.vh-mask {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px;
  text-align: center;
  color: #dbeafe;
  background: linear-gradient(180deg, rgba(15, 23, 42, 0.66), rgba(15, 23, 42, 0.82));
  font-size: 13px;
}
.vh-mask.err {
  color: #fecaca;
}
.vh-unlock {
  position: absolute;
  right: 12px;
  bottom: 12px;
  border: none;
  border-radius: 999px;
  background: rgba(37, 99, 235, 0.9);
  color: #fff;
  font-size: 12px;
  padding: 6px 12px;
  cursor: pointer;
}
</style>
