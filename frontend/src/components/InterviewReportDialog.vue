<template>
  <el-dialog
    :model-value="modelValue"
    title="面试报告详情"
    width="min(1320px, 96vw)"
    class="interview-report-dialog"
    :close-on-click-modal="false"
    destroy-on-close
    align-center
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <div v-if="interview" class="interview-detail">
      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="应聘岗位">{{ interview.job }}</el-descriptions-item>
        <el-descriptions-item label="面试难度">
          <el-tag :type="getDifficultyTag(interview.level)" size="small">{{ interview.level }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="面试时间">{{ interview.time }}</el-descriptions-item>
        <el-descriptions-item label="面试状态">
          <el-tag type="success" size="small">{{ interview.status }}</el-tag>
        </el-descriptions-item>
      </el-descriptions>

      <div v-if="interview.report" class="report-wrapper">
        <div class="report-hero">
          <div class="report-hero-score" :class="scoreBandClass(interview.report.overall_score)">
            <div class="report-hero-label">综合得分</div>
            <div class="report-hero-num">{{ Number(interview.report.overall_score).toFixed(1) }}</div>
            <div class="report-hero-unit">满分 10</div>
            <div class="report-hero-badge">{{ getScoreLabel(Number(interview.report.overall_score)) }}</div>
          </div>
          <div class="report-hero-tech" v-if="technicalMastery != null">
            <div class="report-hero-tech-label">技术掌握度</div>
            <div class="report-hero-tech-val">{{ technicalMastery.toFixed(1) }}<span>/10</span></div>
            <el-progress
              :percentage="Math.min(100, technicalMastery * 10)"
              :color="getProgressColor(technicalMastery * 10)"
              :stroke-width="10"
              :show-text="false"
              style="margin-top: 10px;"
            />
            <p class="report-hero-tech-desc">基于「技术正确性 + 知识深度」综合，反映岗位核心知识的准确性与理解深度。</p>
          </div>
        </div>

        <div class="score-overview">
          <div class="total-score-card">
            <el-progress
              type="circle"
              :percentage="Math.round(Number(interview.report.overall_score) * 10)"
              :color="getProgressColor(Math.round(Number(interview.report.overall_score) * 10))"
              :stroke-width="10"
              :width="110"
            >
              <template #default>
                <div class="circle-inner">
                  <div class="total-score-value">{{ Number(interview.report.overall_score).toFixed(1) }}</div>
                  <div class="total-score-sub">/ 10</div>
                </div>
              </template>
            </el-progress>
            <div class="total-score-label">维度雷达</div>
            <el-tag
              :type="getScoreTagType(Number(interview.report.overall_score))"
              size="small"
              style="margin-top: 8px;"
            >
              {{ getScoreLabel(Number(interview.report.overall_score)) }}
            </el-tag>
          </div>

          <div class="radar-wrapper" v-if="radarDimensions.length >= 3" title="各维度得分（0–10）雷达示意">
            <svg :viewBox="`0 0 ${radarSize} ${radarSize}`" class="radar-svg">
              <g v-for="level in 5" :key="'grid'+level">
                <polygon
                  :points="getRadarPolygonPoints(level * 0.2)"
                  fill="none"
                  :stroke="level === 5 ? '#dde4ff' : '#eef0f8'"
                  stroke-width="1"
                />
              </g>
              <g v-for="(_, i) in radarDimensions" :key="'axis'+i">
                <line
                  :x1="radarCx"
                  :y1="radarCy"
                  :x2="getRadarPoint(i, 1).x"
                  :y2="getRadarPoint(i, 1).y"
                  stroke="#dde4ff"
                  stroke-width="1"
                />
              </g>
              <polygon
                :points="radarDataPolygon"
                fill="rgba(64,158,255,0.18)"
                stroke="#409eff"
                stroke-width="2"
                stroke-linejoin="round"
              />
              <g v-for="(dim, i) in radarDimensions" :key="'pt'+i">
                <circle
                  :cx="getRadarPoint(i, dim.ratio).x"
                  :cy="getRadarPoint(i, dim.ratio).y"
                  r="4"
                  :fill="getProgressColor(dim.ratio * 100)"
                  stroke="#fff"
                  stroke-width="1.5"
                />
              </g>
              <g v-for="(dim, i) in radarDimensions" :key="'lbl'+i">
                <text
                  :x="getRadarLabelPos(i).x"
                  :y="getRadarLabelPos(i).y"
                  text-anchor="middle"
                  dominant-baseline="middle"
                  font-size="10"
                  :fill="getProgressColor(dim.ratio * 100)"
                  font-weight="600"
                >{{ dim.shortName }}</text>
                <text
                  :x="getRadarLabelPos(i).x"
                  :y="getRadarLabelPos(i).y + 12"
                  text-anchor="middle"
                  dominant-baseline="middle"
                  font-size="9"
                  fill="#909399"
                >{{ dim.score.toFixed(1) }}</text>
              </g>
            </svg>
          </div>

          <div class="score-detail-list" v-if="reportScores.length">
            <div v-for="(item, idx) in reportScores" :key="idx" class="score-detail-row">
              <span class="score-detail-name">{{ item.name }}</span>
              <el-progress
                :percentage="item.value"
                :color="getProgressColor(item.value)"
                :stroke-width="6"
                :show-text="false"
                style="flex:1; min-width: 60px;"
              />
              <span class="score-detail-val" :style="{ color: getProgressColor(item.value) }">
                {{ (item.value / 10).toFixed(1) }}
              </span>
            </div>
          </div>
          <div v-else class="no-score-hint">维度数据不足 3 项时仅显示下方条形图（结束面试后将生成完整多维评分）</div>
        </div>

        <div v-if="hasImprovementResources" class="improvement-resources-section">
          <div class="section-header">提升资源精选</div>
          <div class="improvement-resources-grid">
            <div
              v-if="improvementKnowledgePoints.length"
              class="ir-column card-elevated"
            >
              <div class="ir-column-title">技术知识点</div>
              <ul class="ir-list">
                <li v-for="(it, i) in improvementKnowledgePoints" :key="'kp'+i">
                  <strong>{{ it.topic }}</strong>
                  <p class="ir-line">{{ it.summary }}</p>
                  <p v-if="it.action" class="ir-action">行动：{{ it.action }}</p>
                </li>
              </ul>
            </div>
            <div
              v-if="improvementQuestions.length"
              class="ir-column card-elevated"
            >
              <div class="ir-column-title">常见面试题</div>
              <ul class="ir-list">
                <li v-for="(it, i) in improvementQuestions" :key="'iq'+i">
                  <p class="ir-q">{{ it.question }}</p>
                  <p v-if="it.focus" class="ir-focus">考察：{{ it.focus }}</p>
                </li>
              </ul>
            </div>
            <div
              v-if="improvementCommReadings.length"
              class="ir-column card-elevated"
            >
              <div class="ir-column-title">沟通与表达</div>
              <ul class="ir-list">
                <li v-for="(it, i) in improvementCommReadings" :key="'cr'+i">
                  <template v-if="isHttpUrl(it.url_or_search)">
                    <el-link :href="it.url_or_search" target="_blank" type="primary">{{ it.title || '延伸阅读' }}</el-link>
                  </template>
                  <strong v-else>{{ it.title }}</strong>
                  <p class="ir-line">{{ it.summary }}</p>
                  <p v-if="it.url_or_search && !isHttpUrl(it.url_or_search)" class="ir-action">{{ it.url_or_search }}</p>
                </li>
              </ul>
            </div>
          </div>
        </div>

        <div v-if="dimensionFeedbackEntries.length" class="dimension-feedback-section">
          <div class="section-header">分维度点评与依据</div>
          <div class="dimension-feedback-grid">
            <div
              v-for="([dim, fb], idx) in dimensionFeedbackEntries"
              :key="idx"
              class="dimension-feedback-card card-elevated"
            >
              <div class="df-title">{{ dim }}</div>
              <p class="df-comment">{{ fb.comment || '—' }}</p>
              <div v-if="fb.evidence" class="df-evidence">
                <span class="df-evidence-label">对话依据</span>
                {{ fb.evidence }}
              </div>
            </div>
          </div>
        </div>

        <div v-if="interview.report?.report_markdown" class="report-markdown-section">
          <div class="section-header">评估摘要（Markdown）</div>
          <div class="report-markdown-body card-elevated">
            <MarkdownRich :content="interview.report.report_markdown" />
          </div>
        </div>

        <div class="feedback-section">
          <div class="feedback-block highlight-block card-elevated">
            <div class="feedback-header"><span class="feedback-icon">✨</span> 亮点表现</div>
            <ul v-if="Array.isArray(interview.report.highlights) && interview.report.highlights.length" class="feedback-list">
              <li v-for="(item, i) in interview.report.highlights" :key="i">{{ item }}</li>
            </ul>
            <p v-else class="feedback-text">{{ interview.report.highlights || '暂无' }}</p>
          </div>

          <div class="feedback-block weakness-block card-elevated">
            <div class="feedback-header"><span class="feedback-icon">⚠️</span> 不足之处</div>
            <ul v-if="Array.isArray(interview.report.weaknesses) && interview.report.weaknesses.length" class="feedback-list">
              <li v-for="(item, i) in interview.report.weaknesses" :key="i">{{ item }}</li>
            </ul>
            <p v-else class="feedback-text">{{ interview.report.weaknesses || '暂无' }}</p>
          </div>

          <div class="feedback-block suggestion-block card-elevated">
            <div class="feedback-header"><span class="feedback-icon">💡</span> 改进建议</div>
            <ul v-if="Array.isArray(interview.report.suggestions) && interview.report.suggestions.length" class="feedback-list">
              <li v-for="(item, i) in interview.report.suggestions" :key="i">{{ item }}</li>
            </ul>
            <p v-else class="feedback-text">{{ interview.report.suggestions || '暂无' }}</p>
          </div>
        </div>

        <div class="qa-analysis-section" v-if="questionAnalysisList.length">
          <div class="section-header">逐题分析</div>
          <el-collapse accordion class="qa-analysis-collapse">
            <el-collapse-item
              v-for="(row, index) in questionAnalysisList"
              :key="index"
              :title="`第 ${index + 1} 题 · 得分 ${Number(row.score ?? 0).toFixed(1)}`"
              :name="index"
            >
              <div class="qa-analysis-body">
                <p><strong>题目</strong> {{ row.question }}</p>
                <p><strong>作答</strong> {{ row.answer }}</p>
                <p><strong>正确性</strong> {{ row.correctness || '—' }} · <strong>完整性</strong> {{ row.completeness || '—' }}</p>
                <p v-if="row.feedback"><strong>反馈</strong> {{ row.feedback }}</p>
                <p v-if="(row.missing_points || []).length"><strong>遗漏点</strong> {{ (row.missing_points || []).join('；') }}</p>
                <p v-if="(row.errors || []).length"><strong>错误点</strong> {{ (row.errors || []).join('；') }}</p>
              </div>
            </el-collapse-item>
          </el-collapse>
        </div>

        <div class="qa-section" v-if="qaRecords.length">
          <div class="section-header">📋 问答记录</div>
          <el-collapse accordion>
            <el-collapse-item
              v-for="(qa, index) in qaRecords"
              :key="index"
              :title="`Q${index + 1}：${truncate(qa.question, 60)}`"
              :name="index"
            >
              <div class="qa-content">
                <div class="qa-q"><el-tag size="small" type="primary">问题</el-tag> {{ qa.question }}</div>
                <div class="qa-a"><el-tag size="small" type="success">回答</el-tag> {{ qa.answer || '（未作答）' }}</div>
              </div>
            </el-collapse-item>
          </el-collapse>
        </div>
      </div>

      <div v-else class="no-report-card">
        <el-empty description="该面试尚未生成评估报告" :image-size="80">
          <template #description>
            <p>面试尚未结束或报告生成中，请完成面试后查看。</p>
          </template>
        </el-empty>
      </div>
    </div>

    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">关闭</el-button>
      <el-dropdown v-if="showDownload" trigger="click" @command="onDownloadCommand">
        <el-button type="primary" :disabled="!interview?.report">
          📥 下载报告 ▼
        </el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="docx">Word 文档 (.docx)</el-dropdown-item>
            <el-dropdown-item command="pdf">PDF (.pdf)</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed } from 'vue'
