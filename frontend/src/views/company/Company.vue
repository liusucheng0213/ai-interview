<template>
  <div class="company-page">
    <el-card class="panel-card">
      <template #header>
        <div class="panel-header">
          <span>企业用户管理台</span>
          <el-tag type="success">Enterprise</el-tag>
        </div>
      </template>

      <div class="toolbar">
        <el-input
          v-model="keyword"
          placeholder="搜索用户名/邮箱"
          clearable
          style="width: 260px"
          @keyup.enter="loadUsers"
        />
        <el-button type="primary" @click="loadUsers">查询用户</el-button>
      </div>

      <el-table :data="users" v-loading="loadingUsers" stripe border>
        <el-table-column prop="id" label="用户ID" width="90" />
        <el-table-column prop="username" label="用户名" min-width="130" />
        <el-table-column prop="account_type" label="账号类型" width="120">
          <template #default="{ row }">
            <el-tag :type="row.account_type === 'enterprise' ? 'success' : 'info'">
              {{ row.account_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" min-width="170" />
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button size="small" type="warning" link @click="openPasswordDialog(row)">改密</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card class="panel-card">
      <template #header>
        <div class="panel-header">
          <span>候选人面试记录</span>
          <el-tag type="info">测评报告</el-tag>
        </div>
      </template>
      <p class="interview-hint">
        在此查看企业下候选人的模拟面试记录与完整报告（与求职者端报告一致）。若列表为空，请确认候选人已使用求职者账号完成面试。
      </p>
      <div class="toolbar">
        <el-select
          v-model="filterUserId"
          placeholder="筛选用户（全部）"
          clearable
          filterable
          style="width: 280px"
          @change="loadInterviews"
        >
          <el-option
            v-for="u in personalUsers"
            :key="u.id"
            :label="`${u.username} (ID ${u.id})`"
            :value="u.id"
          />
        </el-select>
        <el-button type="primary" @click="loadInterviews" :loading="loadingInterviews">刷新列表</el-button>
      </div>

      <el-table :data="interviews" v-loading="loadingInterviews" stripe border max-height="480">
        <el-table-column prop="id" label="面试ID" width="88" />
        <el-table-column prop="username" label="候选人" min-width="110" />
        <el-table-column prop="job" label="岗位" min-width="120" />
        <el-table-column prop="mode" label="形式" width="80" />
        <el-table-column prop="status" label="状态" width="100" />
        <el-table-column label="得分" width="88" align="center">
          <template #default="{ row }">
            <span v-if="row.score != null">{{ Number(row.score).toFixed(1) }}</span>
            <span v-else class="muted">--</span>
          </template>
        </el-table-column>
        <el-table-column prop="time" label="时间" min-width="160" />
        <el-table-column label="操作" width="200" align="center">
          <template #default="{ row }">
            <el-button type="primary" size="small" link @click="openInterviewDetail(row)">查看报告</el-button>
            <el-dropdown trigger="click" @command="(fmt) => downloadCompanyReport(row, fmt)">
              <el-button size="small" type="success" link>
                下载 ▼
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="docx">Word</el-dropdown-item>
                  <el-dropdown-item command="pdf">PDF</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="!interviews.length && !loadingInterviews" class="empty-interviews">
        <el-empty description="暂无面试记录" />
      </div>
    </el-card>

    <el-dialog
      v-model="pwdDialogVisible"
      width="440px"
      class="pwd-float-dialog"
      align-center
      destroy-on-close
      :show-close="true"
      :close-on-click-modal="false"
      @closed="resetPwdForm"
    >
      <template #header>
        <div class="pwd-dialog-head">
          <span class="pwd-dialog-icon">🔐</span>
          <div>
            <div class="pwd-dialog-title">重置用户密码</div>
            <div class="pwd-dialog-sub">为用户 {{ pwdTargetName }} 设置新登录密码</div>
          </div>
        </div>
      </template>
      <el-form ref="pwdFormRef" :model="pwdForm" :rules="pwdRules" label-position="top" class="pwd-form">
        <el-form-item label="新密码" prop="password">
          <el-input
            v-model="pwdForm.password"
            type="password"
            show-password
            placeholder="不少于 6 位"
            maxlength="64"
            clearable
          />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirm">
          <el-input
            v-model="pwdForm.confirm"
            type="password"
            show-password
            placeholder="再次输入新密码"
            maxlength="64"
            clearable
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pwdDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="pwdSubmitting" @click="submitPassword">确认重置</el-button>
      </template>
    </el-dialog>

    <InterviewReportDialog
      v-model="detailVisible"
      :interview="currentInterview"
      @download="(fmt) => downloadCompanyReportFromDialog(fmt)"
    />
  </div>
</template>

<script setup>
import { onMounted, ref, computed } from 'vue'
import {
  getCompanyUsers,
  resetCompanyUserPassword,
  getCompanyInterviews,
  getCompanyInterviewDetail,
  downloadReport,
} from '@/api/endpoints'
import { notifySuccess, notifyError, notifyInfo } from '@/utils/appNotify'
import InterviewReportDialog from '@/components/InterviewReportDialog.vue'

const keyword = ref('')
const users = ref([])
const loadingUsers = ref(false)

const interviews = ref([])
const loadingInterviews = ref(false)
const filterUserId = ref(null)
const detailVisible = ref(false)
const currentInterview = ref(null)
const reportRow = ref(null)

const personalUsers = computed(() => users.value.filter((u) => u.account_type !== 'enterprise'))

const pwdDialogVisible = ref(false)
const pwdTargetId = ref(null)
const pwdTargetName = ref('')
const pwdFormRef = ref(null)
const pwdSubmitting = ref(false)
const pwdForm = ref({ password: '', confirm: '' })

const validateConfirm = (_rule, val, callback) => {
  if (!val) {
    callback(new Error('请再次输入密码'))
    return
  }
  if (val !== pwdForm.value.password) {
    callback(new Error('两次输入不一致'))
    return
  }
  callback()
}

const pwdRules = {
  password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '至少 6 位', trigger: 'blur' },
  ],
  confirm: [{ required: true, validator: validateConfirm, trigger: 'blur' }],
}

