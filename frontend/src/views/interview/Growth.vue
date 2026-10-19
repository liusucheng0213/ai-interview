<template>
  <div class="growth-page">
  <el-card class="section-card">
    <template #header>
      <div class="card-header-row">
        <span class="card-title">📈 我的成长轨迹</span>
        <el-button size="small" :loading="loading" @click="loadGrowthData" plain>🔄 刷新</el-button>
      </div>
    </template>

    <div v-if="growthData.length > 0" class="dim-timeline-wrap">
      <div class="dim-timeline-title">历次强弱项（来自各场报告维度）</div>
      <div class="dim-chips-rows">
        <div v-for="(row, ri) in growthData" :key="'dr'+ri" class="dim-chip-row">
          <span class="dim-chip-date">{{ row.date }}</span>
          <span class="dim-chip-job">{{ row.job }}</span>
          <el-tag v-for="s in row.strong_dims" :key="'st'+s" size="small" type="success" effect="light">强 {{ s }}</el-tag>
          <el-tag v-for="w in row.weak_dims" :key="'wk'+w" size="small" type="danger" effect="light">弱 {{ w }}</el-tag>
        </div>
      </div>
    </div>

    <div v-if="growthData.length > 0" class="chart-wrapper">
      <svg class="curve-chart" :viewBox="`0 0 ${svgW} ${svgH}`" preserveAspectRatio="xMidYMid meet">
        <defs>
          <linearGradient id="growthGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#409eff" stop-opacity="0.4"/>
            <stop offset="100%" stop-color="#409eff" stop-opacity="0.02"/>
          </linearGradient>
        </defs>

        <!-- Y 轴参考线 & 标注 -->
        <g v-for="yLine in yLines" :key="'yl'+yLine.val">
          <line
            :x1="padL" :y1="getY(yLine.val)"
            :x2="svgW - padR" :y2="getY(yLine.val)"
            stroke="#f0f2f8" stroke-width="1" stroke-dasharray="4,4"
          />
          <text :x="padL - 6" :y="getY(yLine.val)" text-anchor="end" dominant-baseline="middle"
            font-size="10" fill="#bfc3cc">{{ yLine.label }}</text>
        </g>

        <!-- 面积填充 -->
        <path :d="areaPath" fill="url(#growthGrad)"/>

        <!-- 曲线 -->
        <path :d="curvePath" fill="none" stroke="#409eff" stroke-width="2.5"
          stroke-linecap="round" stroke-linejoin="round"/>

        <!-- 数据点 + tooltip触发区 -->
        <g v-for="(item, index) in growthData" :key="'dp'+index">
          <circle
            :cx="getX(index)"
            :cy="getY(item.score)"
            r="5"
            :fill="getPointFill(item.score)"
            stroke="#fff"
            stroke-width="2"
            class="data-point"
            :style="{ animationDelay: `${index * 0.08}s` }"
          />
          <!-- 悬停显示分数 -->
          <title>{{ item.date }}  {{ item.job }}  {{ (item.score / 10).toFixed(1) }}分</title>
          <!-- 分数标注（最后一个 or 最高分） -->
          <text
            v-if="index === growthData.length - 1 || item.score === maxScoreRaw"
            :x="getX(index)"
            :y="getY(item.score) - 10"
            text-anchor="middle"
            font-size="10"
            font-weight="700"
            :fill="getPointFill(item.score)"
          >{{ (item.score / 10).toFixed(1) }}</text>
        </g>

        <!-- X 轴日期标签 -->
        <g v-for="(item, index) in xLabels" :key="'xl'+index">
          <text
            :x="getX(item.idx)"
            :y="svgH - padB + 14"
            text-anchor="middle"
            font-size="9"
            fill="#bfc3cc"
          >{{ item.date }}</text>
        </g>
      </svg>
    </div>

    <div v-else class="empty-growth" v-loading="loading">
      <el-empty description="暂无面试数据" :image-size="80">
        <template #description>
          <p style="color:#999; font-size:14px;">完成面试后，这里会自动显示你的成长曲线</p>
        </template>
      </el-empty>
    </div>
    <div class="growth-stats">
      <el-row :gutter="15">
        <el-col :span="6">
          <div class="stat-card">
            <div class="stat-value">{{ growthData.length }}</div>
            <div class="stat-label">总面试次数</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card">
            <div class="stat-value">{{ averageScore }}</div>
            <div class="stat-label">平均分（/ 10）</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card">
            <div class="stat-value">{{ highestScore }}</div>
            <div class="stat-label">最高分（/ 10）</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card">
            <div class="stat-value">{{ growthRate }}%</div>
            <div class="stat-label">成长率</div>
          </div>
        </el-col>
      </el-row>
    </div>
  </el-card>

  <!-- ══ 能力提升反馈模块 ══════════════════════════════════════ -->
  <el-card class="section-card advice-card">
    <template #header>
      <div class="card-header-row">
        <span class="card-title">🚀 个性化能力提升建议</span>
        <div class="advice-controls">
          <el-select
            v-model="selectedPosition"
            clearable
            filterable
            placeholder="筛选岗位（仅面试历史）"
            style="width: 220px; margin-right: 10px;"
          >
            <el-option
              v-for="job in positionList"
              :key="job"
              :label="job"
              :value="job"
            />
          </el-select>
          <el-button
            type="primary"
            size="small"
            :loading="adviceLoading"
            @click="fetchGrowthAdvice"
          >
            {{ adviceLoading ? 'AI 分析中...' : '✨ 生成提升建议' }}
          </el-button>
        </div>
      </div>
    </template>

    <!-- 空状态 -->
    <div v-if="!adviceData && !adviceLoading && !adviceError" class="advice-placeholder">
      <div class="advice-placeholder-icon">🎯</div>
      <p>点击「生成提升建议」，AI 将根据你的历史面试数据</p>
      <p>生成个性化的能力提升方案、练习计划和技术学习路线</p>
    </div>

    <!-- 错误状态 -->
    <el-empty v-else-if="adviceError" :description="adviceError" :image-size="60" />

    <!-- 加载中 -->
    <div v-else-if="adviceLoading" class="advice-loading">
      <el-skeleton :rows="8" animated />
    </div>

    <!-- 建议内容 -->
    <div v-else-if="adviceData" class="advice-content">
      <!-- 整体建议 + 鼓励语 -->
      <div class="advice-banner">
        <div class="advice-banner-text">
          <div class="advice-overall">{{ adviceData.advice?.overall_advice }}</div>
          <div class="advice-motive">💬 {{ adviceData.advice?.motivational_message }}</div>
        </div>
        <div class="advice-meta">
          <el-tag type="info" size="small">基于 {{ adviceData.interview_count }} 次面试</el-tag>
          <el-tag type="success" size="small" style="margin-left: 6px;">{{ adviceData.trend_desc }}</el-tag>
        </div>
      </div>

      <el-row :gutter="20" style="margin-top: 20px;">
        <!-- 左：薄弱点 + 改进计划 -->
        <el-col :span="14">
          <!-- 薄弱点 -->
          <div class="advice-section" v-if="adviceData.advice?.weak_points?.length">
            <div class="advice-section-title">⚠️ 当前薄弱点</div>
            <div
              v-for="(wp, i) in adviceData.advice.weak_points"
              :key="i"
              class="weak-point-row"
            >
              <el-tag :type="getPriorityType(wp.priority)" size="small" style="min-width: 50px;">{{ wp.priority }}优先</el-tag>
              <span class="weak-dim">{{ wp.dimension }}</span>
              <span class="weak-issue">{{ wp.issue }}</span>
            </div>
          </div>

          <!-- 改进计划时间线 -->
          <div class="advice-section" v-if="adviceData.advice?.improvement_plan?.length">
            <div class="advice-section-title">📅 改进练习计划</div>
            <el-timeline>
              <el-timeline-item
                v-for="(plan, i) in adviceData.advice.improvement_plan"
                :key="i"
                :type="i === 0 ? 'primary' : i === 1 ? 'success' : 'info'"
                :hollow="i > 1"
                size="normal"
              >
                <div class="plan-header">
                  <span class="plan-week">{{ plan.week }}</span>
                  <span class="plan-focus">{{ plan.focus }}</span>
                </div>
                <ul class="plan-tasks">
                  <li v-for="(task, ti) in plan.tasks" :key="ti">{{ task }}</li>
                </ul>
                <div class="plan-goal">🎯 目标：{{ plan.goal }}</div>
              </el-timeline-item>
            </el-timeline>
          </div>
        </el-col>

        <!-- 右：技术路线 + 练习建议 -->
        <el-col :span="10">
          <!-- 技术学习路线 -->
          <div class="advice-section" v-if="adviceData.advice?.learning_roadmap">
            <div class="advice-section-title">🗺️ 技术学习路线（{{ adviceData.advice.learning_roadmap.total_weeks }}周）</div>
            <div
              v-for="(phase, pi) in adviceData.advice.learning_roadmap.phases"
              :key="pi"
              class="roadmap-phase"
            >
              <div class="roadmap-phase-header">
                <el-tag type="primary" size="small">{{ phase.weeks }}</el-tag>
                <span class="roadmap-phase-name">{{ phase.phase }}</span>
              </div>
              <div class="roadmap-topics">
                <el-tag
                  v-for="(t, ti) in phase.topics"
                  :key="ti"
                  type="info"
                  size="small"
                  style="margin: 2px;"
                >{{ t }}</el-tag>
              </div>
              <div class="roadmap-resources">
                <span v-for="(r, ri) in phase.resources" :key="ri" class="resource-item">📖 {{ r }}</span>
              </div>
            </div>
          </div>

          <!-- 练习建议 -->
          <div class="advice-section" v-if="adviceData.advice?.practice_suggestions?.length">
            <div class="advice-section-title">💪 练习建议</div>
            <div
              v-for="(ps, i) in adviceData.advice.practice_suggestions"
              :key="i"
              class="practice-row"
            >
              <el-tag
                :type="ps.type === '刷题' ? 'danger' : ps.type === '项目' ? 'success' : 'warning'"
                size="small"
                style="min-width: 40px;"
              >{{ ps.type }}</el-tag>
              <div class="practice-content">
                <span>{{ ps.content }}</span>
                <span class="practice-freq">{{ ps.frequency }}</span>
              </div>
            </div>
          </div>
        </el-col>
      </el-row>

      <!-- 推荐学习链接 -->
      <div class="advice-section learning-links-section" v-if="adviceData.advice?.learning_resources?.length">
        <div class="advice-section-title">🔗 推荐学习资源（结合历史薄弱点）</div>
        <div class="learning-link-grid">
          <div
            v-for="(lr, li) in adviceData.advice.learning_resources"
            :key="li"
            class="learning-link-card"
          >
            <div class="ll-title">
              <el-link :href="lr.url" target="_blank" type="primary">{{ lr.title }}</el-link>
            </div>
            <div class="ll-topic" v-if="lr.topic"><el-tag size="small" type="info">{{ lr.topic }}</el-tag></div>
            <p class="ll-reason" v-if="lr.reason">{{ lr.reason }}</p>
          </div>
        </div>
      </div>

      <!-- 深度知识点 / 面试题 / 沟通延伸阅读 -->
      <div
        class="advice-section enrich-section"
        v-if="adviceData.advice?.deep_dive_knowledge?.length || adviceData.advice?.star_interview_questions?.length || adviceData.advice?.communication_readings?.length"
      >
        <div class="advice-section-title">📌 深度学习与表达拓展</div>
        <el-row :gutter="16">
          <el-col :xs="24" :md="8" v-if="adviceData.advice?.deep_dive_knowledge?.length">
            <div class="enrich-card">
              <div class="enrich-card-head">技术知识点强化</div>
              <div
                v-for="(dk, di) in adviceData.advice.deep_dive_knowledge"
                :key="'dk'+di"
                class="enrich-block"
              >
                <div class="enrich-topic">{{ dk.topic }}</div>
                <p class="enrich-why">{{ dk.why }}</p>
                <p class="enrich-steps" v-if="dk.study_steps"><span class="enrich-label">步骤</span>{{ dk.study_steps }}</p>
              </div>
            </div>
          </el-col>
          <el-col :xs="24" :md="8" v-if="adviceData.advice?.star_interview_questions?.length">
            <div class="enrich-card enrich-card--q">
              <div class="enrich-card-head">高频面试题演练</div>
              <div
                v-for="(sq, si) in adviceData.advice.star_interview_questions"
                :key="'sq'+si"
                class="enrich-block"
              >
                <div class="enrich-q">{{ sq.question }}</div>
                <p class="enrich-outline" v-if="sq.answer_outline"><span class="enrich-label">要点</span>{{ sq.answer_outline }}</p>
                <p class="enrich-pitfall" v-if="sq.pitfalls">易错：{{ sq.pitfalls }}</p>
              </div>
            </div>
          </el-col>
          <el-col :xs="24" :md="8" v-if="adviceData.advice?.communication_readings?.length">
            <div class="enrich-card enrich-card--comm">
              <div class="enrich-card-head">沟通技巧与文章</div>
              <div
                v-for="(cr, ci) in adviceData.advice.communication_readings"
                :key="'cr'+ci"
                class="enrich-block"
              >
                <div class="enrich-comm-title">
                  <el-link v-if="isHttpUrl(cr.url)" :href="cr.url" target="_blank" type="primary">{{ cr.title }}</el-link>
                  <span v-else>{{ cr.title }}</span>
                </div>
                <p class="enrich-why">{{ cr.summary }}</p>
                <p class="enrich-steps" v-if="cr.practice_tip"><span class="enrich-label">练习</span>{{ cr.practice_tip }}</p>
              </div>
            </div>
          </el-col>
        </el-row>
      </div>

      <!-- 能力分析 -->
      <div class="advice-section" v-if="adviceData?.ability_analysis">
        <div class="advice-section-title">📊 能力分析（基于历史维度均分）</div>
        <div class="ability-grid">
          <div v-for="([dim, val], idx) in sortedDimAvg" :key="idx" class="ability-pill" :class="abilityClass(val)">
            <span class="dim">{{ dim }}</span>
            <span class="val">{{ val.toFixed(1) }}</span>
          </div>
        </div>
      </div>

      <!-- 岗位文字知识图谱 -->
      <div class="advice-section kg-text-section" v-if="textGraphLayers.length">
        <div class="advice-section-title">🧭 岗位知识图谱</div>
        <p class="kg-hint">核心技术栈与知识点概览</p>
        <el-collapse v-model="kgOpen" class="kg-text-collapse">
          <el-collapse-item v-for="(layer, li) in textGraphLayers.slice(0, 3)" :key="li + '-' + (layer.title || '')" :name="layer.title || String(li)">
            <template #title>
              <span class="kg-layer-title">{{ layer.title }}</span>
              <el-tag size="small" type="info" style="margin-left:8px">{{ layer.kind || layer.level }}</el-tag>
            </template>
            <div v-if="layer.kind === 'questions'" class="kg-q-list">
              <div v-for="(it, qi) in layer.items.slice(0, 3)" :key="qi" class="kg-q-item">
                <p class="kg-q-text">{{ it.content }}</p>
                <p v-if="it.answer_preview" class="kg-q-ans">参考：{{ it.answer_preview }}</p>
              </div>
              <div v-if="layer.items.length > 3" class="kg-more">
                <el-tag size="small" type="info">共 {{ layer.items.length }} 个问题，仅显示前 3 个</el-tag>
              </div>
            </div>
            <div v-else-if="layer.kind === 'kb_snippets'" class="kg-snippet-list">
              <div v-for="(s, si) in layer.items.slice(0, 2)" :key="si" class="kg-snippet">
                <div class="kg-snippet-meta">
                  <el-tag size="small" type="success">知识库</el-tag>
                  <span class="fn">{{ s.filename || '文档' }}</span>
                  <router-link v-if="s.file_id" :to="'/interview/knowledge'" class="kg-link">去知识库</router-link>
                </div>
                <p class="kg-snippet-p">{{ s.snippet }}</p>
              </div>
              <div v-if="layer.items.length > 2" class="kg-more">
                <el-tag size="small" type="info">共 {{ layer.items.length }} 个片段，仅显示前 2 个</el-tag>
              </div>
            </div>
            <ul v-else class="kg-simple-list">
              <li v-for="(it, ii) in layer.items.slice(0, 5)" :key="ii">{{ typeof it === 'object' ? (it.label || it.title || '') : it }}</li>
              <li v-if="layer.items.length > 5" class="kg-more-item">
                <el-tag size="small" type="info">共 {{ layer.items.length }} 项，仅显示前 5 个</el-tag>
              </li>
            </ul>
          </el-collapse-item>
          <el-collapse-item v-if="textGraphLayers.length > 3" name="more">
            <template #title>
              <span class="kg-layer-title">更多内容</span>
              <el-tag size="small" type="warning" style="margin-left:8px">展开查看</el-tag>
            </template>
            <div v-for="(layer, idx) in textGraphLayers.slice(3)" :key="'more-' + idx" class="kg-layer">
              <div class="kg-layer-header">
                <span class="kg-layer-title">{{ layer.title }}</span>
                <el-tag size="small" type="info" style="margin-left:8px">{{ layer.kind }}</el-tag>
              </div>
              <ul v-if="Array.isArray(layer.items)" class="kg-simple-list">
                <li v-for="(it, ii) in layer.items" :key="ii">{{ typeof it === 'object' ? (it.label || it.title || '') : it }}</li>
              </ul>
              <p v-else class="kg-simple-text">{{ layer.items }}</p>
            </div>
          </el-collapse-item>
        </el-collapse>
      </div>
    </div>
  </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { getInterviewHistory, getGrowthAdvice, getJobKnowledgeMap, getInterviewJobs } from '@/api/endpoints'