import MarkdownRich from '@/components/MarkdownRich.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  interview: { type: Object, default: null },
  showDownload: { type: Boolean, default: true },
})

const emit = defineEmits(['update:modelValue', 'download'])

const reportScores = computed(() => {
  const report = props.interview?.report
  if (!report?.dimension_scores?.length) return []
  const seen = new Map()
  for (const item of report.dimension_scores) {
    const name = item.name
    if (!name || seen.has(name)) continue
    const v = Number(item.value)
    if (Number.isNaN(v)) continue
    seen.set(name, Math.min(100, Math.round(v * 10)))
  }
  return [...seen.entries()].map(([name, value]) => ({ name, value }))
})

const RADAR_SHORT_NAME = {
  技术知识: '技术',
  技术正确性: '正确性',
  知识深度: '深度',
  专业知识: '专业',
  逻辑思维: '逻辑',
  沟通表达: '沟通',
  应变能力: '应变',
  表达能力: '表达',
  综合表达: '表综',
  岗位匹配: '岗位',
  岗位匹配度: '岗位',
  语速流畅: '语速',
  表达清晰度: '清晰',
  自信度: '自信',
  简历匹配: '简历',
}

const radarSize = 320
const radarCx = radarSize / 2
const radarCy = radarSize / 2
const radarMaxR = 90
const radarLabelOffset = 18

