<template>
  <div class="profile-page">
    <!-- 顶部展示卡：头像 + 签名 + 兴趣 -->
    <section class="profile-hero">
      <div class="profile-hero__bg" aria-hidden="true"></div>
      <div class="profile-hero__inner">
        <div class="profile-avatar-wrap">
          <div class="profile-avatar-ring">
            <span class="profile-avatar-emoji">{{ displayAvatar }}</span>
          </div>
          <p class="profile-avatar-hint">点击下列表情更换头像</p>
        </div>
        <div class="profile-hero__text">
          <h1 class="profile-display-name">{{ userProfile.username || '用户' }}</h1>
          <p v-if="userProfile.signature" class="profile-signature">「 {{ userProfile.signature }} 」</p>
          <p v-else class="profile-signature muted">写一句个性签名，让面试官更了解你</p>
          <div v-if="hobbyTags.length" class="profile-hobby-row">
            <span class="profile-hobby-label">兴趣爱好</span>
            <span v-for="(t, i) in hobbyTags" :key="i" class="profile-hobby-tag">{{ t }}</span>
          </div>
        </div>
      </div>

      <div class="avatar-picker">
        <button
          v-for="em in avatarChoices"
          :key="em"
          type="button"
          class="avatar-pick-btn"
          :class="{ active: userProfile.avatar === em }"
          @click="userProfile.avatar = em"
        >
          {{ em }}
        </button>
      </div>
    </section>

    <!-- 面试统计 -->
    <section class="profile-stats">
      <div class="stat-card" v-for="s in statCards" :key="s.key">
        <div class="stat-card__icon">{{ s.icon }}</div>
        <div class="stat-card__num">{{ s.value }}</div>
        <div class="stat-card__label">{{ s.label }}</div>
      </div>
    </section>

    <!-- 资料编辑 -->
    <el-card class="profile-form-card" shadow="hover">
      <template #header>
        <div class="card-head">
          <span class="card-head-title">编辑资料</span>
          <span class="card-head-sub">保存后将同步到侧栏头像展示</span>
        </div>
      </template>
      <el-form :model="userProfile" label-width="100px" class="profile-form">
        <el-form-item label="用户名">
          <el-input v-model="userProfile.username" disabled />
        </el-form-item>
        <el-form-item label="头像">
          <el-input v-model="userProfile.avatar" maxlength="8" show-word-limit placeholder="可选：直接输入 emoji" clearable />
        </el-form-item>
        <el-form-item label="性别">
          <el-radio-group v-model="userProfile.gender">
            <el-radio value="male">男</el-radio>
            <el-radio value="female">女</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="专业">
          <el-input v-model="userProfile.major" placeholder="在读/所学专业" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="userProfile.email" type="email" />
        </el-form-item>
        <el-form-item label="兴趣爱好">
          <el-input
            v-model="userProfile.hobbies"
            type="textarea"
            :rows="3"
            placeholder="用顿号、逗号或换行分隔，例如：跑步、摄影、开源"
            maxlength="500"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="个性签名">
          <el-input v-model="userProfile.signature" type="textarea" :rows="2" maxlength="255" show-word-limit placeholder="一句话介绍自己" />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="userProfile.password" type="password" placeholder="不修改请留空" show-password />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="saveProfile">保存修改</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, onMounted, ref, computed } from 'vue'
import { saveUserProfile, getInterviewStats, getUserInfo, getInterviewJobs } from '@/api/endpoints'
import { notifyError, notifySuccess } from '@/utils/appNotify'

const avatarChoices = ['🙂', '😎', '🧑‍💻', '👩‍💻', '🦁', '🐱', '🚀', '⭐', '🎯', '💼', '📚', '🎨']

const userProfile = reactive({
  username: '',
  email: '',
  password: '',
  gender: 'male',
  major: '',
  signature: '',
  avatar: '',
  hobbies: '',
})
const loading = ref(false)

const stats = reactive({
  textCount: 0,
  speechCount: 0,
  videoCount: 0,
  questionCount: 0,
})