import { notifyError, notifyInfo } from '@/utils/appNotify'

const growthData = ref([])
const loading = ref(false)
const activeJobId = ref(0)

const resolveActiveJobId = async () => {
  const cached = Number(localStorage.getItem('active_job_id') || 0)
  if (cached > 0) return cached
  const jobsRes = await getInterviewJobs()
  const first = Array.isArray(jobsRes?.jobs) ? jobsRes.jobs[0] : null
  const firstId = Number(first?.job_id || 0)
  if (firstId > 0) {
    localStorage.setItem('active_job_id', String(firstId))
    return firstId
  }
  return 0
}

const loadGrowthData = async () => {
  loading.value = true
  try {
    activeJobId.value = await resolveActiveJobId()
    if (!activeJobId.value) {
      growthData.value = []
      return
    }
    const data = await getInterviewHistory(activeJobId.value)
    const historyList = data.history_list || []

    // 过滤有分数的已结束面试，转换为成长曲线数据
    // 后端返回字段：status="面试结束", score=0-10, time="2026-xx-xx ..."
    const filtered = historyList
      .filter(item => item.status === '面试结束' && item.score != null)
      .map(item => ({
        date: (item.time || '').split(' ')[0] || item.time || '未知',
        score: Math.round(Number(item.score) * 10), // 0-10 → 0-100
        job: item.job || '',
        level: item.level || '',
        strong_dims: item.strong_dims || [],
        weak_dims: item.weak_dims || [],
      }))
      .sort((a, b) => new Date(a.date) - new Date(b.date))

    growthData.value = filtered

    if (filtered.length === 0) {
      notifyInfo('暂无已完成面试记录，完成面试后可查看成长曲线', '成长曲线')
    }
  } catch (err) {
    console.error('加载成长曲线失败:', err)
    notifyError('获取面试历史失败，请检查网络连接', '成长曲线')
    growthData.value = []
  } finally {
    loading.value = false
  }
}

