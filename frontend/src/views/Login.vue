<template>
  <div class="login-page">
    <!-- 背景装饰 -->
    <div class="bg-decoration">
      <div class="bg-circle bg-circle-1"></div>
      <div class="bg-circle bg-circle-2"></div>
      <div class="bg-circle bg-circle-3"></div>
      <div class="bg-grid"></div>
    </div>

    <div class="login-wrapper">
      <div class="auth-card">
        <div class="auth-content">
          <!-- 左侧表单区 -->
          <div class="auth-left">
            <div class="auth-logo-mini">
              <span class="logo-icon">⚡</span>
              <span class="logo-text">AI 面试官</span>
            </div>

            <Transition name="form-switch" mode="out-in">
              <!-- 登录表单 -->
              <div v-if="activeAuthTab === 'login'" key="login">
                <h2 class="login-title">欢迎回来</h2>
                <p class="login-subtitle">登录您的账号，继续模拟面试之旅</p>
                <el-form :model="loginForm" @submit.prevent="handleLogin" class="login-form">
                  <el-form-item>
                    <div class="input-wrapper">
                      <span class="input-icon">👤</span>
                      <el-input v-model="loginForm.username" placeholder="请输入账号" clearable></el-input>
                    </div>
                  </el-form-item>
                  <el-form-item>
                    <div class="input-wrapper">
                      <span class="input-icon">🔒</span>
                      <el-input v-model="loginForm.password" type="password" placeholder="请输入密码" show-password></el-input>
                    </div>
                  </el-form-item>
                  <el-form-item class="form-options">
                    <div class="remember-me">
                      <input type="checkbox" id="remember">
                      <label for="remember">记住我</label>
                    </div>
                    <a href="#" class="forgot-link">忘记密码？</a>
                  </el-form-item>
                  <el-form-item>
                    <el-button type="primary" native-type="submit" class="login-btn">登 录</el-button>
                  </el-form-item>
                  <div class="login-footer">
                    <span class="other-login">还没有账号？</span>
                    <a href="#" class="register-link" @click.prevent="activeAuthTab = 'register'">立即注册</a>
                  </div>
                </el-form>
              </div>

              <!-- 注册表单 -->
              <div v-else key="register">
                <h2 class="login-title">创建账号</h2>
                <p class="login-subtitle">注册后即可开始 AI 模拟面试练习</p>
                <el-form :model="registerForm" @submit.prevent="handleRegister" class="login-form">
                  <el-form-item>
                    <el-radio-group v-model="registerForm.accountType" size="small">
                      <el-radio-button value="personal">个人账号</el-radio-button>
                      <el-radio-button value="enterprise">企业账号</el-radio-button>
                    </el-radio-group>
                  </el-form-item>
                  <el-form-item>
                    <div class="input-wrapper">
                      <span class="input-icon">👤</span>
                      <el-input v-model="registerForm.username" placeholder="请输入用户名" clearable></el-input>
                    </div>
                  </el-form-item>
                  <el-form-item>
                    <div class="input-wrapper">
                      <span class="input-icon">📧</span>
                      <el-input v-model="registerForm.email" type="email" placeholder="请输入邮箱" clearable></el-input>
                    </div>
                  </el-form-item>
                  <el-form-item v-if="registerForm.accountType === 'enterprise'">
                    <div class="input-wrapper">
                      <span class="input-icon">🏢</span>
                      <el-input v-model="registerForm.companyName" placeholder="请输入企业名称" clearable></el-input>
                    </div>
                  </el-form-item>
                  <el-form-item v-if="registerForm.accountType === 'enterprise'">
                    <div class="input-wrapper">
                      <span class="input-icon">🔖</span>
                      <el-input v-model="registerForm.companyCode" placeholder="请输入企业编码（用于企业知识隔离）" clearable></el-input>
                    </div>
                  </el-form-item>
                  <el-form-item>
                    <div class="input-wrapper">
                      <span class="input-icon">🔒</span>
                      <el-input v-model="registerForm.password" type="password" placeholder="请输入密码" show-password></el-input>
                    </div>
                  </el-form-item>
                  <el-form-item>
                    <div class="input-wrapper">
                      <span class="input-icon">✅</span>
                      <el-input v-model="registerForm.confirmPwd" type="password" placeholder="请确认密码" show-password></el-input>
                    </div>
                  </el-form-item>
                  <el-form-item>
                    <el-button type="primary" native-type="submit" class="login-btn">注 册</el-button>
                  </el-form-item>
                  <div class="login-footer">
                    <span class="other-login">已有账号？</span>
                    <a href="#" class="register-link" @click.prevent="activeAuthTab = 'login'">立即登录</a>
                  </div>
                </el-form>
              </div>
            </Transition>
          </div>

          <!-- 右侧品牌区 -->
          <div class="auth-right">
            <div class="brand-showcase">
              <div class="showcase-icon-wrap">
                <div class="showcase-icon">🤖</div>
                <div class="showcase-rings">
                  <div class="s-ring s-ring1"></div>
                  <div class="s-ring s-ring2"></div>
                </div>
              </div>
              <h3 class="showcase-title">AI 模拟面试官</h3>
              <p class="showcase-desc">智能模拟真实面试场景，全方位提升你的求职竞争力</p>
              <div class="feature-list">
                <div class="feature-item">
                  <span class="feature-dot"></span>
                  <span>文字 / 语音 / 视频三种面试模式</span>
                </div>
                <div class="feature-item">
                  <span class="feature-dot"></span>
                  <span>AI 实时分析评分与反馈</span>
                </div>
                <div class="feature-item">
                  <span class="feature-dot"></span>
                  <span>智能简历生成与优化</span>
                </div>
                <div class="feature-item">
                  <span class="feature-dot"></span>
                  <span>面试历史与成长轨迹追踪</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部信息 -->
    <Footer />
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import Footer from '@/components/Footer.vue'
import request from '@/utils/request' // 引入封装的axios
import { notifyError, notifySuccess } from '@/utils/appNotify'
const router = useRouter()

