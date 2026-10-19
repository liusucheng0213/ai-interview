<template>
  <div class="app-layout">
    <!-- 左侧导航栏 -->
    <aside class="app-sidebar">
      <!-- Logo 品牌区 -->
      <div class="sidebar-brand">
        <div class="brand-icon-wrapper">
          <span class="brand-icon">⚡</span>
        </div>
        <div class="brand-text">
          <span class="brand-title">AI 面试官</span>
          <span class="brand-sub">模拟面试评测系统</span>
        </div>
      </div>

      <!-- 导航菜单 -->
      <nav class="sidebar-nav">
        <div class="nav-section-label">主功能</div>
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ active: isActive(item) }"
        >
          <span class="nav-icon">{{ item.icon }}</span>
          <span class="nav-label">{{ item.label }}</span>
          <span v-if="item.badge" class="nav-badge">{{ item.badge }}</span>
        </router-link>
      </nav>

      <!-- 底部用户信息 -->
      <div class="sidebar-footer">
        <div class="user-card">
          <div class="user-avatar" :class="{ 'user-avatar--emoji': sidebarAvatarIsEmoji }">{{ sidebarAvatar }}</div>
          <div class="user-info">
            <div class="user-name">{{ username }}</div>
            <div class="user-role">{{ accountType === 'enterprise' ? '企业用户' : '求职者' }}</div>
          </div>
          <button class="logout-btn" @click="handleLogout" title="退出登录">⏻</button>
        </div>
      </div>
    </aside>

    <!-- 主内容区 -->
    <main class="app-main">
      <router-view v-slot="{ Component }">
        <transition name="page-shell" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <!-- 步骤一：登录后进入首页 — 完善个人信息（居中悬浮窗） -->
    <Teleport to="body">
      <Transition name="onboard-float">
        <div
          v-if="showProfileOnboarding"
          class="onboarding-overlay"
          role="presentation"
          @click.self="dismissProfileLater"
        >
          <div
            class="onboarding-float onboarding-float--center"
            role="dialog"
            aria-modal="true"
            aria-labelledby="onboard-profile-title"
            @click.stop
          >
            <button type="button" class="onboarding-float__dismiss" title="稍后再说" @click="dismissProfileLater">×</button>
            <div class="onboarding-float__hero">
              <div class="onboarding-float__icon">👤</div>
              <div>
                <span class="onboarding-float__badge">第 1 步</span>
                <h3 id="onboard-profile-title" class="onboarding-float__title">先完善个人信息</h3>
                <p class="onboarding-float__sub">
                  补充专业、简介与兴趣后，模拟面试能更贴合你的背景提问。此步骤可随时跳过。
                </p>
              </div>
            </div>
            <div class="onboarding-float__body-text">
              <p>进入「个人中心」即可编辑；完善后本提示不再出现。</p>
            </div>
            <div class="onboarding-float__actions onboarding-float__actions--split">
              <el-button type="primary" round @click="goProfileFromOnboard">去完善</el-button>
              <el-button round @click="dismissProfileLater">稍后再说</el-button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getUserInfo } from '@/api/endpoints'
import { notifyInfo } from '@/utils/appNotify'

const router = useRouter()
const route = useRoute()
const username = ref('用户')
const sidebarAvatar = ref('')
const accountType = ref(localStorage.getItem('account_type') || 'personal')
const showProfileOnboarding = ref(false)

const sidebarAvatarIsEmoji = computed(() => {
  const s = sidebarAvatar.value || ''
  if (!s || s.length > 2) return false
  return /[^\x00-\x7F]/.test(s)
})

const profileLooksIncomplete = (u) => {
  if (!u) return true
  const major = (u.major || '').trim()
  const sig = (u.signature || '').trim()
  const hobbies = (u.hobbies || '').trim()
  return !major && !sig && !hobbies
}

/** 步骤一：仅首页 + 登录后会话标记 + 资料未完成 + 未选择「去完善/稍后再说」 */
const evaluateProfileOnboarding = async () => {
  showProfileOnboarding.value = false
  if (accountType.value === 'enterprise') return
  if (route.path !== '/') return
  if (sessionStorage.getItem('profile_onboard_pending') !== '1') return
  const step = localStorage.getItem('onboarding_profile_step')
  if (step === 'went' || step === 'skipped') return
  try {
    const res = await getUserInfo()
    const user = res?.data ?? res
    if (profileLooksIncomplete(user)) {
      showProfileOnboarding.value = true
    }
  } catch {
    /* 忽略 */
  }
}