// ── 统计数据 ───────────────────────────────────────────
const averageScore = computed(() => {
  if (!growthData.value.length) return '--'
  const sum = growthData.value.reduce((a, b) => a + b.score, 0)
  return (sum / growthData.value.length / 10).toFixed(1)
})

const maxScoreRaw = computed(() => {
  if (!growthData.value.length) return 0
  return Math.max(...growthData.value.map(d => d.score))
})

const highestScore = computed(() => {
  if (!growthData.value.length) return '--'
  return (maxScoreRaw.value / 10).toFixed(1)
})

const growthRate = computed(() => {
  if (growthData.value.length < 2) return '--'
  const first = growthData.value[0].score
  const last = growthData.value[growthData.value.length - 1].score
  if (first === 0) return '--'
  const rate = Math.round(((last - first) / first) * 100)
  return (rate > 0 ? '+' : '') + rate
})

// ── SVG 图表尺寸 ────────────────────────────────────────
const svgW = 780
const svgH = 220
const padL = 44  // 左留 Y 轴标注
const padR = 20
const padT = 20
const padB = 28  // 下留 X 轴日期

const minScore = computed(() => {
  if (!growthData.value.length) return 0
  return Math.max(0, Math.min(...growthData.value.map(d => d.score)) - 10)
})
const maxScore = computed(() => {
  if (!growthData.value.length) return 100
  return Math.min(100, maxScoreRaw.value + 10)
})

