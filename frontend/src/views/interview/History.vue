<template>
  <el-card class="section-card history-page-card">
    <template #header>
      <div class="history-card-head">
        <span class="history-card-title">面试历史记录</span>
        <span class="history-card-sub">得分、岗位、时间与强弱项一览</span>
      </div>
    </template>
    <el-table :data="historyList" class="history-table" v-loading="loading" stripe>
      <el-table-column prop="job" label="应聘岗位" min-width="160" />
      <el-table-column prop="level" label="面试难度" width="110">
        <template #default="scope">
          <el-tag :type="getDifficultyTag(scope.row.level)" size="small">{{ scope.row.level }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="mode" label="面试形式" width="100">
        <template #default="scope">
          <el-tag type="info" size="small">{{ getModeLabel(scope.row.mode) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="time" label="面试时间" min-width="180" />
      <el-table-column prop="status" label="状态" width="90">
        <template #default="scope">
          <el-tag type="success" size="small">{{ scope.row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="综合得分" width="100" align="center">
        <template #default="scope">
          <span v-if="scope.row.score != null" :class="['score-badge', getScoreClass(scope.row.score)]">
            {{ Number(scope.row.score).toFixed(1) }}
          </span>
          <span v-else class="score-na">--</span>
        </template>
      </el-table-column>
      <el-table-column label="强项" min-width="120">
        <template #default="scope">
          <el-tag v-for="s in (scope.row.strong_dims || []).slice(0, 3)" :key="s" size="small" type="success" effect="plain" style="margin: 2px;">{{ s }}</el-tag>
          <span v-if="!(scope.row.strong_dims || []).length" class="cell-muted">—</span>
        </template>
      </el-table-column>
      <el-table-column label="弱项" min-width="120">
        <template #default="scope">
          <el-tag v-for="w in (scope.row.weak_dims || []).slice(0, 3)" :key="w" size="small" type="danger" effect="plain" style="margin: 2px;">{{ w }}</el-tag>
          <span v-if="!(scope.row.weak_dims || []).length" class="cell-muted">—</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120" align="center">
        <template #default="scope">
          <el-button type="primary" size="small" @click="viewDetail(scope.row)">查看报告</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div v-if="historyList.length === 0 && !loading" class="empty-history">
      <el-empty description="暂无面试记录，快去开始你的第一次 AI 模拟面试吧！" />
    </div>

    <InterviewReportDialog
      v-model="detailVisible"
      :interview="currentInterview"
      @download="(fmt) => downloadReport(fmt)"
    />
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { notifyError, notifyInfo, notifySuccess, notifyWarning } from '@/utils/appNotify'
import InterviewReportDialog from '@/components/InterviewReportDialog.vue'
import { getInterviewHistory, getInterviewDetail, downloadReport as downloadReportApi, getInterviewJobs } from '@/api/endpoints'

const loading = ref(false)
const historyList = ref([])
const detailVisible = ref(false)
const currentInterview = ref(null)

const resolveActiveJobId = async () => {
  const cached = Number(localStorage.getItem('active_job_id') || 0)
  if (cached > 0) return cached
  const jobsRes = await getInterviewJobs()
  const jobs = jobsRes?.jobs || []
  const first = Array.isArray(jobs) ? jobs[0] : null
  const firstId = Number(first?.job_id || 0)
  if (firstId > 0) {
    localStorage.setItem('active_job_id', String(firstId))
    return firstId
  }
  return 0
}

const loadHistory = async () => {
  loading.value = true
  try {
    const jobId = await resolveActiveJobId()
    if (!jobId) {
      notifyInfo('请先开始一场面试以绑定岗位后再查看历史', '面试历史')
      historyList.value = []
      return
    }
    const data = await getInterviewHistory(jobId)
    historyList.value = data.history_list || []
  } catch (err) {
    console.error('获取面试历史失败:', err)
    notifyError('获取面试历史失败', '面试历史')
    historyList.value = []
  } finally {
    loading.value = false
  }
}

const viewDetail = async (row) => {
  try {
    const jobId = Number(row.job_id || 0)
    if (!jobId) {
      notifyWarning('该记录缺少 job_id，无法查看报告', '面试详情')
      return
    }
    const data = await getInterviewDetail(row.id, jobId)
    if (data.interview) {
      currentInterview.value = data.interview
      detailVisible.value = true
    } else {
      notifyError('获取面试详情失败', '面试详情')
    }
  } catch (err) {
    console.error('获取面试详情失败:', err)
    notifyError('获取面试详情失败，请重试', '面试详情')
  }
}

const downloadReport = async (format = 'docx') => {
  try {
    if (!currentInterview.value?.id) {
      notifyWarning('未找到面试记录，无法下载报告', '下载报告')
      return
    }
    const interviewId = currentInterview.value.id
    const jobId = Number(currentInterview.value.job_id || 0)
    if (!jobId) {
      notifyWarning('当前报告缺少 job_id，无法下载', '下载报告')
      return
    }
    notifyInfo(format === 'pdf' ? '正在生成 PDF…' : '正在生成 Word…', '下载报告')
    const blob = await downloadReportApi(interviewId, format, jobId)
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    const ext = format === 'pdf' ? 'pdf' : 'docx'
    link.download = `面试报告_${interviewId}.${ext}`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    notifySuccess('面试报告已下载', '下载报告')
  } catch (err) {
    console.error('下载失败:', err)
    notifyError('下载失败，请重试', '下载报告')
  }
}

// ==================== 工具函数 ====================
const getDifficultyTag = (level) => {
  if (level === '专业级' || level === 'expert') return 'danger'
  if (level === '进阶级' || level === 'intermediate') return 'warning'
  return 'success'
}

const getModeLabel = (mode) => {
  const map = { text: '文字', speech: '语音', video: '视频' }
  return map[mode] || mode || '--'
}

const getScoreClass = (score) => {
  const s = Number(score)
  if (s >= 8.5) return 'score-excellent'
  if (s >= 7)   return 'score-good'
  if (s >= 5)   return 'score-average'
  return 'score-low'
}

onMounted(loadHistory)
</script>

<style scoped>
.history-page-card {
  width: 100%;
  max-width: none;
  margin: 0 auto;
  min-height: calc(100vh - 110px);
  border-radius: 16px !important;
  border: 1px solid var(--color-border, #e2e8f0) !important;
  box-shadow: 0 12px 36px rgba(15, 23, 42, 0.08) !important;
  overflow: hidden;
}
.history-card-head {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.history-card-title {
  font-size: 17px;
  font-weight: 700;
  color: #0f172a;
}
.history-card-sub {
  font-size: 12px;
  color: #94a3b8;
  font-weight: 500;
}
.history-table {
  width: 100%;
  border-radius: 0 0 12px 12px;
}
.cell-muted {
  color: #c0c4cc;
  font-size: 13px;
}
.section-card {
  width: 100%;
  max-width: none;
  margin: 0 auto;
}

/* 分数徽章 */
.score-badge {
  font-size: 16px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 6px;
}
.score-excellent { color: #67c23a; background: #f0f9eb; }
.score-good      { color: #409eff; background: #ecf5ff; }
.score-average   { color: #e6a23c; background: #fdf6ec; }
.score-low       { color: #f56c6c; background: #fef0f0; }
.score-na        { color: #c0c4cc; font-size: 16px; }

.empty-history {
  padding: 40px 0;
}
</style>