const dismissProfileLater = () => {
  sessionStorage.removeItem('profile_onboard_pending')
  localStorage.setItem('onboarding_profile_step', 'skipped')
  showProfileOnboarding.value = false
}

const goProfileFromOnboard = () => {
  sessionStorage.removeItem('profile_onboard_pending')
  localStorage.setItem('onboarding_profile_step', 'went')
  showProfileOnboarding.value = false
  router.push('/interview/profile')
}

const refreshSidebarUser = async () => {
  const cachedName = localStorage.getItem('ai-interview-user')
  if (cachedName) username.value = cachedName
  const cachedAv = localStorage.getItem('user-sidebar-avatar')
  if (cachedAv) sidebarAvatar.value = cachedAv
  else if (cachedName) sidebarAvatar.value = cachedName.charAt(0).toUpperCase()

  try {
    const res = await getUserInfo()
    const u = res?.data || res
    if (u?.username) {
      username.value = u.username
      localStorage.setItem('ai-interview-user', u.username)
    }
    accountType.value = u?.account_type || accountType.value || 'personal'
    localStorage.setItem('account_type', accountType.value)
    const av = (u?.avatar || '').trim().slice(0, 2)
    if (av) {
      sidebarAvatar.value = av
      localStorage.setItem('user-sidebar-avatar', av)
    } else if (username.value) {
      sidebarAvatar.value = username.value.charAt(0).toUpperCase()
      localStorage.setItem('user-sidebar-avatar', sidebarAvatar.value)
    }
  } catch {
    /* 未登录或接口失败时沿用本地缓存 */
  }
  await evaluateProfileOnboarding()
}

const onProfileUpdated = async () => {
  await refreshSidebarUser()
  await evaluateProfileOnboarding()
}

const navItems = computed(() => {
  if (accountType.value === 'enterprise') {
    return [
      { icon: '🏠', label: '首页', path: '/', match: ['/'] },
      { icon: '🏢', label: '企业管理', path: '/company', match: ['/company'] },
      { icon: '📖', label: '知识库', path: '/interview/knowledge', match: ['/interview/knowledge', '/interview/question-bank'] },
      { icon: '👤', label: '个人中心', path: '/interview/profile', match: ['/interview/profile'] },
    ]
  }
  return [
    { icon: '🏠', label: '首页',        path: '/',                    match: ['/'] },
    { icon: '🤖', label: '模拟面试',    path: '/interview/start',     match: ['/interview/start'] },
    { icon: '🕐', label: '面试历史',    path: '/interview/history',   match: ['/interview/history'] },
    { icon: '📄', label: '简历优化',    path: '/interview/resume',    match: ['/interview/resume'] },
    { icon: '📖', label: '知识库 & 题库', path: '/interview/knowledge', match: ['/interview/knowledge', '/interview/question-bank'] },
    { icon: '📈', label: '成长轨迹',    path: '/interview/growth',    match: ['/interview/growth'] },
    { icon: '👤', label: '个人中心',    path: '/interview/profile',   match: ['/interview/profile'] },
  ]
})

const isActive = (item) => {
  return item.match.some(p => route.path === p || route.path.startsWith(p + '/'))
}

watch(
  () => route.path,
  () => {
    evaluateProfileOnboarding()
  },
)

onMounted(() => {
  refreshSidebarUser()
  window.addEventListener('user-profile-updated', onProfileUpdated)
})

onUnmounted(() => {
  window.removeEventListener('user-profile-updated', onProfileUpdated)
})

const handleLogout = () => {
  localStorage.removeItem('ai-interview-user')
  localStorage.removeItem('user-sidebar-avatar')
  localStorage.removeItem('token')
  localStorage.removeItem('account_type')
  localStorage.removeItem('current_interview_id')
  localStorage.removeItem('interview-config')
  localStorage.removeItem('first_question')
  notifyInfo('已退出登录', '账号')
  router.push('/login')
}
</script>