const getX = (index) => {
  const n = growthData.value.length
  if (n <= 1) return (svgW - padL - padR) / 2 + padL
  return padL + (index / (n - 1)) * (svgW - padL - padR)
}

const getY = (score) => {
  const range = maxScore.value - minScore.value || 1
  return svgH - padB - ((score - minScore.value) / range) * (svgH - padT - padB)
}

// Y 轴参考线
const yLines = computed(() => {
  const mn = minScore.value, mx = maxScore.value
  const step = mx - mn <= 30 ? 5 : 10
  const lines = []
  for (let v = Math.ceil(mn / step) * step; v <= mx; v += step) {
    lines.push({ val: v, label: (v / 10).toFixed(1) })
  }
  return lines
})

// X 轴标签（最多 8 个，防止拥挤）
const xLabels = computed(() => {
  const n = growthData.value.length
  if (!n) return []
  const step = Math.ceil(n / 8)
  return growthData.value
    .map((d, i) => ({ idx: i, date: d.date.slice(5) }))
    .filter((_, i) => i % step === 0 || i === n - 1)
})

const curvePath = computed(() => {
  const d = growthData.value
  if (!d.length) return ''
  if (d.length === 1) return `M ${getX(0)} ${getY(d[0].score)}`
  let path = `M ${getX(0)} ${getY(d[0].score)}`
  for (let i = 1; i < d.length; i++) {
    const x0 = getX(i - 1), y0 = getY(d[i - 1].score)
    const x1 = getX(i),     y1 = getY(d[i].score)
    const cpx = (x0 + x1) / 2
    path += ` C ${cpx} ${y0}, ${cpx} ${y1}, ${x1} ${y1}`
  }
  return path
})

