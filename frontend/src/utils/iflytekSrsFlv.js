/**
 * 纯前端直连模式：
 * - 若给出 HTTP-FLV 地址（http/https + .flv）直接播放
 * - 若给出 RTMP 地址（rtmp://host/app/stream），自动推断为 https://host/app/stream.flv
 * 注意：浏览器不能直接播放 RTMP，只能播放 HTTP-FLV。
 */

/**
 * @param {string} rtmpUrl 例如 rtmp://srs-pull.xf-yun.com/live/4339362
 * @returns {{ host: string, path: string } | null}
 */
export function parseRtmpUrl(rtmpUrl) {
  if (!rtmpUrl || typeof rtmpUrl !== 'string') return null
  const s = rtmpUrl.trim()
  if (!s.toLowerCase().startsWith('rtmp://')) return null
  const rest = s.slice(7)
  const i = rest.indexOf('/')
  if (i <= 0) return null
  const host = rest.slice(0, i)
  const path = rest.slice(i)
  if (!path || path === '/') return null
  return { host, path }
}

export function buildDirectHttpFlvUrl(rtmpUrl, protocol = 'https') {
  const p = parseRtmpUrl(rtmpUrl)
  if (!p) return ''
  const flvPath = p.path.endsWith('.flv') ? p.path : `${p.path}.flv`
  const scheme = protocol === 'http' ? 'http' : 'https'
  return `${scheme}://${p.host}${flvPath}`
}

/**
 * 将输入流地址解析成浏览器可播放的 HTTP-FLV 地址
 * @param {string} streamUrl 支持 rtmp://、http://、https://
 * @param {string} preferProtocol RTMP 转换时使用的协议（http/https）
 */
export function normalizeFlvPlayableUrl(streamUrl, preferProtocol = 'https') {
  if (!streamUrl || typeof streamUrl !== 'string') return ''
  const s = streamUrl.trim()
  if (!s) return ''
  if (/^https?:\/\//i.test(s)) {
    return s.toLowerCase().endsWith('.flv') ? s : `${s}.flv`
  }
  if (/^rtmp:\/\//i.test(s)) {
    return buildDirectHttpFlvUrl(s, preferProtocol)
  }
  return ''
}