const statCards = computed(() => [
  { key: 'text', icon: '✍️', label: '文本面试', value: stats.textCount },
  { key: 'speech', icon: '🎤', label: '语音面试', value: stats.speechCount },
  { key: 'video', icon: '🎬', label: '视频面试', value: stats.videoCount },
  { key: 'q', icon: '📝', label: '试题练习', value: stats.questionCount },
])

const displayAvatar = computed(() => {
  const a = (userProfile.avatar || '').trim()
  if (a) return a.slice(0, 2)
  const name = userProfile.username || ''
  return name ? name.charAt(0).toUpperCase() : '👤'
})

const hobbyTags = computed(() => {
  const raw = (userProfile.hobbies || '').trim()
  if (!raw) return []
  return raw
    .split(/[,，、;\n]+/)
    .map((s) => s.trim())
    .filter(Boolean)
    .slice(0, 12)
})

onMounted(() => {
  loadUserInfo()
  loadInterviewStats()
})

const loadUserInfo = async () => {
  try {
    const res = await getUserInfo()
    const userInfo = res.data || res
    if (userInfo) {
      userProfile.username = userInfo.username || ''
      userProfile.email = userInfo.email || ''
      userProfile.gender = userInfo.gender || 'male'
      userProfile.major = userInfo.major || ''
      userProfile.signature = userInfo.signature || ''
      userProfile.avatar = userInfo.avatar || ''
      userProfile.hobbies = userInfo.hobbies || ''
      syncSidebar(userInfo.username, userProfile.avatar)
    }
  } catch (err) {
    console.error('获取用户信息失败:', err)
    const user = localStorage.getItem('ai-interview-user')
    userProfile.username = user || ''
  }
}

const syncSidebar = (name, avatar) => {
  if (name) localStorage.setItem('ai-interview-user', name)
  const disp = (avatar || '').trim().slice(0, 2) || (name || 'U').charAt(0).toUpperCase()
  localStorage.setItem('user-sidebar-avatar', disp)
  window.dispatchEvent(new Event('user-profile-updated'))
}

const loadInterviewStats = async () => {
  try {
    let jobId = Number(localStorage.getItem('active_job_id') || 0)
    if (!jobId) {
      const jobsRes = await getInterviewJobs()
      const first = Array.isArray(jobsRes?.jobs) ? jobsRes.jobs[0] : null
      jobId = Number(first?.job_id || 0)
      if (jobId) localStorage.setItem('active_job_id', String(jobId))
    }
    if (!jobId) {
      stats.textCount = 0
      stats.speechCount = 0
      stats.videoCount = 0
      stats.questionCount = 0
      return
    }
    const data = await getInterviewStats(jobId)
    if (data) {
      stats.textCount = data.text_count ?? 0
      stats.speechCount = data.speech_count ?? 0
      stats.videoCount = data.video_count ?? 0
      stats.questionCount = data.question_count ?? 0
    }
  } catch (err) {
    console.error('获取统计数据失败:', err)
    stats.textCount = 0
    stats.speechCount = 0
    stats.videoCount = 0
    stats.questionCount = 0
  }
}