const areaPath = computed(() => {
  const d = growthData.value
  if (!d.length) return ''
  const baseline = svgH - padB
  let path = `M ${getX(0)} ${baseline} L ${getX(0)} ${getY(d[0].score)}`
  for (let i = 1; i < d.length; i++) {
    const x0 = getX(i - 1), y0 = getY(d[i - 1].score)
    const x1 = getX(i),     y1 = getY(d[i].score)
    const cpx = (x0 + x1) / 2
    path += ` C ${cpx} ${y0}, ${cpx} ${y1}, ${x1} ${y1}`
  }
  path += ` L ${getX(d.length - 1)} ${baseline} Z`
  return path
})

const getPointFill = (score) => {
  if (score >= 85) return '#67c23a'
  if (score >= 70) return '#409eff'
  if (score >= 50) return '#e6a23c'
  return '#f56c6c'
}

// ── 能力提升反馈模块 ───────────────────────────────────
const adviceLoading = ref(false)
const adviceData = ref(null)
const adviceError = ref('')
const graphLoading = ref(false)
const selectedPosition = ref('')

// 从成长曲线数据中提取岗位列表
const positionList = computed(() => {
  const positions = [...new Set(growthData.value.map(d => d.job).filter(Boolean))]
  return positions
})

const textGraphExtra = ref(null)
const kgOpen = ref([])

