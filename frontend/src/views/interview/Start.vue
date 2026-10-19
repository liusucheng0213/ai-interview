<template>
  <div class="interview-setup">


    <!-- 自定义面试（个人资料 + 简历背景，置顶） -->
    <section class="custom-interview-card">
      <div class="custom-interview-card__shine" aria-hidden="true" />
      <header class="custom-interview-card__head">
        <div class="custom-interview-card__titles">
          <span class="custom-interview-card__eyebrow">可选 · 提升匹配度</span>
          <h2 class="custom-interview-card__title">自定义面试</h2>
          <p class="custom-interview-card__desc">
            将个人资料与简历摘要提供给本场面试，AI 会结合你的背景提问；可直接编辑，或点击右上方「从资料与简历同步」拉取最新内容。
          </p>
        </div>
        <el-button
          class="custom-interview-card__sync"
          type="primary"
          plain
          round
          size="small"
          @click="loadContextPreview"
          :loading="contextLoading"
        >
          从资料与简历同步
        </el-button>
      </header>
      <div class="custom-interview-card__body">
        <div class="custom-interview-card__field">
          <label class="custom-interview-card__label">个人资料摘要</label>
          <el-input
            v-model="contextDraft.profileText"
            type="textarea"
            :rows="3"
            maxlength="8000"
            show-word-limit
            placeholder="专业、简介、兴趣等"
            class="custom-interview-card__input"
          />
        </div>
        <div class="custom-interview-card__field">
          <label class="custom-interview-card__label">简历摘要</label>
          <el-input
            v-model="contextDraft.resumeText"
            type="textarea"
            :rows="5"
            maxlength="8000"
            show-word-limit
            placeholder="教育、工作、项目、技能等；无简历可先到「简历优化」上传或生成"
            class="custom-interview-card__input"
          />
        </div>
      </div>
    </section>

    <!-- 面试阶段选择 -->
    <div class="section section--compact">
      <h3 class="section-title">面试阶段</h3>
      <div class="stage-grid">
        <div 
          class="stage-card" 
          :class="{ active: interviewForm.stage === 'hr' }"
          @click="interviewForm.stage = 'hr'"
        >
          <div class="stage-icon">💼</div>
          <h4>业务面试</h4>
          <p>专业能力考核</p>
        </div>
        <div 
          class="stage-card" 
          :class="{ active: interviewForm.stage === 'final' }"
          @click="interviewForm.stage = 'final'"
        >
          <div class="stage-icon">🏆</div>
          <h4>终面</h4>
          <p>综合素质与团队匹配</p>
        </div>
      </div>
    </div>

    <!-- 面试形式选择 -->
    <div class="section section--compact">
      <h3 class="section-title">请选择你要体验的面试场景</h3>
      <div class="mode-grid">
        <div 
          class="mode-card" 
          :class="{ active: interviewForm.mode === 'text' }"
          @click="interviewForm.mode = 'text'"
        >
          <div class="mode-icon">📝</div>
          <h4>文本模拟</h4>
          <p>聊天框风格，对话式提问</p>
          <p>锻炼文字组织表达能力</p>
          <button class="select-btn" :class="{ selected: interviewForm.mode === 'text' }">
            {{ interviewForm.mode === 'text' ? '已选择' : '选择' }}
          </button>
        </div>
        <div 
          class="mode-card" 
          :class="{ active: interviewForm.mode === 'speech' }"
          @click="interviewForm.mode = 'speech'"
        >
          <div class="mode-icon">🎤</div>
          <h4>语音模拟</h4>
          <p>听语音提问，语音回答</p>
          <p>训练语速与语调</p>
          <button class="select-btn" :class="{ selected: interviewForm.mode === 'speech' }">
            {{ interviewForm.mode === 'speech' ? '已选择' : '选择' }}
          </button>
        </div>
        <div 
          class="mode-card" 
          :class="{ active: interviewForm.mode === 'video' }"
          @click="interviewForm.mode = 'video'"
        >
          <div class="mode-icon">🎥</div>
          <h4>视频模拟</h4>
          <p>AI 视频面试官出镜</p>
          <p>摄像头录制回答过程</p>
          <button class="select-btn" :class="{ selected: interviewForm.mode === 'video' }">
            {{ interviewForm.mode === 'video' ? '已选择' : '选择' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 面试难度选择 -->
    <div class="section section--compact">
      <h3 class="section-title">面试难度</h3>
      <div class="difficulty-grid">
        <div 
          class="difficulty-card" 
          :class="{ active: interviewForm.difficulty === 'entry' }"
          @click="interviewForm.difficulty = 'entry'"
        >
          <div class="difficulty-icon">🌱</div>
          <h4>入门级</h4>
          <p>基础问题，适合新手</p>
          <button class="select-btn" :class="{ selected: interviewForm.difficulty === 'entry' }">
            {{ interviewForm.difficulty === 'entry' ? '已选择' : '选择' }}
          </button>
        </div>
        <div 
          class="difficulty-card" 
          :class="{ active: interviewForm.difficulty === 'intermediate' }"
          @click="interviewForm.difficulty = 'intermediate'"
        >
          <div class="difficulty-icon">🚀</div>
          <h4>进阶级</h4>
          <p>中等难度，有一定基础</p>
          <button class="select-btn" :class="{ selected: interviewForm.difficulty === 'intermediate' }">
            {{ interviewForm.difficulty === 'intermediate' ? '已选择' : '选择' }}
          </button>
        </div>
        <div 
          class="difficulty-card" 
          :class="{ active: interviewForm.difficulty === 'expert' }"
          @click="interviewForm.difficulty = 'expert'"
        >
          <div class="difficulty-icon">🏆</div>
          <h4>专业级</h4>
          <p>高难度问题，专业人士</p>
          <button class="select-btn" :class="{ selected: interviewForm.difficulty === 'expert' }">
            {{ interviewForm.difficulty === 'expert' ? '已选择' : '选择' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 面试官风格 -->
    <div class="section section--compact">
      <h3 class="section-title">面试官风格</h3>
      <div class="style-grid">
        <div
          class="style-card"
          :class="{ active: interviewForm.interviewerStyle === 'rigorous' }"
          @click="interviewForm.interviewerStyle = 'rigorous'"
        >
          <div class="style-icon">📐</div>
          <h4>严谨型</h4>
          <p>重定义、重逻辑、重边界</p>
        </div>
        <div
          class="style-card"
          :class="{ active: interviewForm.interviewerStyle === 'pressure' }"
          @click="interviewForm.interviewerStyle = 'pressure'"
        >
          <div class="style-icon">🔥</div>
          <h4>压力型</h4>
          <p>追问更强，模拟高压场景</p>
        </div>
        <div
          class="style-card"
          :class="{ active: interviewForm.interviewerStyle === 'heuristic' }"
          @click="interviewForm.interviewerStyle = 'heuristic'"
        >
          <div class="style-icon">💡</div>
          <h4>启发型</h4>
          <p>循序引导，强调思考过程</p>
        </div>
      </div>
    </div>

    <!-- 语言策略 -->
    <div class="section section--compact">
      <h3 class="section-title">语言策略</h3>
      <el-select
        v-model="interviewForm.language"
        placeholder="请选择问答语言策略"
        style="width: 100%;"
        size="default"
      >
        <el-option label="中文" value="zh"></el-option>
        <el-option label="English" value="en"></el-option>
        <el-option label="中英双语" value="bilingual"></el-option>
      </el-select>
    </div>

    <!-- 岗位选择（job 表，可搜索） -->
    <div class="section section--compact">
      <h3 class="section-title">应聘岗位</h3>
      <JobPositionSelect
        v-model="interviewForm.job"
        :show-error="jobTouched && !interviewForm.job"
      />
    </div>

    <!-- 开始按钮 -->
    <div class="start-section">
      <button class="start-btn" @click="startInterview2" :disabled="!canStart">
        🚀 开始模拟面试
      </button>
    </div>

    <!-- 步骤二：无简历时提示上传或生成（居中悬浮窗） -->
    <Teleport to="body">
      <Transition name="resume-hint-fade">
        <div v-if="showResumeOnboarding" class="resume-onboard-overlay" @click.self="dismissResumeOnboard">
          <div class="resume-onboard-card" @click.stop>
            <button type="button" class="resume-onboard-close" @click="dismissResumeOnboard">×</button>
            <div class="resume-onboard-hero">
              <span class="resume-onboard-badge">第 2 步</span>
              <h3>补充一份简历</h3>
              <p>检测到尚未上传简历。上传或 AI 生成简历后，模拟面试可结合你的经历提问。</p>
            </div>
            <div class="resume-onboard-actions">
              <el-button type="primary" round @click="goResumeUpload">上传简历</el-button>
              <el-button round @click="goResumeGenerate">AI 生成简历</el-button>
              <el-button text type="info" @click="dismissResumeOnboard">知道了</el-button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { reactive, ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { startInterview, getInterviewContextPreview, getResumeHistory, getUserInfo, getInterviewJobs } from '@/api/endpoints'
import JobPositionSelect from '@/components/JobPositionSelect.vue'
import { notifyError, notifySuccess, notifyWarning } from '@/utils/appNotify'

const router = useRouter()
const loading = ref(false)
const jobTouched = ref(false)
const contextLoading = ref(false)
const showResumeOnboarding = ref(false)
const profileHintDismissed = ref(false)
const hasResumeOnServer = ref(true)
const contextDraft = reactive({
  profileText: '',
  resumeText: '',
})
const jobNameToIdMap = ref({})

// 面试配置表单
const interviewForm = reactive({ 
  job: '',              // 岗位
  stage: 'hr',          // 面试阶段：hr（业务面试）, final（终面）
  mode: 'text',         // 面试形式：text（文本）, speech（语音）, video（视频）
  difficulty: 'entry',  // 面试难度：entry（入门级）, intermediate（进阶级）, expert（专业级）
  interviewerStyle: 'rigorous', // 面试官风格：rigorous/pressure/heuristic
  language: 'zh'        // 语言策略：zh/en/bilingual
})

// 计算是否可以开始面试
const canStart = computed(() => {
  return !!(interviewForm.job && interviewForm.job.trim()) && interviewForm.mode && interviewForm.difficulty
})

const profileIncomplete = ref(false)

const profileIncompleteHint = computed(() => {
  if (profileHintDismissed.value) return false
  if (localStorage.getItem('account_type') === 'enterprise') return false
  return profileIncomplete.value
})

const checkProfileAndResume = async () => {
  if (localStorage.getItem('account_type') === 'enterprise') return
  try {
    const res = await getUserInfo()
    const u = res?.data ?? res
    const major = (u?.major || '').trim()
    const sig = (u?.signature || '').trim()
    const hobbies = (u?.hobbies || '').trim()
    profileIncomplete.value = !major && !sig && !hobbies
  } catch {
    profileIncomplete.value = false
  }
  try {
    const res = await getResumeHistory()
    const list = res?.data?.resumes ?? []
    hasResumeOnServer.value = Array.isArray(list) && list.length > 0
  } catch {
    hasResumeOnServer.value = false
  }
  if (
    !hasResumeOnServer.value &&
    localStorage.getItem('onboarding_resume_step') !== 'done'
  ) {
    showResumeOnboarding.value = true
  }
}

const dismissResumeOnboard = () => {
  localStorage.setItem('onboarding_resume_step', 'done')
  showResumeOnboarding.value = false
}

const goResumeUpload = () => {
  localStorage.setItem('onboarding_resume_step', 'done')
  showResumeOnboarding.value = false
  router.push({ path: '/interview/resume', query: { focus: 'upload' } })
}

const goResumeGenerate = () => {
  localStorage.setItem('onboarding_resume_step', 'done')
  showResumeOnboarding.value = false
  router.push({ path: '/interview/resume', query: { focus: 'generate' } })
}

const loadContextPreview = async () => {
  contextLoading.value = true
  try {
    const res = await getInterviewContextPreview()
    const payload = res?.data ?? res
    const inner = payload?.data !== undefined ? payload.data : payload
    contextDraft.profileText = inner?.profile_text ?? ''
    contextDraft.resumeText = inner?.resume_text ?? ''
  } catch (e) {
    console.error(e)
    notifyWarning('加载自定义面试背景失败，将使用空背景', '背景同步')
  } finally {
    contextLoading.value = false
  }
}

const loadJobIdMap = async () => {
  try {
    const res = await getInterviewJobs()
    const rows = Array.isArray(res?.jobs) ? res.jobs : []
    const nextMap = {}
    for (const row of rows) {
      const jobName = String(row?.job_name || '').trim()
      const jobId = Number(row?.job_id || 0)
      if (!jobName || !jobId) continue
      nextMap[jobName] = jobId
    }
    jobNameToIdMap.value = nextMap
  } catch {
    jobNameToIdMap.value = {}
  }
}

onMounted(async () => {
  await loadContextPreview()
  await loadJobIdMap()
  await checkProfileAndResume()
})

const startInterview2 = async () => {
  jobTouched.value = true
  if (!(interviewForm.job || '').trim()) {
    notifyError('请从岗位库中选择岗位后再开始面试', '岗位必选')
    return
  }
  if (!canStart.value) {
    notifyWarning('请完善面试形式与难度', '无法开始')
    return
  }
  
  loading.value = true
  
  try {
    const selectedJobName = (interviewForm.job || '').trim()
    const selectedJobId = Number(jobNameToIdMap.value[selectedJobName] || 0)
    if (!selectedJobId) {
      notifyError('岗位 ID 解析失败，请重新选择岗位后再试', '模拟面试')
      return
    }
    // 调用后端开始面试接口，传递面试形式和难度
    const data = await startInterview(
      selectedJobId,
      interviewForm.mode,
      interviewForm.difficulty,
      interviewForm.interviewerStyle,
      interviewForm.language,
      contextDraft.profileText.trim() || undefined,
      contextDraft.resumeText.trim() || undefined
    )
    
    if (data.interview_id) {
      // 存储面试 ID 和配置
      localStorage.setItem('current_interview_id', data.interview_id)
      localStorage.setItem('interview-config', JSON.stringify(interviewForm))
      if (data.job_id) {
        localStorage.setItem('active_job_id', String(data.job_id))
      }
      
      // 🌟 关键：保存第一个问题到 localStorage，供 Chat.vue 使用
      if (data.question) {
        localStorage.setItem('first_question', data.question)
        console.log('💾 已保存第一个问题:', data.question)
      }
      
      notifySuccess('面试已开始', '模拟面试')
      router.push('/interview/chat')
    } else {
      notifyError(data.detail || '启动面试失败', '模拟面试')
    }
  } catch (err) {
    console.error('启动面试失败:', err)
    const msg =
      err?.response?.data?.detail ||
      err?.message ||
      (typeof err === 'string' ? err : '') ||
      '请检查网络与登录状态后重试'
    notifyError(`启动面试失败：${msg}`, '模拟面试')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.interview-setup {
  max-width: 1040px;
  margin: 0 auto;
  padding: 24px 16px 32px;
}



/* ========== 自定义面试（置顶卡片） ========== */
.custom-interview-card {
  position: relative;
  margin-bottom: 28px;
  border-radius: var(--radius-lg);
  background: var(--gradient-card);
  border: 1px solid rgba(37, 99, 235, 0.2);
  box-shadow: var(--shadow-md);
  overflow: hidden;
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.custom-interview-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
}

.custom-interview-card__shine {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: var(--gradient-primary);
  opacity: 1;
}

.custom-interview-card__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  padding: 24px 28px 20px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.9);
  background: linear-gradient(180deg, rgba(239, 246, 255, 0.8) 0%, transparent 100%);
}

.custom-interview-card__titles {
  min-width: 0;
}

.custom-interview-card__eyebrow {
  display: block;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.06em;
  color: var(--color-primary);
  text-transform: uppercase;
  margin-bottom: 8px;
}

.custom-interview-card__title {
  margin: 0 0 10px;
  font-size: 20px;
  font-weight: 700;
  color: var(--color-text-primary);
  letter-spacing: 0.02em;
}

.custom-interview-card__desc {
  margin: 0;
  font-size: 15px;
  line-height: 1.6;
  color: var(--color-text-secondary);
  max-width: 52em;
}

.custom-interview-card__sync {
  flex-shrink: 0;
  background: var(--gradient-primary) !important;
  border-color: transparent !important;
  color: #fff !important;
}

.custom-interview-card__body {
  padding: 20px 28px 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.custom-interview-card__field {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.custom-interview-card__label {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-secondary);
}

.custom-interview-card__input :deep(.el-textarea__inner) {
  border-radius: var(--radius-md);
  font-size: 15px;
  line-height: 1.5;
  border: 1px solid var(--color-border);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
  background: rgba(255, 255, 255, 0.8);
}

.custom-interview-card__input :deep(.el-textarea__inner:focus) {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.2);
}

.section {
  margin-bottom: 28px;
}

.section--compact .section-title {
  margin-bottom: 16px;
}

.section-title {
  font-size: 18px;
  color: var(--color-text-primary);
  margin-bottom: 16px;
  font-weight: 700;
  position: relative;
  padding-left: 12px;
}

.section-title::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 4px;
  height: 20px;
  background: var(--gradient-primary);
  border-radius: 4px;
}

/* 面试阶段 */
.stage-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

.stage-card {
  background: var(--gradient-card);
  border: 2px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 24px 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
  position: relative;
  overflow: hidden;
}

.stage-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: var(--gradient-success);
  transform: scaleX(0);
  transition: transform 0.3s ease;
}

.stage-card:hover {
  border-color: var(--color-success);
  transform: translateY(-6px);
  box-shadow: 0 8px 24px rgba(16, 185, 129, 0.3);
}

.stage-card:hover::before {
  transform: scaleX(1);
}

.stage-card.active {
  border-color: var(--color-success);
  background: linear-gradient(135deg, #f0f9f4 0%, #e8f5e9 100%);
  box-shadow: 0 10px 28px rgba(16, 185, 129, 0.4);
}

.stage-card.active::before {
  transform: scaleX(1);
}

.stage-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.stage-card h4 {
  font-size: 18px;
  color: var(--color-text-primary);
  margin: 12px 0;
  font-weight: 700;
}

.stage-card p {
  font-size: 14px;
  color: var(--color-text-secondary);
  margin: 0;
  line-height: 1.5;
}

/* 面试形式 */
.mode-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

.mode-card {
  background: var(--gradient-card);
  border: 2px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 24px 16px 28px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
  position: relative;
  overflow: hidden;
}

.mode-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: var(--gradient-primary);
  transform: scaleX(0);
  transition: transform 0.3s ease;
}

.mode-card:hover {
  border-color: var(--color-primary);
  transform: translateY(-6px);
  box-shadow: 0 8px 24px rgba(37, 99, 235, 0.3);
}

.mode-card:hover::before {
  transform: scaleX(1);
}

.mode-card.active {
  border-color: var(--color-primary);
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
  box-shadow: 0 10px 28px rgba(37, 99, 235, 0.4);
}

.mode-card.active::before {
  transform: scaleX(1);
}

.mode-icon {
  font-size: 44px;
  margin-bottom: 12px;
}

.mode-card h4 {
  font-size: 18px;
  color: var(--color-text-primary);
  margin: 12px 0 8px;
  font-weight: 700;
}

.mode-card p {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin: 4px 0;
  line-height: 1.5;
}

.select-btn {
  margin-top: 18px;
  padding: 10px 28px;
  border: 2px solid var(--color-primary);
  background: #fff;
  color: var(--color-primary);
  border-radius: 999px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  transition: all 0.3s;
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.15);
}

.select-btn:hover {
  background: var(--color-primary);
  color: #fff;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
}

.select-btn.selected {
  background: var(--color-primary);
  color: #fff;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
}

.mode-card:hover .select-btn {
  background: var(--color-primary);
  color: #fff;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
}

.mode-card.active .select-btn {
  background: var(--color-primary);
  color: #fff;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
}

/* 面试难度 */
.difficulty-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

.difficulty-card {
  background: var(--gradient-card);
  border: 2px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 24px 16px 28px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
  position: relative;
  overflow: hidden;
}

.difficulty-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: var(--gradient-warning);
  transform: scaleX(0);
  transition: transform 0.3s ease;
}

.difficulty-card:hover {
  border-color: var(--color-warning);
  transform: translateY(-6px);
  box-shadow: 0 8px 24px rgba(245, 158, 11, 0.3);
}

.difficulty-card:hover::before {
  transform: scaleX(1);
}

.difficulty-card.active {
  border-color: var(--color-warning);
  background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
  box-shadow: 0 10px 28px rgba(245, 158, 11, 0.4);
}

.difficulty-card.active::before {
  transform: scaleX(1);
}

.difficulty-icon {
  font-size: 44px;
  margin-bottom: 12px;
}

.difficulty-card h4 {
  font-size: 18px;
  color: var(--color-text-primary);
  margin: 12px 0 8px;
  font-weight: 700;
}

.difficulty-card p {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin: 4px 0;
  line-height: 1.5;
}

/* 面试官风格 */
.style-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

.style-card {
  background: var(--gradient-card);
  border: 2px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 24px 16px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
  position: relative;
  overflow: hidden;
}

.style-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: var(--gradient-primary);
  transform: scaleX(0);
  transition: transform 0.3s ease;
}