<style scoped>
/* ==================== 整体布局 ==================== */
.app-layout {
  display: flex;
  height: 100vh;
  background: linear-gradient(145deg, #f0f9ff 0%, #e8f0fe 40%, #f1f5f9 100%);
}

/* ==================== 左侧导航栏 ==================== */
.app-sidebar {
  width: 228px;
  flex-shrink: 0;
  background: linear-gradient(168deg, #1e3a5f 0%, #2c528c 22%, #3d6fb5 48%, #2563eb 72%, #1e4976 100%);
  background-size: 100% 200%;
  animation: sidebar-gradient-flow 24s ease-in-out infinite alternate;
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
  border-right: 1px solid rgba(255, 255, 255, 0.08);
  position: relative;
  box-shadow: 4px 0 24px rgba(30, 58, 95, 0.22);
}

@keyframes sidebar-gradient-flow {
  0% { background-position: 0% 0%; }
  100% { background-position: 0% 100%; }
}

/* 顶部高光装饰 */
.app-sidebar::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 260px;
  background: radial-gradient(ellipse at 30% 0%, rgba(255,255,255,0.12) 0%, transparent 65%);
  pointer-events: none;
}

/* 底部暗角 */
.app-sidebar::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 120px;
  background: linear-gradient(to top, rgba(10,20,60,0.25), transparent);
  pointer-events: none;
}

/* ==================== Logo 品牌区 ==================== */
.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 24px 20px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.12);
  position: relative;
  z-index: 1;
}

.brand-icon-wrapper {
  width: 40px;
  height: 40px;
  border-radius: 11px;
  background: rgba(255, 255, 255, 0.22);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  flex-shrink: 0;
  box-shadow: 0 2px 10px rgba(0,0,0,0.18), inset 0 1px 0 rgba(255,255,255,0.3);
  backdrop-filter: blur(4px);
}

.brand-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow: hidden;
}

.brand-title {
  font-size: 15px;
  font-weight: 700;
  color: rgba(255,255,255,0.95);
  letter-spacing: 0.5px;
  white-space: nowrap;
}

.brand-sub {
  font-size: 10px;
  color: rgba(255,255,255,0.55);
  white-space: nowrap;
  letter-spacing: 0.2px;
}

/* ==================== 导航菜单 ==================== */
.sidebar-nav {
  flex: 1;
  overflow-y: auto;
  padding: 14px 10px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  position: relative;
  z-index: 1;
}

.sidebar-nav::-webkit-scrollbar { width: 0; }

.nav-section-label {
  font-size: 10px;
  font-weight: 600;
  color: rgba(255,255,255,0.35);
  text-transform: uppercase;
  letter-spacing: 1px;
  padding: 0 10px;
  margin-bottom: 6px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 9px;
  text-decoration: none;
  color: rgba(255,255,255,0.72);
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s ease;
  position: relative;
  cursor: pointer;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.13);
  color: rgba(255,255,255,0.96);
}

.nav-item.active {
  background: rgba(255, 255, 255, 0.20);
  color: #ffffff;
  font-weight: 600;
  box-shadow: 0 2px 10px rgba(0,0,0,0.12);
}

/* 激活项左侧亮条 */
.nav-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 55%;
  background: rgba(255,255,255,0.85);
  border-radius: 0 3px 3px 0;
}

.nav-icon {
  font-size: 16px;
  flex-shrink: 0;
  width: 20px;
  text-align: center;
  filter: drop-shadow(0 1px 2px rgba(0,0,0,0.2));
}

.nav-label {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  letter-spacing: 0.2px;
}

.nav-badge {
  background: rgba(255,255,255,0.25);
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  padding: 1px 7px;
  border-radius: 20px;
}

/* ==================== 底部用户信息 ==================== */
.sidebar-footer {
  padding: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(0, 0, 0, 0.12);
  position: relative;
  z-index: 1;
}

.user-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 10px;
  border-radius: 9px;
  background: rgba(255, 255, 255, 0.08);
  transition: background 0.2s;
}

.user-card:hover {
  background: rgba(255, 255, 255, 0.14);
}

.user-avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: rgba(255,255,255,0.25);
  color: #fff;
  font-size: 14px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 2px 6px rgba(0,0,0,0.2);
  line-height: 1;
}

.user-avatar--emoji {
  font-size: 19px;
  font-weight: 500;
}

.user-info {
  flex: 1;
  overflow: hidden;
}

