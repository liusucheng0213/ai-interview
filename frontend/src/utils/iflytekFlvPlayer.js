import flvjs from 'flv.js'

/**
 * 将 HTTP-FLV 绑定到 video 元素（直播流）
 * @param {HTMLVideoElement} videoEl
 * @param {string} flvUrl 同源或已处理代理的 .flv 地址
 * @returns {() => void} destroy
 */
export function attachFlvLivePlayer(videoEl, flvUrl) {
  if (!videoEl || !flvUrl) {
    throw new Error('attachFlvLivePlayer: 缺少 video 或 url')
  }
  if (!flvjs.isSupported()) {
    throw new Error('当前浏览器不支持 flv.js（HTTP-FLV）播放')
  }

  const player = flvjs.createPlayer(
    {
      type: 'flv',
      url: flvUrl,
      isLive: true,
      hasAudio: true,
      hasVideo: true,
    },
    {
      enableWorker: false,
      // 低延迟配置：减少音画累计缓冲，提升口型同步性
      enableStashBuffer: false,
      stashInitialSize: 32,
      lazyLoad: false,
      autoCleanupSourceBuffer: true,
      autoCleanupMaxBackwardDuration: 8,
      autoCleanupMinBackwardDuration: 2,
      fixAudioTimestampGap: false,
      deferLoadAfterSourceOpen: false,
    },
  )

  // 明确要求浏览器尽快渲染音视频，降低“声音先出、嘴后动”
  videoEl.preload = 'auto'
  videoEl.playsInline = true
  videoEl.setAttribute('playsinline', 'true')
  videoEl.setAttribute('webkit-playsinline', 'true')

  player.attachMediaElement(videoEl)
  player.load()

  return () => {
    try {
      player.pause()
    } catch (_) {
      /* noop */
    }
    try {
      player.unload()
    } catch (_) {
      /* noop */
    }
    try {
      player.detachMediaElement()
    } catch (_) {
      /* noop */
    }
    try {
      player.destroy()
    } catch (_) {
      /* noop */
    }
  }
}