const radarExcludeNames = new Set(['综合得分'])

const radarDimensions = computed(() => {
  const scores = reportScores.value.filter((s) => !radarExcludeNames.has(s.name))
  if (scores.length < 3) return []
  return scores.map((s) => ({
    name: s.name,
    shortName: RADAR_SHORT_NAME[s.name] || (s.name.length > 2 ? s.name.slice(0, 2) : s.name),
    score: s.value / 10,
    ratio: s.value / 100,
  }))
})

const getRadarPoint = (idx, ratio) => {
  const n = radarDimensions.value.length
  const angle = (2 * Math.PI * idx) / n - Math.PI / 2
  const r = ratio * radarMaxR
  return {
    x: radarCx + r * Math.cos(angle),
    y: radarCy + r * Math.sin(angle),
  }
}

const getRadarPolygonPoints = (ratio) => {
  const n = radarDimensions.value.length
  if (!n) return ''
  return Array.from({ length: n }, (_, i) => {
    const pt = getRadarPoint(i, ratio)
    return `${pt.x.toFixed(1)},${pt.y.toFixed(1)}`
  }).join(' ')
}

const radarDataPolygon = computed(() => {
  return radarDimensions.value
    .map((d, i) => {
      const pt = getRadarPoint(i, d.ratio)
      return `${pt.x.toFixed(1)},${pt.y.toFixed(1)}`
    })
    .join(' ')
})

