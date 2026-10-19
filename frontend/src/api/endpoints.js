import axios from 'axios'
import request from '@/utils/request'

// ==================== 简历 ====================

export const uploadResumeApi = (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return request.post('/resume/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
}

export const analyzeResumeApi = (formData) => {
    return request.post('/resume/analyze', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
}

export const optimizeAndDownloadResumeApi = (resumeData) => {
    return request.post('/resume/optimize-data', resumeData)
}

export async function downloadResumeDocx(resumeData, format = 'docx') {
    const f = format === 'pdf' ? 'pdf' : 'docx'
    return await request.post('/resume/download/docx', resumeData, {
        params: { format: f },
        responseType: 'blob',
    })
}

export async function downloadResume(resumeId, format = 'docx') {
    if (!resumeId) throw new Error('简历 ID 不能为空')
    const f = format === 'pdf' ? 'pdf' : 'docx'
    return await request.get(`/resume/download/${resumeId}`, {
        params: { format: f },
        responseType: 'blob',
    })
}

/** 简历历史列表（用于引导等） */
export async function getResumeHistory() {
    return await request.get('/resume/history')
}

export async function generateResume(userInfo) {
    return await request.post('/resume/generate', userInfo)
}

// ==================== 用户 ====================

export async function login(username, password) {
    return await request.post('/user/login', { username, password })
}

export async function register(
    username,
    email,
    password,
    accountType = 'personal',
    companyName = '',
    companyCode = ''
) {
    return await request.post('/user/register', {
        username,
        email,
        password,
        account_type: accountType,
        company_name: companyName,
        company_code: companyCode,
    })
}

export async function getUserInfo() {
    return await request.get('/user/info')
}

export async function saveUserProfile(updateData) {
    return await request.put('/user/profile', updateData)
}

// ==================== 面试 ====================

export async function startInterview(
    jobId,
    mode = 'text',
    difficulty = 'entry',
    interviewerStyle = 'rigorous',
    language = 'zh',
    profileContext = undefined,
    resumeContext = undefined
) {
    const body = {
        job_id: jobId,
        mode,
        difficulty,
        interviewer_style: interviewerStyle,
        language,
    }
    if (profileContext !== undefined) body.profile_context = profileContext
    if (resumeContext !== undefined) body.resume_context = resumeContext
    return await request.post('/interview/start', body)
}

/** 面试开始页：个人资料 + 最新简历摘要默认值 */
export async function getInterviewContextPreview() {
    return await request.get('/interview/context-preview')
}

export async function getInterviewPositions() {
    return await request.get('/interview/positions')
}

export async function submitTextAnswer(interviewId, answer, jobId) {
    return await request.post(
        '/interview/answer/text',
        { interview_id: interviewId, answer },
        { params: { job_id: jobId } },
    )
}

export async function submitTextAnswerStream(interviewId, answer, jobId) {
    const token = localStorage.getItem('token')
    const response = await fetch(`/api/interview/answer/text/stream?job_id=${encodeURIComponent(jobId)}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': token ? `Bearer ${token}` : '',
        },
        body: JSON.stringify({ interview_id: interviewId, answer }),
    })
    if (!response.ok) {
        const errData = await response.json().catch(() => ({}))
        throw new Error(errData.message || errData.detail || `请求失败：HTTP ${response.status}`)
    }
    return response.body
}

export async function submitSpeechAnswer(interviewId, audioBlob, jobId) {
    const formData = new FormData()
    formData.append('file', audioBlob, 'recording.webm')
    formData.append('interview_id', interviewId)
    formData.append('job_id', String(jobId))
    return await request.post('/interview/answer/speech', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
}

export async function submitVideoAnswer(interviewId, videoBlob, jobId) {
    const formData = new FormData()
    formData.append('file', videoBlob, 'interview_video.webm')
    formData.append('interview_id', interviewId)
    formData.append('job_id', String(jobId))
    return await request.post('/interview/answer/video', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
}

export async function uploadVideoStream(interviewId, videoChunk) {
    const formData = new FormData()
    formData.append('file', videoChunk, `chunk_${Date.now()}.webm`)
    formData.append('interview_id', interviewId)
    formData.append('chunk', 'true')
    return await request.post('/interview/answer/video/stream', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
}

export async function endInterviewApi(jobId) {
    return await request.post('/interview/end', null, { params: { job_id: jobId } })
}

export async function getInterviewHistory(jobId) {
    return await request.get('/interview/history', { params: { job_id: jobId } })
}

export async function getInterviewStats(jobId) {
    return await request.get('/interview/stats', { params: { job_id: jobId } })
}

export async function getInterviewDetail(interviewId, jobId) {
    return await request.get(`/interview/detail/${interviewId}`, { params: { job_id: jobId } })
}

export async function downloadReport(interviewId, format = 'docx', jobId) {
    if (!interviewId) throw new Error('面试 ID 不能为空')
    const f = format === 'pdf' ? 'pdf' : 'docx'
    return await request.get(`/interview/download/${interviewId}`, {
        params: { format: f, job_id: jobId },
        responseType: 'blob',
    })
}

export async function getGrowthAdvice(position = '', jobId) {
    const params = {}
    if (position) params.position = position
    if (jobId) params.job_id = jobId
    return await request.get('/interview/growth-advice', { params, timeout: 90000 })
}

export async function getInterviewJobs() {
    const res = await request.get('/interview/positions')
    const payload = res?.data ?? res
    const list = Array.isArray(payload?.positions) ? payload.positions : []
    const jobs = list
        .map((row) => ({
            job_id: Number(row?.job_id || row?.id || 0),
            job_name: String(row?.job_name || row?.name || '').trim(),
        }))
        .filter((row) => row.job_id > 0 && row.job_name)
    return { jobs, total: jobs.length }
}

/** 讯飞虚拟人：配置 */
export async function getVirtualHumanConfig() {
    return await request.get('/interview/virtual-human/config')
}

export async function startVirtualHumanSession() {
    return await request.post('/interview/virtual-human/start')
}

export async function virtualHumanSpeak(text) {
    const form = new FormData()
    form.append('text', text)
    return await request.post('/interview/virtual-human/speak', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
    })
}

export async function stopVirtualHumanSession() {
    return await request.post('/interview/virtual-human/stop')
}

// ==================== 题库 ====================

export async function importQuestions(file, position) {
    throw new Error('题库上传已下线，请改为上传知识库文档')
}

export async function getQuestions(position, opts = {}) {
    const params = {}
    if (position) params.position = position
    if (opts.difficulty) params.difficulty = opts.difficulty
    if (opts.category) params.category = opts.category
    if (opts.limit != null) params.limit = opts.limit
    if (opts.offset != null) params.offset = opts.offset
    return await request.get('/question/list', { params })
}

/** 导出题库为 CSV（后端 StreamingResponse，浏览器触发下载） */
export async function downloadQuestionsCsv(position = '') {
    const token = localStorage.getItem('token')
    const params = new URLSearchParams()
    if (position) params.set('position', position)
    const q = params.toString()
    const url = `/api/question/download${q ? `?${q}` : ''}`
    const response = await fetch(url, {
        method: 'GET',
        headers: {
            Authorization: token ? `Bearer ${token}` : '',
        },
    })
    if (!response.ok) {
        const err = await response.json().catch(() => ({}))
        throw new Error(err.detail || err.message || `导出失败：HTTP ${response.status}`)
    }
    const blob = await response.blob()
    const dispo = response.headers.get('Content-Disposition')
    let filename = 'questions_export.csv'
    const m = dispo && /filename\*?=(?:UTF-8'')?([^;]+)/i.exec(dispo)
    if (m) {
        try {
            filename = decodeURIComponent(m[1].replace(/['"]/g, '').trim())
        } catch {
            filename = m[1].replace(/['"]/g, '').trim()
        }
    }
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = filename
    link.click()
    URL.revokeObjectURL(link.href)
}

// ==================== 知识库（解析 + 子块向量） ====================

function kbAuthHeaders() {
    const token = localStorage.getItem('token')
    const h = {}
    if (token) h.Authorization = `Bearer ${token}`
    return h
}

/** onProgress: (0–100) => void */
export async function uploadKnowledge(file, category = 'general', description = '', onProgress) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('category', category)
    formData.append('description', description)
    const { data } = await axios.post('/api/knowledge/upload', formData, {
        headers: kbAuthHeaders(),
        timeout: 120000,
        onUploadProgress: (ev) => {
            if (typeof onProgress !== 'function' || !ev.total) return
            onProgress(Math.min(100, Math.round((ev.loaded * 100) / ev.total)))
        },
    })
    return data
}

export async function getKnowledgeFiles() {
    return await request.get('/knowledge/files')
}

export async function getKnowledgeFile(fileId) {
    return await request.get(`/knowledge/files/${fileId}`)
}

export async function getKnowledgeDetail(fileId) {
    return await request.get(`/knowledge/files/${fileId}/detail`)
}

export async function deleteKnowledgeFile(fileId) {
    return await request.delete(`/knowledge/files/${fileId}`)
}

export async function searchKnowledge(query, topK = 8, fileId = null, positionHint = null) {
    const body = { query, top_k: topK }
    if (fileId != null) body.file_id = fileId
    if (positionHint != null && String(positionHint).trim()) body.position_hint = String(positionHint).trim()
    return await request.post('/knowledge/search', body)
}

export async function getJobKnowledgeMap(jobName, q = '') {
    const params = { job_name: jobName }
    if (q) params.q = q
    return await request.get('/knowledge/job-map', { params, timeout: 25000 })
}

export async function getKnowledgeStats() {
    return await request.get('/knowledge/stats')
}

export async function getKnowledgeJobs() {
    return await request.get('/knowledge/jobs')
}

export async function getKnowledgeQuestions(params = {}) {
    return await request.get('/knowledge/questions', { params })
}

/** 求职者：企业共享 knowledge_file 是否参与检索 */
export async function setEnterpriseKnowledgeFileRetrieval(fileId, enabled) {
    return await request.put(`/knowledge/enterprise-file/${fileId}/retrieval`, { enabled })
}

// ==================== 企业管理 ====================

export async function getCompanyUsers(keyword = '') {
    const params = {}
    if (keyword) params.keyword = keyword
    return await request.get('/company/users', { params })
}

export async function getCompanyInterviews(userId = null) {
    const params = {}
    if (userId) params.user_id = userId
    return await request.get('/company/interviews', { params })
}

/** 与求职者「面试详情」接口数据结构一致（含维度分、问答、亮点/不足/建议） */
export async function getCompanyInterviewDetail(interviewId) {
    return await request.get(`/company/interviews/${interviewId}`)
}

export async function resetCompanyUserPassword(userId, newPassword) {
    const params = { new_password: newPassword }
    return await request.put(`/company/users/${userId}/password`, null, { params })
}