const saveProfile = async () => {
  loading.value = true
  try {
    const updateData = {}
    if (userProfile.email !== undefined) updateData.email = userProfile.email
    if (userProfile.password) updateData.password = userProfile.password
    if (userProfile.gender) updateData.gender = userProfile.gender
    if (userProfile.major !== undefined) updateData.major = userProfile.major
    if (userProfile.signature !== undefined) updateData.signature = userProfile.signature
    if (userProfile.avatar !== undefined) updateData.avatar = (userProfile.avatar || '').trim().slice(0, 32) || null
    if (userProfile.hobbies !== undefined) updateData.hobbies = (userProfile.hobbies || '').trim().slice(0, 500) || null

    await saveUserProfile(updateData)
    notifySuccess('个人信息保存成功！', '个人中心')
    userProfile.password = ''
    syncSidebar(userProfile.username, userProfile.avatar)
    loadInterviewStats()
  } catch (err) {
    console.error('保存个人信息失败:', err)
    notifyError('保存失败，请重试', '个人中心')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.profile-page {
  max-width: 920px;
  margin: 0 auto;
  padding: 20px 20px 40px;
}

.profile-hero {
  position: relative;
  border-radius: 20px;
  overflow: hidden;
  margin-bottom: 22px;
  box-shadow: 0 16px 40px rgba(15, 23, 42, 0.1);
}

.profile-hero__bg {
  position: absolute;
  inset: 0;
  background: linear-gradient(125deg, #1e3a5f 0%, #2563eb 42%, #6366f1 78%, #8b5cf6 100%);
  background-size: 200% 200%;
  animation: hero-shift 14s ease-in-out infinite alternate;
}

@keyframes hero-shift {
  0% {
    background-position: 0% 40%;
  }
  100% {
    background-position: 100% 60%;
  }
}

.profile-hero__bg::after {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(ellipse 80% 60% at 20% 20%, rgba(255, 255, 255, 0.2), transparent 55%);
  pointer-events: none;
}

.profile-hero__inner {
  position: relative;
  z-index: 1;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 24px;
  padding: 28px 28px 20px;
  color: #fff;
}

.profile-avatar-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.profile-avatar-ring {
  width: 108px;
  height: 108px;
  border-radius: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.18);
  border: 2px solid rgba(255, 255, 255, 0.45);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.35);
  backdrop-filter: blur(8px);
}

.profile-avatar-emoji {
  font-size: 52px;
  line-height: 1;
  font-weight: 600;
  text-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.profile-avatar-hint {
  margin: 0;
  font-size: 11px;
  opacity: 0.75;
}

.profile-hero__text {
  flex: 1;
  min-width: 200px;
}

.profile-display-name {
  margin: 0 0 8px;
  font-size: 26px;
  font-weight: 800;
  letter-spacing: -0.02em;
}

.profile-signature {
  margin: 0 0 12px;
  font-size: 14px;
  line-height: 1.55;
  opacity: 0.92;
}

.profile-signature.muted {
  opacity: 0.65;
  font-style: italic;
}

.profile-hobby-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.profile-hobby-label {
  font-size: 12px;
  font-weight: 700;
  opacity: 0.8;
  margin-right: 4px;
}

.profile-hobby-tag {
  font-size: 12px;
  padding: 4px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.22);
  border: 1px solid rgba(255, 255, 255, 0.35);
}

.avatar-picker {
  position: relative;
  z-index: 1;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 0 20px 20px 20px;
}

.avatar-pick-btn {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  border: 2px solid transparent;
  background: rgba(255, 255, 255, 0.2);
  font-size: 22px;
  cursor: pointer;
  transition: transform 0.15s ease, border-color 0.15s ease, background 0.15s ease;
}

.avatar-pick-btn:hover {
  transform: scale(1.08);
  background: rgba(255, 255, 255, 0.32);
}

.avatar-pick-btn.active {
  border-color: #fff;
  background: rgba(255, 255, 255, 0.4);
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.15);
}

.profile-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin-bottom: 22px;
}

@media (max-width: 768px) {
  .profile-stats {
    grid-template-columns: repeat(2, 1fr);
  }
}

.stat-card {
  text-align: center;
  padding: 18px 12px;
  border-radius: 16px;
  background: linear-gradient(160deg, #ffffff 0%, #f1f5f9 100%);
  border: 1px solid rgba(226, 232, 240, 0.95);
  box-shadow: 0 6px 20px rgba(15, 23, 42, 0.05);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.stat-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 12px 28px rgba(37, 99, 235, 0.12);
}

.stat-card__icon {
  font-size: 22px;
  margin-bottom: 6px;
}

.stat-card__num {
  font-size: 26px;
  font-weight: 800;
  color: #2563eb;
  line-height: 1.2;
}

.stat-card__label {
  font-size: 12px;
  color: #64748b;
  margin-top: 4px;
}

.profile-form-card {
  border-radius: 16px;
  border: 1px solid rgba(226, 232, 240, 0.95);
}

.card-head {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.card-head-title {
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
}

.card-head-sub {
  font-size: 12px;
  color: #94a3b8;
}

.profile-form :deep(.el-form-item) {
  margin-bottom: 18px;
}
</style>