const getRadarLabelPos = (idx) => {
  const n = radarDimensions.value.length
  const angle = (2 * Math.PI * idx) / n - Math.PI / 2
  const r = radarMaxR + radarLabelOffset
  return {
    x: radarCx + r * Math.cos(angle),
    y: radarCy + r * Math.sin(angle),
  }
}

const getScoreTagType = (score) => {
  if (score >= 8.5) return 'success'
  if (score >= 7) return 'primary'
  if (score >= 5) return 'warning'
  return 'danger'
}

const getScoreLabel = (score) => {
  if (score >= 9) return '优秀'
  if (score >= 8) return '良好'
  if (score >= 7) return '中等'
  if (score >= 5) return '待提升'
  return '需加强'
}

const qaRecords = computed(() => props.interview?.report?.qa_records || [])

const questionAnalysisList = computed(() => {
  const raw = props.interview?.report?.question_analysis
  if (!Array.isArray(raw)) return []
  return raw.filter((x) => x && typeof x === 'object')
})

const dimensionFeedbackEntries = computed(() => {
  const fb = props.interview?.report?.dimension_feedback
  if (!fb || typeof fb !== 'object') return []
  return Object.entries(fb).filter(([, v]) => v && typeof v === 'object')
})

const technicalMastery = computed(() => {
  const r = props.interview?.report
  if (r?.technical_mastery != null) return Number(r.technical_mastery)
  const ds = r?.dimension_scores || []
  const a = ds.find((x) => x.name === '技术正确性')
  const b = ds.find((x) => x.name === '知识深度')
  if (a != null && b != null) return (Number(a.value) + Number(b.value)) / 2
  const t = ds.find((x) => x.name === '技术知识' || x.name === '专业知识')
  return t != null ? Number(t.value) : null
})