.style-card:hover {
  border-color: var(--color-primary);
  transform: translateY(-6px);
  box-shadow: 0 8px 24px rgba(37, 99, 235, 0.3);
}

.style-card:hover::before {
  transform: scaleX(1);
}

.style-card.active {
  border-color: var(--color-primary);
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
  box-shadow: 0 10px 28px rgba(37, 99, 235, 0.4);
}

.style-card.active::before {
  transform: scaleX(1);
}

.style-icon {
  font-size: 40px;
  margin-bottom: 10px;
}

.style-card h4 {
  font-size: 18px;
  color: var(--color-text-primary);
  margin: 10px 0 8px;
  font-weight: 700;
}

.style-card p {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin: 4px 0;
  line-height: 1.5;
}

/* 岗位选择 */
.section :deep(.el-select) {
  width: 100%;
}

.section :deep(.el-select .el-input__wrapper) {
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.section :deep(.el-select .el-input__wrapper.is-focus) {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.2);
}

.tech-stack-hint {
  margin-top: 12px;
  font-size: 14px;
  color: var(--color-text-secondary);
  line-height: 1.5;
}

.tech-stack-label {
  color: var(--color-text-muted);
  margin-right: 8px;
}

/* 开始按钮 */
.start-section {
  text-align: center;
  margin-top: 40px;
  margin-bottom: 24px;
}

.start-btn {
  background: var(--gradient-primary);
  color: #fff;
  border: none;
  padding: 20px 64px;
  border-radius: 999px;
  font-size: 18px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 10px 32px rgba(37, 99, 235, 0.4);
  position: relative;
  overflow: hidden;
}

.start-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
  transition: left 0.6s ease;
}

.start-btn:hover:not(:disabled) {
  transform: translateY(-6px);
  box-shadow: 0 16px 48px rgba(37, 99, 235, 0.5);
}

.start-btn:hover::before {
  left: 100%;
}

.start-btn:disabled {
  background: #cbd5e1;
  cursor: not-allowed;
  box-shadow: none;
  transform: none;
}

.start-btn:disabled::before {
  display: none;
}

@media (max-width: 720px) {
  .custom-interview-card__head {
    flex-direction: column;
    align-items: stretch;
  }
  .custom-interview-card__sync {
    align-self: flex-start;
  }
}
</style>