const activeAuthTab = ref('login')
const loginForm = reactive({ username: '', password: '' })
const registerForm = reactive({
  username: '',
  email: '',
  password: '',
  confirmPwd: '',
  accountType: 'personal',
  companyName: '',
  companyCode: ''
})

// 🌟 改造登录方法：使用 axios + 存储 Token
const handleLogin = async () => {
  if (!loginForm.username || !loginForm.password) {
    notifyError('请输入用户名和密码!', '登录')
    return
  }
  try {
    const res = await request.post('/user/login', loginForm)
    // 后端返回格式：{ code:200, data: { token: 'xxx', user_info: { username: 'xxx', ... } }, message: '成功' }
    const token = res.data?.token
    const username = res.data?.user_info?.username || loginForm.username
    const accountType = res.data?.user_info?.account_type || 'personal'
    
    if (!token) {
      throw new Error('登录失败，未获取到 Token')
    }

    localStorage.setItem('token', token)
    localStorage.setItem('ai-interview-user', username)
    localStorage.setItem('account_type', accountType)
    // 进入首页后触发「完善资料」一步引导（仅当未完成时由 MainLayout 展示）
    if (accountType !== 'enterprise') {
      sessionStorage.setItem('profile_onboard_pending', '1')
    }
    notifySuccess('登录成功!', '登录')
    router.push('/')
  } catch (err) {
    console.error('登录错误:', err)
    notifyError(err.message || '登录失败，请检查用户名和密码', '登录')
  }
}

// 🌟 可选：改造注册方法（同理替换fetch为axios）
const handleRegister = async () => {
  if (registerForm.password !== registerForm.confirmPwd) {
    notifyError('两次密码不一致！', '注册')
    return
  }
  if (!registerForm.username || !registerForm.email || !registerForm.password) {
    notifyError('请填写完整注册信息！', '注册')
    return
  }
  if (registerForm.accountType === 'enterprise' && !registerForm.companyName.trim()) {
    notifyError('企业账号请填写企业名称！', '注册')
    return
  }
  try {
    const res = await request.post('/user/register', {
      username: registerForm.username,
      email: registerForm.email,
      password: registerForm.password,
      account_type: registerForm.accountType,
      company_name: registerForm.companyName || '',
      company_code: registerForm.companyCode || ''
    })
    const accountType = res?.data?.user_info?.account_type || registerForm.accountType || 'personal'
    localStorage.setItem('account_type', accountType)
    notifySuccess('注册成功，请登录！', '注册')
    activeAuthTab.value = 'login'
    loginForm.username = registerForm.username
    loginForm.password = ''
  } catch (err) {
    console.error('注册错误:', err)
    notifyError('注册失败，用户名可能已存在', '注册')
  }
}
</script>

