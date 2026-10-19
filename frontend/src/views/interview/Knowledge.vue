<template>
  <div class="knowledge-page">
    <el-tabs v-model="activeTab" class="knowledge-tabs" @tab-change="handleTabChange">
      <!-- ===== Tab 1: 统一知识库 ===== -->
      <el-tab-pane label="统一知识库" name="general">
        <div class="tab-content">
          <!-- 统计卡片 -->
          <div class="stats-row">
            <el-card class="stat-card">
              <div class="stat-inner">
                <div class="stat-icon">📚</div>
                <div class="stat-info">
                  <div class="stat-value">{{ docList.length }}</div>
                  <div class="stat-label">已上传文档</div>
                </div>
              </div>
            </el-card>
            <el-card class="stat-card">
              <div class="stat-inner">
                <div class="stat-icon">🧩</div>
                <div class="stat-info">
                  <div class="stat-value">{{ totalChildChunks }}</div>
                  <div class="stat-label">子块向量（Chroma）</div>
                </div>
              </div>
            </el-card>
            <el-card class="stat-card">
              <div class="stat-inner">
                <div class="stat-icon">{{ ragStats.status === 'ok' ? '✅' : '⚠️' }}</div>
                <div class="stat-info">
                  <div class="stat-value" :class="ragStats.status === 'ok' ? 'text-success' : 'text-warning'">
                    {{ ragStats.status === 'ok' ? '正常' : ragStats.status === 'unavailable' ? '未启用' : '--' }}
                  </div>
                  <div class="stat-label">向量库状态</div>
                </div>
              </div>
            </el-card>
          </div>

          <!-- 上传区域 -->
          <el-card class="section-card upload-card-container">
            <template #header>
              <span class="card-title">📤 上传文档</span>
            </template>
            <div class="upload-form">
              <div class="form-row">
                <el-select v-model="uploadCategory" placeholder="选择类别" style="width: 160px;">
                  <el-option label="通用知识" value="general" />
                  <el-option label="技术文档" value="tech" />
                  <el-option label="行业资料" value="industry" />
                  <el-option label="其他" value="other" />
                </el-select>
                <el-input
                  v-model="uploadDescription"
                  placeholder="文档描述（可选）"
                  style="flex: 1;"
                  clearable
                />
              </div>
              <div class="upload-guide">
                <el-tag type="info" size="small">解析后结构化入库 + 父子分块向量化</el-tag>
                <el-tag type="info" size="small" style="margin-left: 8px;">TXT / MD / PDF / DOCX / CSV / XLSX / XLS</el-tag>
                <el-tag type="warning" size="small" style="margin-left: 8px;">最大 20MB</el-tag>
              </div>
              <el-progress v-if="uploading && uploadProgress > 0" :percentage="uploadProgress" style="margin-top: 12px;" />
              <el-upload
                ref="uploadRef"
                :auto-upload="false"
                :limit="1"
                :on-change="handleFileChange"
                :on-exceed="() => notifyWarning('每次只能上传一个文件', '数量限制')"
                accept=".txt,.md,.pdf,.docx,.doc,.csv,.xlsx,.xls"
                class="upload-area"
                drag
              >
                <el-icon class="el-icon--upload" style="font-size: 48px; color: #c0c4cc;"><upload-filled /></el-icon>
                <div class="el-upload__text">拖拽文件到此处，或 <em>点击选择文件</em></div>
              </el-upload>
              <div v-if="selectedFile" class="selected-file-info">
                <el-tag type="success" size="large">✅ 已选择：{{ selectedFile.name }}</el-tag>
                <el-button
                  type="primary"
                  size="large"
                  :loading="uploading"
                  @click="handleUploadDoc"
                  style="margin-left: 16px;"
                >
                  {{ uploading ? '上传中...' : '⬆️ 开始上传' }}
                </el-button>
                <el-button size="large" @click="clearSelectedFile" plain>取消</el-button>
              </div>
            </div>
          </el-card>

          <!-- 搜索区域 -->
          <el-card class="section-card">
            <template #header>
              <span class="card-title">🔍 语义搜索</span>
            </template>
            <div class="search-form">
              <div class="search-job-row">
                <span class="search-job-label">当前岗位</span>
                <JobPositionSelect v-model="searchJobName" class="search-job-select" />
              </div>
              <el-input
                v-model="searchQuery"
                placeholder="输入关键词或问题，进行语义搜索..."
                size="large"
                clearable
                @keyup.enter="handleSearch"
              >
                <template #append>
                  <el-button type="primary" :loading="searching" @click="handleSearch">搜索</el-button>
                </template>
              </el-input>
              <div v-if="searchResults.length > 0" class="search-results">
                <div class="search-result-header">
                  <span>找到 {{ searchResults.length }} 条相关内容</span>
                  <el-button link @click="searchResults = []">清除结果</el-button>
                </div>
                <div
                  v-for="(item, idx) in searchResults"
                  :key="idx"
                  class="search-result-item"
                >
                  <div class="result-meta">
                    <el-tag size="small" :type="item.result_kind === '题库' ? 'danger' : 'success'">{{ item.source_type || item.result_kind || '知识库' }}</el-tag>
                    <el-tag v-if="item.source_filename" size="small" type="info" style="margin-left: 6px;">{{ item.source_filename }}</el-tag>
                    <el-tag size="small" type="warning" style="margin-left: 6px;">{{ item.parent_title || '—' }}</el-tag>
                    <el-tag v-if="item.distance != null" size="small" type="success" style="margin-left: 6px;">
                      距离 {{ Number(item.distance).toFixed(4) }}
                    </el-tag>
                  </div>
                  <div class="result-text result-child">{{ item.child_content }}</div>
                  <div v-if="item.related_questions?.length" class="result-related">
                    <div v-for="(rq, j) in item.related_questions" :key="j" class="related-q">
                      <div><strong>关联题</strong> {{ rq.content }}</div>
                      <div v-if="rq.answer"><strong>参考答</strong> {{ rq.answer }}</div>
                      <div v-if="rq.exam_points" class="ep"><strong>考点</strong> {{ rq.exam_points }}</div>
                    </div>
                  </div>
                </div>
              </div>
              <el-empty v-else-if="hasSearched && searchResults.length === 0" description="未找到相关内容" />
            </div>
          </el-card>

          <!-- 文档列表 -->
          <el-card class="section-card">
            <template #header>
              <div class="card-header-row">
                <span class="card-title">📋 文档列表</span>
                <div class="header-actions">
                  <el-select
                    v-model="filterCategory"
                    placeholder="全部类别"
                    clearable
                    size="small"
                    style="width: 130px;"
                    @change="fetchDocList"
                  >
                    <el-option label="全部类别" value="" />
                    <el-option label="通用知识" value="general" />
                    <el-option label="技术文档" value="tech" />
                    <el-option label="行业资料" value="industry" />
                    <el-option label="其他" value="other" />
                  </el-select>
                  <el-button size="small" :loading="loadingDocs" @click="fetchDocList" plain>
                    🔄 刷新
                  </el-button>
                </div>
              </div>
            </template>
            <el-table
              :data="filteredDocs"
              v-loading="loadingDocs"
              border
              class="doc-table"
              :header-cell-style="{ background: '#f5f7fa', color: '#606266' }"
              empty-text="暂无文档，请上传"
            >
              <el-table-column prop="filename" label="文件名" min-width="200" show-overflow-tooltip />
              <el-table-column prop="file_type" label="类型" width="80">
                <template #default="{ row }">
                  <el-tag size="small" type="info">{{ row.file_type?.toUpperCase() }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="category" label="类别" width="100">
                <template #default="{ row }">
                  <el-tag size="small">{{ categoryLabel(row.category) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="description" label="描述" min-width="140" show-overflow-tooltip>
                <template #default="{ row }">
                  <span class="desc-text">{{ row.description || '—' }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="child_chunk_count" label="子块数" width="85" align="center" />
              <el-table-column prop="char_count" label="字符数" width="90" align="center">
                <template #default="{ row }">{{ formatNumber(row.char_count) }}</template>
              </el-table-column>
              <el-table-column prop="created_at" label="上传时间" width="160" show-overflow-tooltip>
                <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
              </el-table-column>
              <el-table-column label="解析状态" width="120" align="center">
                <template #default="{ row }">
                  <el-tag :type="parseStatusType(row.parse_status)" size="small">
                    {{ parseStatusLabel(row.parse_status) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="来源" width="118" align="center">
                <template #default="{ row }">
                  <el-tag v-if="row.is_enterprise_shared" type="success" size="small">企业共享</el-tag>
                  <el-tag v-else type="info" size="small">我的上传</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" min-width="260" align="center">
                <template #default="{ row }">
                  <el-button type="primary" link size="small" @click="openFileDetail(row)">详情</el-button>
                  <template v-if="!isEnterpriseUser && row.is_enterprise_shared">
                    <span class="kb-op-label">参与检索</span>
                    <el-switch
                      :model-value="row.retrieval_enabled !== false"
                      @change="(v) => toggleEnterpriseKf(row, v)"
                    />
                  </template>
                  <template v-if="row.is_own || isEnterpriseUser">
                    <el-popconfirm
                      width="280"
                      popper-class="kb-inline-confirm-popover"
                      title="删除后无法恢复，数据库记录与向量一并清除。"
                      confirm-button-text="确定删除"
                      cancel-button-text="取消"
                      @confirm="handleDeleteDoc(row.id)"
                    >
                      <template #reference>
                        <el-button type="danger" link size="small">删除</el-button>
                      </template>
                    </el-popconfirm>
                  </template>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </div>
      </el-tab-pane>

      <!-- ===== Tab 3: 岗位查询（统一库内检索） ===== -->
      <el-tab-pane label="岗位查询" name="position">
        <div class="tab-content">
          <el-card class="section-card">
            <template #header>
              <span class="card-title">🔎 岗位查询</span>
            </template>
            <div class="search-form">
              <JobPositionSelect v-model="positionSearchJob" />
              <el-input
                v-model="positionSearchQuery"
                placeholder="输入问题后在统一知识库中检索（会自动带上岗位上下文）"
                clearable
                @keyup.enter="handlePositionSearch"
              >
                <template #append>
                  <el-button type="primary" :loading="positionSearching" @click="handlePositionSearch">查询</el-button>
                </template>
              </el-input>
              <div v-if="positionSearchResults.length > 0" class="search-results">
                <div class="search-result-header">
                  <span>找到 {{ positionSearchResults.length }} 条相关内容</span>
                  <el-button link @click="positionSearchResults = []">清除结果</el-button>
                </div>
                <div
                  v-for="(item, idx) in positionSearchResults"
                  :key="idx"
                  class="search-result-item"
                >
                  <div class="result-meta">
                    <el-tag size="small" :type="item.result_kind === '题库' ? 'danger' : 'success'">{{ item.source_type || item.result_kind || '知识库' }}</el-tag>
                    <el-tag v-if="item.source_filename" size="small" type="info" style="margin-left: 6px;">{{ item.source_filename }}</el-tag>
                    <el-tag size="small" type="warning" style="margin-left: 6px;">{{ item.parent_title || '—' }}</el-tag>
                  </div>
                  <div class="result-text result-child">{{ item.child_content }}</div>
                </div>
              </div>
              <el-empty
                v-else-if="positionHasSearched && positionSearchResults.length === 0"
                description="未找到相关内容"
              />
            </div>
          </el-card>
        </div>
      </el-tab-pane>

      <!-- ===== Tab 2: 智能题库 ===== -->
      <el-tab-pane label="智能题库" name="questions">
        <div class="tab-content">
          <el-card class="section-card">
            <div class="job-input-section">
              <h3 class="section-title">🎯 选择岗位</h3>
              <div class="job-input-wrapper">
                <JobPositionSelect v-model="jobInput" width="100%" />
                <el-button
                  type="primary"
                  size="large"
                  :loading="querying"
                  :disabled="!jobInput.trim()"
                  @click="queryJobQuestions"
                >
                  🔍 智能生成题目
                </el-button>
              </div>
            </div>

            <div class="result-section" v-if="hasQueried">
              <!-- 有题目 -->
              <div v-if="questions.length > 0" class="questions-display">
                <div class="result-header">
                  <h4>📚 {{ jobInput }} - 智能题目列表</h4>
                  <div class="result-header-actions">
                    <el-tag type="success" size="large">✅ 共 {{ questions.length }} 道题目</el-tag>
                    <el-button
                      type="success"
                      plain
                      size="default"
                      :loading="qExporting"
                      @click="handleExportQuestions"
                    >
                      📥 导出 CSV
                    </el-button>
                  </div>
                </div>

                <!-- 筛选栏 -->
                <div class="filter-section">
                  <span class="filter-label">🎯 难度筛选：</span>
                  <el-select
                    v-model="selectedDifficulty"
                    placeholder="全部难度"
                    clearable
                    size="default"
                    style="width: 150px;"
                    @change="onQuestionFilterChange"
                  >
                    <el-option label="全部难度" value="" />
                    <el-option label="简单" value="easy" />
                    <el-option label="中等" value="medium" />
                    <el-option label="困难" value="hard" />
                  </el-select>
                  <span class="filter-label" style="margin-left: 12px;">分类：</span>
                  <el-input
                    v-model="selectedCategory"
                    placeholder="精确匹配，如 technical"
                    clearable
                    size="default"
                    style="width: 180px;"
                    @keyup.enter="onQuestionFilterChange"
                  />
                  <el-button size="default" style="margin-left: 8px;" @click="onQuestionFilterChange">应用筛选</el-button>
                  <div class="filter-stats">
                    <span class="stat-value-small">{{ questions.length }}</span>
                    <span class="stat-label-small"> 题</span>
                  </div>
                </div>

                <el-table
                  :data="paginatedQuestions"
                  border
                  class="question-table"
                  :header-cell-style="{ background: '#f5f7fa', color: '#606266' }"
                >
                  <el-table-column prop="question" label="📝 问题" min-width="280" show-overflow-tooltip />
                  <el-table-column prop="answer" label="💡 答案" min-width="180" show-overflow-tooltip />
                  <el-table-column prop="difficulty" label="难度" width="90">
                    <template #default="{ row }">
                      <el-tag
                        :type="row.difficulty === 'easy' ? 'success' : row.difficulty === 'medium' ? 'warning' : 'danger'"
                        size="small"
                      >
                        {{ row.difficulty === 'easy' ? '简单' : row.difficulty === 'medium' ? '中等' : '困难' }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="job" label="岗位" width="120">
                    <template #default="{ row }">
                      <el-tag type="info" size="small">{{ row.job }}</el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="exam_points" label="考点" min-width="140" show-overflow-tooltip />
                </el-table>

                <div class="pagination-container">
                  <el-pagination
                    v-model:current-page="currentPage"
                    v-model:page-size="pageSize"
                    :page-sizes="[10, 20, 50, 100]"
                    :total="questions.length"
                    layout="total, sizes, prev, pager, next, jumper"
                    @size-change="currentPage = 1"
                  />
                </div>

              </div>

              <!-- 无题目 -->
              <div v-else>
                <div class="empty-tip-container">
                  <el-empty :description="`暂无「${jobInput}」可用题目，请先上传统一知识库文档`">
                    <el-button type="primary" size="large" @click="goToKnowledgeUpload">
                      📚 前往统一知识库上传
                    </el-button>
                  </el-empty>
                </div>
              </div>
            </div>
          </el-card>
        </div>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="detailVisible" title="文件详情（结构化抽取）" width="760px" destroy-on-close>
      <div v-loading="detailLoading">
        <template v-if="fileDetail">
          <p class="detail-line"><strong>文件</strong> {{ fileDetail.file?.filename }} · <strong>状态</strong> {{ fileDetail.file?.parse_status }}</p>
          <h4 class="detail-h">岗位与技术栈</h4>
          <ul class="detail-ul">
            <li v-for="j in fileDetail.jobs" :key="j.id">
              <strong>{{ j.job_name }}</strong>
              <span v-if="(j.tech_stack || []).length"> — {{ (j.tech_stack || []).join('、') }}</span>
            </li>
            <li v-if="!fileDetail.jobs?.length" class="muted">暂无抽取岗位，请等待解析完成或检查文档内容</li>
          </ul>
          <h4 class="detail-h">面试题与考点（最多展示 80 条）</h4>
          <el-table :data="(fileDetail.questions || []).slice(0, 80)" size="small" max-height="360" border>
            <el-table-column prop="content" label="题干" min-width="200" show-overflow-tooltip />
            <el-table-column prop="answer" label="参考答案" min-width="160" show-overflow-tooltip />
            <el-table-column prop="difficulty" label="难度" width="72" />
            <el-table-column prop="exam_points" label="考点" min-width="120" show-overflow-tooltip />
            <el-table-column prop="category" label="分类" width="90" />
          </el-table>
        </template>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { UploadFilled } from '@element-plus/icons-vue'
import JobPositionSelect from '@/components/JobPositionSelect.vue'
import {
  uploadKnowledge,
  getKnowledgeFiles,
  getKnowledgeFile,
  getKnowledgeDetail,
  deleteKnowledgeFile,
  searchKnowledge,
  setEnterpriseKnowledgeFileRetrieval,
  getKnowledgeStats,
  getQuestions,
  downloadQuestionsCsv,
} from '@/api/endpoints'
import { notifySuccess, notifyError, notifyWarning, notifyInfo } from '@/utils/appNotify'

const route = useRoute()
const activeTab = ref('general')
const isEnterpriseUser = (localStorage.getItem('account_type') || 'personal') === 'enterprise'

const docList = ref([])
const loadingDocs = ref(false)
const filterCategory = ref('')
const ragStats = ref({ total_chunks: null, status: '' })

const uploadRef = ref(null)
const selectedFile = ref(null)
const uploadCategory = ref('general')
const uploadDescription = ref('')
const uploading = ref(false)
const uploadProgress = ref(0)

const searchQuery = ref('')
const searchJobName = ref('')
const searching = ref(false)
const searchResults = ref([])
const hasSearched = ref(false)

const detailVisible = ref(false)
const detailLoading = ref(false)
const fileDetail = ref(null)

const positionSearchJob = ref('')
const positionSearchQuery = ref('')
const positionSearching = ref(false)
const positionSearchResults = ref([])
const positionHasSearched = ref(false)

const jobInput = ref('')
const hasQueried = ref(false)
const querying = ref(false)
const questions = ref([])
const selectedDifficulty = ref('')
const selectedCategory = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const qExporting = ref(false)

const totalChildChunks = computed(() =>
  docList.value.reduce((s, r) => s + (r.child_chunk_count || 0), 0)
)

const filteredDocs = computed(() => {
  if (!filterCategory.value) return docList.value
  return docList.value.filter((d) => d.category === filterCategory.value)
})

const paginatedQuestions = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return questions.value.slice(start, start + pageSize.value)
})

const categoryLabel = (val) => {
  const map = { general: '通用知识', tech: '技术文档', industry: '行业资料', other: '其他', question_bank: '题库' }
  return map[val] || val || '—'
}

const parseStatusLabel = (st) => {
  const m = {
    pending: '排队',
    parsing: '解析中',
    structuring: '结构化',
    chunking: '分块',
    vectorizing: '向量化',
    done: '完成',
    error: '失败',
  }
  return m[st] || st || '—'
}

const parseStatusType = (st) => {
  if (st === 'done') return 'success'
  if (st === 'error') return 'danger'
  return 'warning'
}

const formatNumber = (n) => {
  if (n == null) return '—'
  return n >= 10000 ? (n / 10000).toFixed(1) + 'w' : n
}

const formatDate = (str) => {
  if (!str) return '—'
  try {
    return str.replace('T', ' ').substring(0, 16)
  } catch {
    return str
  }
}

const pollUntilDone = async (fileId) => {
  for (let i = 0; i < 90; i++) {
    await new Promise((r) => setTimeout(r, 2000))
    try {
      const data = await getKnowledgeFile(fileId)
      const st = data?.data?.parse_status
      if (st === 'done' || st === 'error') {
        await fetchDocList()
        if (st === 'error') notifyError(data?.data?.parse_message || '解析失败')
        else notifySuccess('解析与向量化已完成', '知识库')
        return
      }
    } catch {
      break
    }
  }
  notifyInfo('解析耗时较长，请稍后手动刷新列表', '知识库')
}

const fetchDocList = async () => {
  loadingDocs.value = true
  try {
    const data = await getKnowledgeFiles()
    docList.value = data?.data?.files || []
  } catch {
    notifyError('获取文档列表失败')
  } finally {
    loadingDocs.value = false
  }
}

const fetchStats = async () => {
  try {
    const data = await getKnowledgeStats()
    const inner = data?.data || {}
    ragStats.value = {
      total_chunks: inner.child_chunks,
      status: inner.embedding_ok ? 'ok' : 'unavailable',
    }
  } catch {
    ragStats.value = { total_chunks: 0, status: 'error' }
  }
}

const handleFileChange = (file) => {
  selectedFile.value = file.raw
}

const clearSelectedFile = () => {
  selectedFile.value = null
  uploadProgress.value = 0
  if (uploadRef.value) uploadRef.value.clearFiles()
}

const handleUploadDoc = async () => {
  if (!selectedFile.value) {
    notifyWarning('请先选择文件', '上传')
    return
  }
  uploading.value = true
  uploadProgress.value = 0
  try {
    const data = await uploadKnowledge(
      selectedFile.value,
      uploadCategory.value,
      uploadDescription.value,
      (p) => { uploadProgress.value = p }
    )
    const fid = data?.data?.file_id
    notifySuccess('已上传，后台解析中（父子分块 + 向量化）', '知识库')
    clearSelectedFile()
    uploadDescription.value = ''
    await fetchDocList()
    await fetchStats()
    if (fid) pollUntilDone(fid)
  } catch (err) {
    notifyError(err?.response?.data?.detail || err?.message || '上传失败')
  } finally {
    uploading.value = false
    uploadProgress.value = 0
  }
}

const toggleEnterpriseKf = async (row, enabled) => {
  try {
    await setEnterpriseKnowledgeFileRetrieval(row.id, enabled)
    notifySuccess(enabled ? '已参与该企业文件的检索' : '已排除该文件', '检索偏好')
    await fetchDocList()
  } catch (err) {
    notifyError(err?.response?.data?.detail || '更新失败')
    await fetchDocList()
  }
}

const handleDeleteDoc = async (docId) => {
  try {
    await deleteKnowledgeFile(docId)
    notifySuccess('已删除', '知识库')
    await fetchDocList()
    await fetchStats()
  } catch (err) {
    notifyError(err?.response?.data?.detail || '删除失败')
  }
}

const openFileDetail = async (row) => {
  detailVisible.value = true
  detailLoading.value = true
  fileDetail.value = null
  try {
    const data = await getKnowledgeDetail(row.id)
    fileDetail.value = data?.data || null
  } catch {
    notifyError('加载详情失败')
    detailVisible.value = false
  } finally {
    detailLoading.value = false
  }
}

const handleSearch = async () => {
  if (!(searchJobName.value || '').trim()) {
    notifyWarning('请先选择当前岗位，再检索知识库与题库', '岗位必选')
    return
  }
  if (!searchQuery.value.trim()) {
    notifyWarning('请输入搜索内容', '语义搜索')
    return
  }
  searching.value = true
  hasSearched.value = true
  searchResults.value = []
  try {
    const data = await searchKnowledge(searchQuery.value.trim(), 12, null, searchJobName.value.trim())
    searchResults.value = data?.data?.results || []
    if (searchResults.value.length === 0) {
      notifyInfo('未命中子块向量，可尝试换关键词或确认已完成向量化。', '检索')
    }
  } catch {
    notifyError('搜索失败，请确认 RAG 已初始化且存在子块向量')
  } finally {
    searching.value = false
  }
}

const handlePositionSearch = async () => {
  if (!(positionSearchJob.value || '').trim()) {
    notifyWarning('请先选择岗位', '岗位查询')
    return
  }
  if (!(positionSearchQuery.value || '').trim()) {
    notifyWarning('请输入查询内容', '岗位查询')
    return
  }
  positionSearching.value = true
  positionHasSearched.value = true
  positionSearchResults.value = []
  try {
    const data = await searchKnowledge(
      positionSearchQuery.value.trim(),
      12,
      null,
      positionSearchJob.value.trim(),
    )
    positionSearchResults.value = data?.data?.results || []
    if (!positionSearchResults.value.length) {
      notifyInfo('未命中相关内容，可更换关键词重试', '岗位查询')
    }
  } catch {
    notifyError('岗位查询失败，请稍后重试')
  } finally {
    positionSearching.value = false
  }
}

const queryJobQuestions = async () => {
  if (!jobInput.value.trim()) {
    notifyWarning('请从岗位库中选择岗位后再出题', '题库')
    return
  }
  querying.value = true
  hasQueried.value = true
  currentPage.value = 1
  try {
    const opts = {}
    if (selectedDifficulty.value) opts.difficulty = selectedDifficulty.value
    if (selectedCategory.value) opts.category = selectedCategory.value
    const data = await getQuestions(jobInput.value, opts)
    questions.value = data?.questions || []
    if (questions.value.length > 0) {
      notifySuccess(`共 ${questions.value.length} 道题目（${data?.source || '题库'}）`, '题库')
    } else {
      notifyInfo(`暂无「${jobInput.value}」结构化题目，可先在统一知识库上传相关文档`, '题库')
      goToKnowledgeUpload()
    }
  } catch {
    questions.value = []
    notifyWarning('获取题库失败', '题库')
  } finally {
    querying.value = false
  }
}

const onQuestionFilterChange = () => {
  currentPage.value = 1
  if (hasQueried.value && jobInput.value.trim()) {
    queryJobQuestions()
  }
}

const goToKnowledgeUpload = () => {
  activeTab.value = 'general'
  uploadCategory.value = 'general'
}

const handleExportQuestions = async () => {
  if (!jobInput.value.trim()) {
    notifyWarning('请先输入并查询岗位', '导出')
    return
  }
  qExporting.value = true
  try {
    await downloadQuestionsCsv(jobInput.value.trim())
    notifySuccess('浏览器已开始下载 CSV 文件。', '导出题库')
  } catch (e) {
    notifyError(e?.message || '导出失败')
  } finally {
    qExporting.value = false
  }
}

const handleTabChange = (name) => {
  if (name === 'general') {
    fetchDocList()
    fetchStats()
  }
}

const syncActiveTabFromRoute = () => {
  const t = route.query.tab
  if (t === 'questions') activeTab.value = 'questions'
  else if (t === 'position') activeTab.value = 'position'
  else if (t === 'general') activeTab.value = 'general'
}

watch(
  () => route.query.tab,
  () => {
    syncActiveTabFromRoute()
  },
)

onMounted(() => {
  syncActiveTabFromRoute()
  fetchDocList()
  fetchStats()
})
</script>

<style scoped>
.knowledge-page {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}

.knowledge-tabs :deep(.el-tabs__header) {
  margin-bottom: 0;
}

.knowledge-tabs :deep(.el-tabs__nav-wrap::after) {
  display: none;
}

.knowledge-tabs :deep(.el-tabs__item) {
  font-size: 16px;
  font-weight: 500;
  padding: 0 28px;
  height: 48px;
  line-height: 48px;
}

.knowledge-tabs :deep(.el-tabs__active-bar) {
  background-color: #42b983;
}

.knowledge-tabs :deep(.el-tabs__item.is-active) {
  color: #42b983;
}

.tab-content {
  padding-top: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 统计卡片 */
.stats-row {
  display: flex;
  gap: 16px;
}

.stat-card {
  flex: 1;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.stat-inner {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 8px 0;
}

.stat-icon {
  font-size: 36px;
  line-height: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #2c3e50;
  line-height: 1;
}

.stat-value.text-success { color: #42b983; }
.stat-value.text-warning { color: #e6a23c; }

.stat-label {
  font-size: 13px;
  color: #909399;
  margin-top: 4px;
}

/* 区块卡片 */
.section-card {
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #2c3e50;
}

.card-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* 上传区域 */
.upload-card-container :deep(.el-card__body) {
  padding: 20px;
}

.upload-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.form-row {
  display: flex;
  gap: 12px;
  align-items: center;
}

.upload-guide {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.upload-area {
  width: 100%;
}

.upload-area :deep(.el-upload-dragger) {
  width: 100%;
  height: 100px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: 2px dashed #dcdfe6;
  border-radius: 8px;
  transition: border-color 0.3s;
}

.upload-area :deep(.el-upload-dragger:hover) {
  border-color: #42b983;
}

.selected-file-info {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  padding: 12px 16px;
  background: #f0f9f4;
  border-radius: 8px;
  border: 1px solid #b2dfdb;
}

/* 搜索结果 */
.search-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.search-result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
  color: #606266;
  margin-bottom: 10px;
}

.search-results {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.search-result-item {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 14px 16px;
  border-left: 3px solid #42b983;
}

.result-meta {
  margin-bottom: 8px;
}

.result-text {
  font-size: 14px;
  color: #303133;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-all;
}

/* 文档表格 */
.doc-table {
  border-radius: 8px;
  overflow: hidden;
}

.kb-op-label {
  margin-right: 8px;
  font-size: 12px;
  color: #606266;
  vertical-align: middle;
}

.desc-text {
  color: #909399;
  font-size: 13px;
}

/* ── 岗位查询 ── */
.pos-collapse-title {
  display: flex;
  align-items: center;
  font-size: 15px;
}

.pos-name {
  font-weight: 600;
  color: #2c3e50;
}

.position-list :deep(.el-collapse-item__header) {
  font-size: 15px;
  padding: 0 16px;
  background: linear-gradient(135deg, #f8f9fa, #eef5ff);
  border-radius: 8px;
  margin-bottom: 4px;
}

.pos-doc-table {
  border-radius: 6px;
  overflow: hidden;
}

.parsed-section {
  background: #fafbff;
  border-radius: 10px;
  padding: 14px 16px;
  border: 1px solid #e8eeff;
  min-height: 160px;
}

.parsed-section-title {
  font-size: 13px;
  font-weight: 700;
  color: #409eff;
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid #e0e8ff;
}

.parsed-list {
  margin: 0;
  padding-left: 16px;
  list-style: disc;
}

.parsed-list li {
  font-size: 12px;
  color: #303133;
  line-height: 1.7;
  margin: 4px 0;
}

.empty-item {
  color: #c0c4cc !important;
  font-style: italic;
  list-style: none;
}

.search-job-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}
.search-job-label {
  font-size: 13px;
  font-weight: 600;
  color: #475569;
  padding-top: 10px;
  min-width: 72px;
}
.search-job-select {
  flex: 1;
  min-width: 220px;
  max-width: 520px;
}

/* 题库管理 */
.job-input-section {
  padding: 24px 24px 20px;
  background: linear-gradient(135deg, #f0f9f4 0%, #e8f5e9 100%);
  border-radius: 8px;
  margin-bottom: 20px;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: #2c3e50;
  margin: 0 0 16px 0;
}

.job-input-wrapper {
  display: flex;
  gap: 15px;
  align-items: flex-start;
}

.job-input-wrapper > :first-child {
  flex: 1;
  min-width: 200px;
  max-width: 640px;
}

.result-section {
  padding: 0 4px;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 2px solid #42b983;
}

.result-header h4 {
  font-size: 16px;
  font-weight: 600;
  color: #2c3e50;
  margin: 0;
}

.result-header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.filter-section {
  margin: 16px 0;
  padding: 12px 16px;
  background: #f8f9fa;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.filter-label {
  font-size: 14px;
  font-weight: 600;
  color: #606266;
}

.filter-stats {
  margin-left: auto;
  font-size: 14px;
}

.stat-value-small {
  font-size: 18px;
  font-weight: 700;
  color: #42b983;
}

.stat-label-small {
  color: #909399;
}

.question-table {
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.06);
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.continue-upload-btn {
  margin-top: 20px;
  text-align: center;
}

.upload-section {
  margin-top: 20px;
}

.upload-card {
  background: linear-gradient(135deg, #f0f9f4 0%, #e8f5e9 100%);
  border: 2px solid #42b983;
  border-radius: 12px;
}

.upload-title {
  font-size: 16px;
  font-weight: 600;
  color: #2c3e50;
  margin: 0 0 16px 0;
}

.upload-guide-q {
  background: #fff;
  border-left: 4px solid #42b983;
  padding: 14px 18px;
  border-radius: 8px;
  margin-bottom: 16px;
}

.upload-guide-q h4 {
  font-size: 14px;
  color: #2c3e50;
  margin: 0 0 10px 0;
}

.upload-guide-q ul {
  margin: 0;
  padding-left: 18px;
}

.upload-guide-q li {
  font-size: 13px;
  color: #606266;
  margin: 6px 0;
  line-height: 1.6;
}

.upload-actions {
  background: #fff;
  padding: 16px;
  border-radius: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}

.file-info {
  margin-top: 4px;
}

.empty-tip-container {
  text-align: center;
  padding: 50px 20px;
}

/* 响应式 */
@media (max-width: 768px) {
  .knowledge-page {
    padding: 10px;
  }

  .stats-row {
    flex-direction: column;
  }

  .job-input-wrapper {
    flex-direction: column;
    align-items: stretch;
  }

  .job-input-wrapper .el-input {
    max-width: 100%;
  }

  .result-header {
    flex-direction: column;
    gap: 10px;
    align-items: flex-start;
  }

  .form-row {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