const improvementRes = computed(() => props.interview?.report?.improvement_resources || null)

const improvementKnowledgePoints = computed(() => {
  const raw = improvementRes.value?.knowledge_points
  if (!Array.isArray(raw)) return []
  return raw.filter((x) => x && (x.topic || x.summary))
})

const improvementQuestions = computed(() => {
  const raw = improvementRes.value?.sample_interview_questions
  if (!Array.isArray(raw)) return []
  return raw.filter((x) => x && x.question)
})

const improvementCommReadings = computed(() => {
  const raw = improvementRes.value?.communication_readings
  if (!Array.isArray(raw)) return []
  return raw.filter((x) => x && (x.title || x.summary || x.url_or_search))
})

const hasImprovementResources = computed(() => {
  return (
    improvementKnowledgePoints.value.length > 0
    || improvementQuestions.value.length > 0
    || improvementCommReadings.value.length > 0
  )
})

const isHttpUrl = (s) => /^https?:\/\//i.test(String(s || '').trim())

const scoreBandClass = (raw) => {
  const s = Number(raw)
  if (s >= 8.5) return 'band-excellent'
  if (s >= 7) return 'band-good'
  if (s >= 5) return 'band-mid'
  return 'band-low'
}

const getDifficultyTag = (level) => {
  if (level === '专业级' || level === 'expert') return 'danger'
  if (level === '进阶级' || level === 'intermediate') return 'warning'
  return 'success'
}

const getProgressColor = (pct) => {
  if (pct >= 85) return '#67c23a'
  if (pct >= 70) return '#409eff'
  if (pct >= 50) return '#e6a23c'
  return '#f56c6c'
}

const truncate = (str, len) => {
  if (!str) return ''
  return str.length > len ? str.substring(0, len) + '...' : str
}

const onDownloadCommand = (cmd) => {
  if (cmd === 'pdf' || cmd === 'docx') emit('download', cmd)
}
</script>

<style scoped>
.interview-detail {
  padding: 4px 0;
}