const loadUsers = async () => {
  loadingUsers.value = true
  try {
    const data = await getCompanyUsers(keyword.value.trim())
    users.value = data?.users || []
  } catch (e) {
    notifyError(e?.response?.data?.detail || '获取用户列表失败')
  } finally {
    loadingUsers.value = false
  }
}

const loadInterviews = async () => {
  loadingInterviews.value = true
  try {
    const data = await getCompanyInterviews(filterUserId.value || undefined)
    interviews.value = data?.interviews || []
  } catch (e) {
    notifyError(e?.response?.data?.detail || '获取面试列表失败')
    interviews.value = []
  } finally {
    loadingInterviews.value = false
  }
}

const openInterviewDetail = async (row) => {
  reportRow.value = row
  try {
    const data = await getCompanyInterviewDetail(row.id)
    if (data?.interview) {
      currentInterview.value = data.interview
      detailVisible.value = true
    } else {
      notifyError('获取面试详情失败', '企业管理台')
    }
  } catch (e) {
    notifyError(e?.response?.data?.detail || '获取详情失败')
  }
}

const downloadCompanyReport = async (row, format = 'docx') => {
  try {
    notifyInfo(format === 'pdf' ? '正在生成 PDF…' : '正在生成 Word…', '下载报告')
    const blob = await downloadReport(row.id, format)
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    const ext = format === 'pdf' ? 'pdf' : 'docx'
    link.download = `面试报告_${row.job || '岗位'}_${row.id}.${ext}`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    notifySuccess('已开始下载', '下载报告')
  } catch (e) {
    console.error(e)
    notifyError('下载失败', '下载报告')
  }
}

const downloadCompanyReportFromDialog = (format) => {
  if (reportRow.value) {
    downloadCompanyReport(reportRow.value, format)
  } else if (currentInterview.value?.id) {
    downloadCompanyReport({ id: currentInterview.value.id, job: currentInterview.value.job }, format)
  }
}

const openPasswordDialog = (row) => {
  pwdTargetId.value = row.id
  pwdTargetName.value = row.username || `ID ${row.id}`
  pwdForm.value = { password: '', confirm: '' }
  pwdDialogVisible.value = true
}

const resetPwdForm = () => {
  pwdTargetId.value = null
  pwdTargetName.value = ''
  pwdForm.value = { password: '', confirm: '' }
  pwdFormRef.value?.clearValidate?.()
}

const submitPassword = async () => {
  const form = pwdFormRef.value
  if (!form) return
  try {
    await form.validate()
  } catch {
    return
  }
  pwdSubmitting.value = true
  try {
    await resetCompanyUserPassword(pwdTargetId.value, pwdForm.value.password)
    notifySuccess('新密码已生效，用户可使用新密码登录。', '密码已重置')
    pwdDialogVisible.value = false
  } catch (e) {
    notifyError(e?.response?.data?.detail || '重置失败')
  } finally {
    pwdSubmitting.value = false
  }
}

onMounted(async () => {
  await loadUsers()
  await loadInterviews()
})
</script>

<style scoped>
.company-page {
  max-width: 1300px;
  margin: 0 auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.panel-card {
  border-radius: 10px;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.toolbar {
  margin-bottom: 12px;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
}

.interview-hint {
  font-size: 13px;
  color: #64748b;
  line-height: 1.55;
  margin: 0 0 12px;
}

.empty-interviews {
  padding: 24px 0;
}

.muted {
  color: #c0c4cc;
}
</style>

<style>
.pwd-float-dialog.el-dialog {
  border-radius: 16px;
  overflow: hidden;
  padding: 0;
  box-shadow: 0 24px 64px rgba(30, 58, 95, 0.2);
}
.pwd-float-dialog .el-dialog__header {
  padding: 0;
  margin: 0;
}
.pwd-float-dialog .el-dialog__body {
  padding: 20px 24px 8px;
}
.pwd-float-dialog .el-dialog__footer {
  padding: 12px 24px 20px;
  border-top: 1px solid var(--el-border-color-lighter);
}
.pwd-dialog-head {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 22px 24px 18px;
  background: linear-gradient(135deg, #1e3a5f 0%, #2563eb 55%, #3d6fb5 100%);
  color: #fff;
}
.pwd-dialog-icon {
  font-size: 28px;
  line-height: 1;
}
.pwd-dialog-title {
  font-size: 17px;
  font-weight: 700;
  letter-spacing: 0.02em;
}
.pwd-dialog-sub {
  margin-top: 6px;
  font-size: 13px;
  opacity: 0.92;
  font-weight: 400;
}
.pwd-form :deep(.el-form-item__label) {
  font-weight: 600;
  color: var(--el-text-color-primary);
}
</style>
