<template>
  <div class="job-position-select">
    <el-select
      :model-value="modelValue"
      :placeholder="placeholder"
      :loading="loading"
      filterable
      clearable
      :class="['job-position-select__inner', { 'is-error': showError }]"
      :style="wrapStyle"
      size="default"
      :teleported="true"
      popper-class="job-position-select-dropdown"
      @update:model-value="onInput"
    >
      <el-option
        v-for="j in options"
        :key="j.id"
        :label="j.job_name"
        :value="j.job_name"
      >
        <span class="job-opt-name">{{ j.job_name }}</span>
        <span v-if="techPreview(j).length" class="job-opt-tech">{{ techPreview(j).join(' · ') }}</span>
      </el-option>
    </el-select>
    <p v-if="showError" class="job-position-select__err">{{ requiredMessage }}</p>
    <p v-if="techPreview(selectedRow).length && !showError" class="job-position-select__hint">
      <span class="lbl">技术栈</span>
      {{ techPreview(selectedRow).join('、') }}
    </p>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { getKnowledgeJobs } from '@/api/endpoints'

const props = defineProps({
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: '请搜索并选择岗位（必选）' },
  requiredMessage: { type: String, default: '请选择岗位' },
  showError: { type: Boolean, default: false },
  width: { type: String, default: '100%' },
})

const emit = defineEmits(['update:modelValue'])

const loading = ref(false)
const options = ref([])

const wrapStyle = computed(() => ({ width: props.width }))

const selectedRow = computed(() => {
  const n = (props.modelValue || '').trim()
  if (!n) return null
  return options.value.find((x) => x.job_name === n) || null
})

const techPreview = (row) => {
  if (!row) return []
  const ts = row.tech_stack
  if (Array.isArray(ts)) return ts.filter(Boolean).slice(0, 12)
  if (ts && typeof ts === 'object') return Object.values(ts).filter(Boolean).slice(0, 12).map(String)
  return []
}

const onInput = (v) => {
  emit('update:modelValue', v || '')
}

const loadJobs = async () => {
  loading.value = true
  try {
    const res = await getKnowledgeJobs()
    const list = res?.data?.jobs ?? []
    options.value = Array.isArray(list) ? list : []
  } catch {
    options.value = []
  } finally {
    loading.value = false
  }
}

onMounted(loadJobs)

defineExpose({ reload: loadJobs, options })
</script>

<style scoped>
.job-position-select {
  width: 100%;
}
.job-position-select__inner {
  width: 100%;
}
.job-position-select__inner :deep(.el-select__wrapper) {
  border-radius: 12px;
  min-height: 42px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06);
  border: 1px solid var(--color-border, #e2e8f0);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.job-position-select__inner:not(.is-error) :deep(.el-select__wrapper:hover) {
  border-color: rgba(37, 99, 235, 0.35);
}
.job-position-select__inner :deep(.el-select__wrapper.is-focused) {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}
.job-position-select__inner.is-error :deep(.el-select__wrapper) {
  border-color: #f56c6c;
}
.job-position-select__err {
  margin: 8px 0 0;
  font-size: 12px;
  color: #f56c6c;
}
.job-position-select__hint {
  margin: 10px 0 0;
  font-size: 13px;
  line-height: 1.55;
  color: #64748b;
}
.job-position-select__hint .lbl {
  color: #94a3b8;
  margin-right: 6px;
}
.job-opt-name {
  font-weight: 600;
  color: #0f172a;
}
.job-opt-tech {
  display: block;
  font-size: 11px;
  color: #94a3b8;
  margin-top: 2px;
  max-width: 420px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>

<style>
.job-position-select-dropdown.el-select-dropdown {
  border-radius: 12px !important;
  border: 1px solid rgba(148, 163, 184, 0.35) !important;
  box-shadow: 0 16px 40px rgba(30, 58, 95, 0.14) !important;
  padding: 6px 0 !important;
}
.job-position-select-dropdown .el-select-dropdown__item {
  height: auto !important;
  min-height: 40px;
  line-height: 1.35 !important;
  padding: 8px 14px !important;
}
</style>