.report-wrapper {
  margin-top: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.report-hero {
  display: grid;
  grid-template-columns: 1fr 1.1fr;
  gap: 16px;
  align-items: stretch;
}
@media (max-width: 720px) {
  .report-hero {
    grid-template-columns: 1fr;
  }
}
.report-hero-score {
  border-radius: 18px;
  padding: 22px 20px;
  text-align: center;
  color: #fff;
  box-shadow: 0 14px 36px rgba(30, 58, 95, 0.18);
}
.report-hero-score.band-excellent {
  background: linear-gradient(145deg, #059669 0%, #10b981 45%, #34d399 100%);
}
.report-hero-score.band-good {
  background: linear-gradient(145deg, #1d4ed8 0%, #2563eb 50%, #38bdf8 100%);
}
.report-hero-score.band-mid {
  background: linear-gradient(145deg, #c2410c 0%, #ea580c 55%, #fb923c 100%);
}
.report-hero-score.band-low {
  background: linear-gradient(145deg, #b91c1c 0%, #ef4444 50%, #f87171 100%);
}
.report-hero-label {
  font-size: 12px;
  opacity: 0.92;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.report-hero-num {
  font-size: 56px;
  font-weight: 800;
  line-height: 1.05;
  margin: 6px 0 4px;
  text-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}
.report-hero-unit {
  font-size: 13px;
  opacity: 0.88;
}
.report-hero-badge {
  display: inline-block;
  margin-top: 12px;
  padding: 4px 14px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.22);
  font-size: 13px;
  font-weight: 600;
}
.report-hero-tech {
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  border-radius: 18px;
  padding: 20px 22px;
  border: 1px solid #e2e8f0;
  box-shadow: var(--shadow-md, 0 4px 16px rgba(15, 23, 42, 0.08));
}
.report-hero-tech-label {
  font-size: 12px;
  color: #64748b;
  font-weight: 600;
  letter-spacing: 0.04em;
}
.report-hero-tech-val {
  font-size: 32px;
  font-weight: 800;
  color: #0f172a;
  margin-top: 6px;
}
.report-hero-tech-val span {
  font-size: 14px;
  color: #94a3b8;
  font-weight: 600;
  margin-left: 4px;
}
.report-hero-tech-desc {
  margin: 10px 0 0;
  font-size: 12px;
  color: #64748b;
  line-height: 1.5;
}
.card-elevated {
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
  border-radius: 14px !important;
}

.score-overview {
  display: flex;
  gap: 20px;
  align-items: center;
  background: linear-gradient(135deg, #fafbff 0%, #f0f4ff 100%);
  border-radius: 14px;
  padding: 20px 24px;
  border: 1px solid #e0e6f6;
  flex-wrap: wrap;
}

.total-score-card {
  text-align: center;
  min-width: 120px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.circle-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.total-score-value {
  font-size: 24px;
  font-weight: 800;
  background: linear-gradient(135deg, #409eff, #667eea);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  line-height: 1.1;
}

.total-score-sub {
  font-size: 10px;
  color: #c0c4cc;
}

.total-score-label {
  font-size: 12px;
  color: #909399;
  font-weight: 600;
}

.radar-wrapper {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.radar-svg {
  width: 280px;
  height: 280px;
  overflow: visible;
}

.score-detail-list {
  flex: 1;
  min-width: 160px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.score-detail-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.score-detail-name {
  font-size: 12px;
  color: #606266;
  width: 76px;
  flex-shrink: 0;
  white-space: nowrap;
}

.improvement-resources-section {
  margin-top: 4px;
}
.improvement-resources-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 14px;
}
.ir-column {
  padding: 14px 16px;
  border-radius: 10px;
  border: 1px solid #e4e7ed;
  background: linear-gradient(180deg, #ffffff 0%, #fafbff 100%);
}
.ir-column-title {
  font-size: 14px;
  font-weight: 700;
  color: #409eff;
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px dashed #e4e7ed;
}
.ir-list {
  margin: 0;
  padding-left: 18px;
  list-style-type: disc;
}
.ir-list li {
  margin-bottom: 12px;
  font-size: 13px;
  color: #555;
  line-height: 1.55;
}
.ir-list li:last-child {
  margin-bottom: 0;
}
.ir-line {
  margin: 4px 0 0;
  font-size: 12px;
  color: #606266;
}
.ir-action {
  margin: 4px 0 0;
  font-size: 12px;
  color: #909399;
}
.ir-q {
  margin: 0;
  font-weight: 600;
  color: #303133;
}
.ir-focus {
  margin: 4px 0 0;
  font-size: 12px;
  color: #64748b;
}

.score-detail-val {
  font-size: 12px;
  font-weight: 700;
  width: 24px;
  text-align: right;
  flex-shrink: 0;
}

.no-score-hint {
  color: #c0c4cc;
  font-size: 13px;
  padding: 20px 0;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.dimension-feedback-section {
  margin-top: 4px;
}
.dimension-feedback-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 12px;
}
.dimension-feedback-card {
  padding: 14px 16px;
  border-radius: 10px;
}
.df-title {
  font-weight: 700;
  color: #409eff;
  margin-bottom: 8px;
  font-size: 14px;
}
.df-comment {
  font-size: 13px;
  color: #333;
  line-height: 1.55;
  margin: 0 0 8px;
}
.df-evidence {
  font-size: 12px;
  color: #606266;
  background: #f5f7fa;
  padding: 8px 10px;
  border-radius: 6px;
  line-height: 1.5;
}
.df-evidence-label {
  display: block;
  font-size: 11px;
  color: #909399;
  margin-bottom: 4px;
}

.qa-analysis-section {
  margin-top: 8px;
}
.qa-analysis-body {
  font-size: 13px;
  line-height: 1.6;
  color: #333;
}
.qa-analysis-body p {
  margin: 6px 0;
}

.feedback-section {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}
@media (max-width: 900px) {
  .feedback-section {
    grid-template-columns: 1fr;
  }
}

.feedback-block {
  border-radius: 10px;
  padding: 14px 16px;
  border: 1px solid;
}

.highlight-block {
  background: #f6ffed;
  border-color: #b7eb8f;
}
.weakness-block {
  background: #fffbe6;
  border-color: #ffe58f;
}
.suggestion-block {
  background: #e6f7ff;
  border-color: #91d5ff;
}

.feedback-header {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 10px;
  color: #303133;
  display: flex;
  align-items: center;
  gap: 4px;
}

.feedback-icon {
  font-size: 16px;
}

.feedback-list {
  margin: 0;
  padding-left: 18px;
  list-style-type: disc;
}

.feedback-list li {
  font-size: 13px;
  color: #555;
  line-height: 1.6;
  margin-bottom: 4px;
}

.feedback-text {
  font-size: 13px;
  color: #555;
  line-height: 1.6;
  margin: 0;
}

.section-header {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 10px;
  padding-left: 8px;
  border-left: 3px solid #409eff;
}

.report-markdown-section {
  margin-top: 4px;
}
.report-markdown-body {
  padding: 18px 20px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  overflow: visible;
  max-height: none;
}

@media (prefers-color-scheme: dark) {
  .report-markdown-body {
    background: rgba(30, 41, 59, 0.75);
    border-color: #334155;
    box-shadow: 0 8px 28px rgba(0, 0, 0, 0.25);
  }
}

.qa-content {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 4px 0;
}

.qa-q,
.qa-a {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 13px;
  color: #555;
  line-height: 1.6;
  word-wrap: break-word;
  overflow-wrap: break-word;
}

.no-report-card {
  margin-top: 20px;
  padding: 30px;
  background: #fafafa;
  border-radius: 10px;
  text-align: center;
}

/* 确保悬停时布局稳定 */
.interview-report-dialog .el-button:hover,
.interview-report-dialog .el-tag:hover,
.interview-report-dialog .el-collapse-item__title:hover {
  transform: none !important;
  box-shadow: none !important;
}

/* 确保表格内容显示完整 */
.interview-report-dialog .el-table {
  width: 100% !important;
}

.interview-report-dialog .el-table th,
.interview-report-dialog .el-table td {
  white-space: normal !important;
  word-break: break-all !important;
}
</style>

<style>
.interview-report-dialog.el-dialog {
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 24px 64px rgba(30, 58, 95, 0.18);
  max-height: 92vh;
  display: flex;
  flex-direction: column;
}
.interview-report-dialog .el-dialog__body {
  overflow-y: auto;
}
.interview-report-dialog .el-dialog__header {
  padding: 18px 22px;
  margin: 0;
  background: linear-gradient(135deg, #1e3a5f 0%, #2563eb 100%);
}
.interview-report-dialog .el-dialog__title {
  color: #fff;
  font-weight: 700;
  font-size: 17px;
}
.interview-report-dialog .el-dialog__headerbtn .el-dialog__close {
  color: rgba(255, 255, 255, 0.9);
}
</style>