const loadTextGraphForPosition = async () => {
  const pos = (selectedPosition.value || '').trim()
    || (positionList.value[0] || '')
  if (!pos) return
  graphLoading.value = true
  try {
    const data = await getJobKnowledgeMap(pos, '')
    textGraphExtra.value = data?.data || null
  } catch {
    textGraphExtra.value = null
  } finally {
    graphLoading.value = false
  }
}

const fetchGrowthAdvice = async () => {
  adviceLoading.value = true
  adviceError.value = ''
  adviceData.value = null
  textGraphExtra.value = null
  try {
    const jobId = activeJobId.value || await resolveActiveJobId()
    if (!jobId) {
      adviceError.value = '请先开始一场面试，生成岗位后再获取成长建议'
      return
    }
    const res = await getGrowthAdvice(selectedPosition.value, jobId)
    if (!res.has_data) {
      adviceError.value = res.message || '暂无历史面试数据'
      return
    }
    adviceData.value = res
    // 不阻塞主建议展示：图谱异步加载
    loadTextGraphForPosition()
  } catch (err) {
    adviceError.value = '获取建议失败，请检查网络连接'
    notifyError(adviceError.value, '成长建议')
  } finally {
    adviceLoading.value = false
  }
}

const textGraphLayers = computed(() => {
  const fromAdvice = adviceData.value?.knowledge_map?.layers
  if (fromAdvice && fromAdvice.length) return fromAdvice
  const ex = textGraphExtra.value?.layers
  return ex && ex.length ? ex : []
})

const sortedDimAvg = computed(() => {
  const d = adviceData.value?.ability_analysis?.dimension_avg
  if (!d || typeof d !== 'object') return []
  return Object.entries(d).sort((a, b) => b[1] - a[1])
})

const abilityClass = (val) => {
  if (val >= 8) return 'is-high'
  if (val >= 6.5) return 'is-mid'
  return 'is-low'
}

watch(selectedPosition, () => {
  loadTextGraphForPosition()
})

watch(
  textGraphLayers,
  (layers) => {
    if (layers && layers.length) {
      kgOpen.value = layers.slice(0, 6).map((l) => l.title).filter(Boolean)
    }
  },
  { immediate: true },
)

const getPriorityType = (priority) => {
  if (priority === '高') return 'danger'
  if (priority === '中') return 'warning'
  return 'info'
}

const isHttpUrl = (u) => /^https?:\/\//i.test(String(u || '').trim())

onMounted(async () => {
  await loadGrowthData()
  await loadTextGraphForPosition()
})
</script>

<style scoped>
.growth-page {
  max-width: min(1200px, var(--page-max-width));
  margin: 0 auto;
  padding: 0 6px calc(var(--section-gap) + 8px);
  background: #ffffff;
}

.growth-page :deep(.el-card) {
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-md);
  background: #ffffff;
  transition: box-shadow var(--transition), transform var(--transition), border-color var(--transition);
}

.growth-page :deep(.el-card:hover) {
  box-shadow: var(--shadow-lg);
  border-color: rgba(37, 99, 235, 0.25);
  transform: translateY(-4px);
}

.section-card {
  max-width: 1200px;
  margin: 0 auto 24px;
}

.card-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 4px;
}

.card-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text-primary);
  letter-spacing: -0.02em;
  display: flex;
  align-items: center;
  gap: 8px;
}

.dim-timeline-wrap {
  margin-bottom: 20px;
  padding: 20px 24px;
  background: #ffffff;
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-sm);
}

.dim-timeline-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--color-text-primary);
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.dim-chip-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 12px;
  padding: 12px 0;
  border-bottom: 1px dashed var(--color-border);
  font-size: 13px;
}

.dim-chip-row:last-child {
  border-bottom: none;
}

.dim-chip-date {
  color: var(--color-text-muted);
  min-width: 96px;
  font-weight: 500;
}

.dim-chip-job {
  color: var(--color-text-primary);
  font-weight: 600;
  margin-right: 8px;
  font-size: 14px;
}

.ability-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.ability-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border-radius: 999px;
  font-size: 13px;
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  transition: all 0.3s ease;
}

.ability-pill:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
}

.ability-pill .val {
  font-weight: 800;
  font-size: 16px;
}