<style scoped>
/* ==================== 整体页面 ==================== */
.login-page {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-height: 100vh;
  background:
    radial-gradient(ellipse 100% 80% at 50% -30%, rgba(186, 230, 253, 0.75), transparent 60%),
    radial-gradient(ellipse 80% 60% at 10% 10%, rgba(224, 231, 255, 0.55), transparent 55%),
    linear-gradient(155deg, #eef6ff 0%, #dbeafe 30%, #c7d2fe 60%, #e0f2fe 100%);
  padding-bottom: 40px;
  position: relative;
  overflow: hidden;
}

/* ==================== 背景装饰 ==================== */
.bg-decoration {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
}

.bg-circle {
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.04);
}

.bg-circle-1 {
  width: 500px;
  height: 500px;
  top: -150px;
  right: -100px;
  background: radial-gradient(circle, rgba(255,255,255,0.08) 0%, transparent 70%);
  animation: float-slow 8s ease-in-out infinite;
}

.bg-circle-2 {
  width: 350px;
  height: 350px;
  bottom: -80px;
  left: -80px;
  background: radial-gradient(circle, rgba(100,160,255,0.12) 0%, transparent 70%);
  animation: float-slow 12s ease-in-out infinite reverse;
}

.bg-circle-3 {
  width: 200px;
  height: 200px;
  top: 40%;
  left: 20%;
  background: radial-gradient(circle, rgba(255,255,255,0.05) 0%, transparent 70%);
  animation: float-slow 10s ease-in-out infinite 2s;
}

.bg-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px);
  background-size: 50px 50px;
}

@keyframes float-slow {
  0%, 100% { transform: translateY(0) scale(1); }
  50% { transform: translateY(-20px) scale(1.05); }
}

/* ==================== 卡片包裹 ==================== */
.login-wrapper {
  margin-top: 60px;
  position: relative;
  z-index: 1;
}

.auth-card {
  width: 860px;
  max-width: calc(100vw - 32px);
  background: rgba(255, 255, 255, 0.94);
  border-radius: 22px;
  border: 1px solid rgba(255, 255, 255, 0.55);
  box-shadow:
    0 28px 72px rgba(15, 23, 42, 0.28),
    0 0 0 1px rgba(255, 255, 255, 0.4) inset,
    0 1px 0 rgba(255, 255, 255, 0.8) inset;
  overflow: hidden;
  backdrop-filter: blur(16px) saturate(1.2);
  animation: auth-card-enter 0.65s cubic-bezier(0.22, 1, 0.36, 1) both;
}

@keyframes auth-card-enter {
  from {
    opacity: 0;
    transform: translateY(16px) scale(0.985);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.auth-content {
  display: flex;
  min-height: 540px;
}

/* ==================== 左侧表单区 ==================== */
.auth-left {
  width: 50%;
  padding: 40px 36px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
}

.auth-logo-mini {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 28px;
}

.logo-icon {
  width: 30px;
  height: 30px;
  background: linear-gradient(135deg, #1a3a9e, #2055c7);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  box-shadow: 0 2px 8px rgba(32,85,199,0.35);
}

.logo-text {
  font-size: 14px;
  font-weight: 700;
  color: #1a3a9e;
  letter-spacing: 0.5px;
}

.login-title {
  font-size: 26px;
  font-weight: 700;
  color: #1a1a2e;
  margin: 0 0 6px 0;
}

.login-subtitle {
  font-size: 13px;
  color: #909399;
  margin: 0 0 24px 0;
  line-height: 1.5;
}

.login-form {
  flex: 1;
}

.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  width: 100%;
}

.input-icon {
  position: absolute;
  left: 14px;
  z-index: 1;
  font-size: 16px;
}

.login-form :deep(.el-form-item) {
  margin-bottom: 18px;
}

.login-form :deep(.el-input__wrapper) {
  border-radius: 12px;
  padding: 10px 14px 10px 44px;
  box-shadow: 0 0 0 1px #dde1e9 inset;
  transition: box-shadow 0.2s;
}

.login-form :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #93b8ff inset;
}

.login-form :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px rgba(32,85,199,0.25) inset, 0 0 0 1px #2055c7 inset !important;
}