.user-name {
  font-size: 13px;
  font-weight: 600;
  color: rgba(255,255,255,0.92);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-role {
  font-size: 11px;
  color: rgba(255,255,255,0.48);
  margin-top: 1px;
}

.logout-btn {
  background: none;
  border: none;
  color: rgba(255,255,255,0.45);
  font-size: 18px;
  cursor: pointer;
  padding: 4px 6px;
  border-radius: 6px;
  transition: all 0.2s;
  line-height: 1;
  flex-shrink: 0;
}

.logout-btn:hover {
  color: #fca5a5;
  background: rgba(255, 100, 100, 0.18);
}

/* ==================== 主内容区 ==================== */
.app-main {
  flex: 1;
  overflow-y: auto;
  min-height: 100vh;
  padding: clamp(16px, 2.5vw, 28px) clamp(16px, 2.8vw, 32px) 32px;
  background:
    radial-gradient(ellipse 80% 50% at 50% -20%, rgba(59, 130, 246, 0.06), transparent),
    linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
  position: relative;
  z-index: 1;
}

.page-shell-enter-active,
.page-shell-leave-active {
  transition: opacity 0.28s ease, transform 0.28s ease;
}
.page-shell-enter-from,
.page-shell-leave-to {
  opacity: 0;
  transform: translateY(8px);
}

/* 新手引导步骤一：全屏遮罩 + 居中悬浮窗 */
.onboarding-overlay {
  position: fixed;
  inset: 0;
  z-index: 5000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(15, 23, 42, 0.48);
  backdrop-filter: blur(8px);
}

.onboarding-float {
  position: relative;
  width: min(420px, 100%);
  max-height: min(88vh, 520px);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  border-radius: 20px;
  background: linear-gradient(165deg, #ffffff 0%, #f8fafc 55%, #f1f5f9 100%);
  border: 1px solid rgba(148, 163, 184, 0.35);
  box-shadow:
    0 4px 6px -1px rgba(15, 23, 42, 0.06),
    0 28px 60px -16px rgba(30, 58, 95, 0.35),
    inset 0 1px 0 rgba(255, 255, 255, 0.9);
}

.onboarding-float--center {
  animation: onboard-pop 0.4s cubic-bezier(0.34, 1.35, 0.64, 1);
}

@keyframes onboard-pop {
  from {
    opacity: 0;
    transform: scale(0.94) translateY(12px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.onboarding-float__body-text {
  padding: 0 22px 8px;
  font-size: 13px;
  line-height: 1.6;
  color: #475569;
}

.onboarding-float__actions--split {
  justify-content: center;
  gap: 12px;
}
.onboarding-float__dismiss {
  position: absolute;
  top: 10px;
  right: 12px;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 10px;
  background: rgba(15, 23, 42, 0.06);
  color: #64748b;
  font-size: 22px;
  line-height: 1;
  cursor: pointer;
  z-index: 2;
  transition: background 0.2s, color 0.2s;
}
.onboarding-float__dismiss:hover {
  background: rgba(239, 68, 68, 0.12);
  color: #b91c1c;
}
.onboarding-float__hero {
  display: flex;
  gap: 14px;
  padding: 20px 44px 16px 20px;
  background: linear-gradient(135deg, #1e3a5f 0%, #2563eb 48%, #3b82f6 100%);
  color: #fff;
}
.onboarding-float__icon {
  flex-shrink: 0;
  width: 44px;
  height: 44px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.18);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.25);
}
.onboarding-float__badge {
  display: inline-block;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  opacity: 0.85;
  margin-bottom: 6px;
}
.onboarding-float__title {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 0.02em;
  line-height: 1.35;
}
.onboarding-float__sub {
  margin: 8px 0 0;
  font-size: 12px;
  line-height: 1.5;
  opacity: 0.92;
  font-weight: 400;
}
.onboarding-float__steps {
  margin: 0;
  padding: 14px 18px 6px;
  list-style: none;
  flex: 1;
  overflow-y: auto;
}
.onboarding-float__steps li {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  font-size: 12.5px;
  line-height: 1.5;
  color: #334155;
  margin-bottom: 10px;
}
.onboarding-float__num {
  flex-shrink: 0;
  width: 22px;
  height: 22px;
  border-radius: 8px;
  background: linear-gradient(135deg, #e0f2fe 0%, #dbeafe 100%);
  color: #1d4ed8;
  font-size: 11px;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 1px;
}
.onboarding-float__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  padding: 12px 16px 16px;
  border-top: 1px solid rgba(226, 232, 240, 0.9);
  background: rgba(248, 250, 252, 0.85);
}
.onboard-float-enter-active,
.onboard-float-leave-active {
  transition: opacity 0.32s ease;
}
.onboard-float-enter-from,
.onboard-float-leave-to {
  opacity: 0;
}
</style>