.ability-pill.is-high { 
  border-color: rgba(5, 150, 105, 0.45); 
  color: #047857;
  background: linear-gradient(135deg, #f0fdf4 0%, #ffffff 100%);
}

.ability-pill.is-mid { 
  border-color: rgba(37, 99, 235, 0.35); 
  color: #1d4ed8;
  background: linear-gradient(135deg, #eff6ff 0%, #ffffff 100%);
}

.ability-pill.is-low { 
  border-color: rgba(220, 38, 38, 0.35); 
  color: #b91c1c;
  background: linear-gradient(135deg, #fef2f2 0%, #ffffff 100%);
}

.kg-text-section {
  margin-top: 12px;
}

.kg-text-collapse {
  border: none !important;
}

.kg-text-collapse :deep(.el-collapse-item__header) {
  border-radius: var(--radius-md);
  padding: 12px 16px;
  background: #ffffff;
  margin-bottom: 10px;
  font-weight: 600;
  color: var(--color-text-primary);
  border: 1px solid var(--color-border);
  transition: all 0.3s ease;
}

.kg-text-collapse :deep(.el-collapse-item__header:hover) {
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
}

.kg-text-collapse :deep(.el-collapse-item__wrap) {
  border: none !important;
}

.kg-layer-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.kg-q-item {
  padding: 12px 16px;
  margin-bottom: 10px;
  background: #ffffff;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  transition: all 0.3s ease;
}

.kg-q-item:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
}

.kg-q-text {
  margin: 0;
  font-size: 14px;
  color: var(--color-text-secondary);
  line-height: 1.6;
  font-weight: 500;
}

.kg-q-ans {
  margin: 10px 0 0;
  font-size: 13px;
  color: var(--color-text-muted);
  line-height: 1.5;
}

.kg-snippet {
  padding: 12px 16px;
  margin-bottom: 10px;
  border-radius: var(--radius-md);
  background: #ffffff;
  border: 1px solid var(--color-border);
  transition: all 0.3s ease;
}

.kg-snippet:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
}

.kg-snippet-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
  font-size: 12px;
  color: var(--color-text-muted);
}

.kg-snippet-meta .fn {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 500;
}

.kg-link {
  font-size: 13px;
  color: var(--color-primary);
  font-weight: 500;
  transition: color 0.3s ease;
}

.kg-link:hover {
  color: var(--color-primary-dark);
}

.kg-snippet-p {
  margin: 0;
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.6;
}

.kg-simple-list {
  margin: 0;
  padding-left: 20px;
  color: var(--color-text-secondary);
  font-size: 14px;
  line-height: 1.8;
}

.kg-more {
  margin-top: 12px;
  text-align: center;
}

.kg-more-item {
  list-style: none;
  margin-top: 10px;
  text-align: center;
}

.kg-more-hint {
  font-size: 13px;
  color: var(--color-text-muted);
  text-align: center;
  margin: 0;
  padding: 12px 0;
}

.chart-wrapper {
  margin-top: 20px;
  padding: 20px 16px 12px;
  background: #ffffff;
  border-radius: var(--radius-lg);
  overflow: hidden;
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-sm);
}

.curve-chart {
  width: 100%;
  height: 240px;
  display: block;
}

.data-point {
  cursor: pointer;
  transition: r 0.2s ease;
  animation: pointAppear 0.4s ease-out forwards;
  opacity: 0;
}

.data-point:hover {
  filter: drop-shadow(0 0 6px rgba(37, 99, 235, 0.8));
  r: 7;
}

@keyframes pointAppear {
  to { opacity: 1; }
}

.empty-growth {
  text-align: center;
  padding: 60px 20px;
}

.growth-stats {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid var(--color-border);
}

.stat-card {
  text-align: center;
  padding: 20px 16px;
  background: #ffffff;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-sm);
  transition: transform var(--transition), box-shadow var(--transition);
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-md);
}

.stat-value {
  font-size: 28px;
  font-weight: 800;
  background: var(--gradient-primary);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 8px;
  letter-spacing: -0.03em;
}

.stat-label {
  font-size: 12px;
  color: var(--color-text-muted);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* ── 能力提升模块 ── */
.advice-card {
  max-width: 1200px;
  margin: 12px auto 0;
}

.advice-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

.advice-placeholder {
  text-align: center;
  padding: 60px 20px;
  color: var(--color-text-muted);
  font-size: 15px;
  line-height: 2;
}

.advice-placeholder-icon {
  font-size: 56px;
  margin-bottom: 16px;
}

.advice-loading {
  padding: 24px;
}

/* 整体建议横幅 */
.advice-banner {
  background: #ffffff;
  border-radius: var(--radius-lg);
  padding: 24px 28px;
  border-left: 4px solid var(--color-primary);
  box-shadow: var(--shadow-sm);
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 24px;
  margin-bottom: 24px;
  border: 1px solid var(--color-border);
}

.advice-banner-text {
  flex: 1;
}

.advice-overall {
  font-size: 15px;
  color: var(--color-text-primary);
  font-weight: 500;
  line-height: 1.7;
}

.advice-motive {
  font-size: 14px;
  color: var(--color-success);
  margin-top: 8px;
  font-style: italic;
  font-weight: 500;
}

.advice-meta {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-end;
}

/* 各区块 */
.advice-section {
  margin-bottom: 24px;
}

.advice-section-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--color-text-primary);
  margin-bottom: 16px;
  padding-bottom: 10px;
  border-bottom: 2px solid var(--color-primary-pale);
  letter-spacing: -0.01em;
  display: flex;
  align-items: center;
  gap: 8px;
}

.growth-page :deep(.el-timeline-item__tail) {
  border-left: 2px solid var(--color-border);
}

.growth-page :deep(.el-timeline-item__node) {
  box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.15);
}

.growth-page :deep(.el-timeline-item__wrapper) {
  padding-bottom: 12px;
}