.login-form :deep(.el-input__inner) {
  font-size: 14px;
}

.form-options {
  margin-bottom: 18px;
}

.form-options :deep(.el-form-item__content) {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.remember-me {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #666;
  font-size: 13px;
  cursor: pointer;
}

.remember-me input {
  accent-color: #2055c7;
  cursor: pointer;
}

.forgot-link {
  color: #2055c7;
  text-decoration: none;
  font-size: 13px;
  transition: color 0.2s;
}

.forgot-link:hover {
  color: #1a3a9e;
  text-decoration: underline;
}

.login-btn {
  width: 100%;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
  padding: 13px;
  letter-spacing: 2px;
  background: linear-gradient(135deg, #1a3a9e, #2055c7);
  border: none;
  box-shadow: 0 4px 16px rgba(32,85,199,0.35);
  transition: all 0.25s;
}

.login-btn:hover {
  background: linear-gradient(135deg, #0f2a7a, #1a3a9e);
  box-shadow: 0 6px 20px rgba(32,85,199,0.45);
  transform: translateY(-1px);
}

.login-footer {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin-top: 18px;
  font-size: 13px;
}

.other-login {
  color: #909399;
}

.register-link {
  color: #2055c7;
  text-decoration: none;
  font-weight: 600;
}

.register-link:hover {
  text-decoration: underline;
}

/* 表单切换动画 */
.form-switch-enter-active,
.form-switch-leave-active {
  transition: opacity 0.2s, transform 0.2s;
}

.form-switch-enter-from {
  opacity: 0;
  transform: translateX(12px);
}

.form-switch-leave-to {
  opacity: 0;
  transform: translateX(-12px);
}

/* ==================== 右侧品牌区 ==================== */
.auth-right {
  width: 50%;
  padding: 36px 32px;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(150deg, #1e3a5f 0%, #2563eb 40%, #3b82f6 72%, #60a5fa 100%);
  background-size: 140% 140%;
  animation: auth-right-shimmer 18s ease-in-out infinite alternate;
  position: relative;
  overflow: hidden;
}

@keyframes auth-right-shimmer {
  0% { background-position: 0% 40%; }
  100% { background-position: 100% 60%; }
}

.auth-right::before {
  content: '';
  position: absolute;
  top: -60px;
  right: -60px;
  width: 200px;
  height: 200px;
  border-radius: 50%;
  background: rgba(255,255,255,0.06);
}

.auth-right::after {
  content: '';
  position: absolute;
  bottom: -40px;
  left: -40px;
  width: 150px;
  height: 150px;
  border-radius: 50%;
  background: rgba(255,255,255,0.05);
}

.brand-showcase {
  text-align: center;
  color: #fff;
  position: relative;
  z-index: 1;
}

.showcase-icon-wrap {
  position: relative;
  display: inline-block;
  margin-bottom: 20px;
}

.showcase-icon {
  font-size: 64px;
  line-height: 1;
  filter: drop-shadow(0 4px 12px rgba(0,0,0,0.3));
  animation: float-icon 3s ease-in-out infinite;
}

@keyframes float-icon {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); }
}

.showcase-rings {
  position: absolute;
  inset: -20px;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}

.s-ring {
  position: absolute;
  border-radius: 50%;
  border: 1.5px solid rgba(255,255,255,0.2);
  animation: ring-expand 3s ease-out infinite;
}

.s-ring1 {
  width: 100px;
  height: 100px;
  animation-delay: 0s;
}

.s-ring2 {
  width: 140px;
  height: 140px;
  animation-delay: 1s;
}

@keyframes ring-expand {
  0%   { transform: scale(0.9); opacity: 0.5; }
  100% { transform: scale(1.3); opacity: 0; }
}

.showcase-title {
  font-size: 22px;
  font-weight: 700;
  margin: 0 0 10px;
  letter-spacing: 0.5px;
}

.showcase-desc {
  font-size: 13px;
  opacity: 0.75;
  line-height: 1.6;
  margin: 0 0 24px;
}

.feature-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  text-align: left;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  opacity: 0.88;
}

.feature-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba(255,255,255,0.7);
  flex-shrink: 0;
}
</style>