/* 薄弱点 */
.weak-point-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  padding: 16px 20px;
  background: #ffffff;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-sm);
  transition: border-color var(--transition), box-shadow var(--transition), transform var(--transition);
}

.weak-point-row:hover {
  border-color: rgba(37, 99, 235, 0.3);
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.weak-dim {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
  min-width: 70px;
}

.weak-issue {
  font-size: 13px;
  color: var(--color-text-secondary);
  flex: 1;
  line-height: 1.5;
}

/* 改进计划时间线 */
.plan-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.plan-week {
  font-size: 13px;
  font-weight: 700;
  color: var(--color-primary);
  background: var(--color-primary-pale);
  padding: 4px 12px;
  border-radius: 999px;
}

.plan-focus {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.plan-tasks {
  margin: 6px 0 8px 20px;
  padding: 0;
}

.plan-tasks li {
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.8;
  margin-bottom: 4px;
}

.plan-goal {
  font-size: 13px;
  color: var(--color-success);
  font-weight: 600;
  background: rgba(16, 185, 129, 0.1);
  padding: 4px 12px;
  border-radius: 999px;
  display: inline-block;
}

/* 技术路线 */
.roadmap-phase {
  background: #ffffff;
  border-radius: var(--radius-md);
  padding: 18px 20px;
  margin-bottom: 14px;
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-sm);
  transition: box-shadow var(--transition), transform var(--transition);
}

.roadmap-phase:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.roadmap-phase-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.roadmap-phase-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.roadmap-topics {
  margin-bottom: 10px;
}

.roadmap-resources {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.resource-item {
  font-size: 12px;
  color: var(--color-text-muted);
  line-height: 1.5;
}

/* 练习建议 */
.practice-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 12px;
  padding: 12px 16px;
  background: #ffffff;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  transition: all 0.3s ease;
}

.practice-row:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
}

.practice-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.practice-content span:first-child {
  font-size: 13px;
  color: var(--color-text-primary);
  line-height: 1.6;
  font-weight: 500;
}

.practice-freq {
  font-size: 12px !important;
  color: var(--color-text-muted) !important;
  font-weight: 500;
}

.learning-links-section {
  margin-top: 28px;
  padding-top: 20px;
  border-top: 2px solid var(--color-primary-pale);
}

.learning-link-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.learning-link-card {
  padding: 18px 20px;
  border-radius: var(--radius-md);
  background: #ffffff;
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-sm);
  transition: transform var(--transition), box-shadow var(--transition), border-color var(--transition);
}

.learning-link-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-md);
  border-color: rgba(37, 99, 235, 0.25);
}

.ll-title {
  font-weight: 600;
  margin-bottom: 8px;
  font-size: 14px;
  color: var(--color-text-primary);
}

.ll-topic {
  margin-bottom: 8px;
}

.ll-reason {
  margin: 0;
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.6;
}

.enrich-section {
  margin-top: 28px;
  padding-top: 20px;
  border-top: 2px solid var(--color-primary-pale);
}

.enrich-card {
  padding: 16px 18px;
  border-radius: var(--radius-md);
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-sm);
  height: 100%;
  transition: transform var(--transition), box-shadow var(--transition), border-color var(--transition);
}

.enrich-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-md);
  border-color: rgba(37, 99, 235, 0.22);
}

.enrich-card--q {
  background: linear-gradient(180deg, #ffffff 0%, #f5f9ff 100%);
}

.enrich-card--comm {
  background: linear-gradient(180deg, #ffffff 0%, #f6fffa 100%);
}

.enrich-card-head {
  font-size: 14px;
  font-weight: 700;
  color: var(--color-primary-dark);
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px dashed var(--color-border);
}

.enrich-block {
  margin-bottom: 14px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.25);
}

.enrich-block:last-child {
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
}

.enrich-topic,
.enrich-q {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
  line-height: 1.5;
}

.enrich-why,
.enrich-outline {
  margin: 6px 0 0;
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.65;
}

.enrich-steps,
.enrich-pitfall {
  margin: 8px 0 0;
  font-size: 12px;
  color: var(--color-text-muted);
  line-height: 1.55;
}

.enrich-label {
  display: inline-block;
  margin-right: 6px;
  padding: 0 8px;
  border-radius: 999px;
  background: var(--color-primary-pale);
  color: var(--color-primary-dark);
  font-size: 11px;
  font-weight: 600;
}

.enrich-comm-title {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 6px;
}

.kg-section {
  margin-top: 24px;
}

.kg-hint {
  font-size: 13px;
  color: var(--color-text-muted);
  margin: 0 0 12px;
  font-weight: 500;
}

.kg-svg-wrap {
  background: #ffffff;
  border-radius: var(--radius-md);
  padding: 16px;
  overflow-x: auto;
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-sm);
}

.kg-svg {
  width: 100%;
  min-width: 480px;
  height: 280px;
  display: block;
}
</style>
