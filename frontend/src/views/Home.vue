<template>
  <div class="home-page">
    <div class="page-container">
      <!-- 顶部英雄区 -->
      <header class="home-hero surface-card">
        <div class="home-hero__copy">
          <p class="home-hero__eyebrow">AI 模拟面试 · 能力提升</p>
          <h1 class="home-hero__title">更专业的练习场，更清晰的成长路径</h1>
          <p class="home-hero__desc">
            在统一蓝色工作台中完成模拟面试、简历与知识沉淀；本地记录与工具入口并排呈现，结构清晰、留白舒适。
          </p>
          <div class="home-hero__actions">
            <button type="button" class="home-hero__btn home-hero__btn--primary" @click="goToInterview('start')">
              开始模拟面试
            </button>
            <button type="button" class="home-hero__btn home-hero__btn--ghost" @click="goToInterview('resume')">
              简历优化
            </button>
          </div>
        </div>
        <div class="home-hero__visual" aria-hidden="true">
          <div class="home-hero__orb" />
          <div class="home-hero__stats">
            <div class="home-stat">
              <span class="home-stat__val">多模式</span>
              <span class="home-stat__lab">文字 · 语音 · 视频</span>
            </div>
            <div class="home-stat">
              <span class="home-stat__val">全流程</span>
              <span class="home-stat__lab">报告 · 成长 · 题库</span>
            </div>
          </div>
        </div>
      </header>

      <div class="home-grid">
        <!-- 主栏：动态 + 发布 -->
        <div class="home-main">
          <section class="home-carousel surface-card">
            <img
              src="https://images.unsplash.com/photo-1497366216548-37526070297c?w=800&h=400&fit=crop"
              alt="工作台氛围"
              class="home-carousel__img"
            />
            <div class="home-carousel__cap">
              <span>今日专注</span>
              <strong>结构化表达与岗位匹配</strong>
            </div>
          </section>

          <section class="home-feed surface-card" v-loading="loadingPosts">
            <div class="home-section-head">
              <h2 class="home-section-title">本地动态</h2>
              <span class="home-section-sub">仅保存在当前浏览器</span>
            </div>
            <div v-for="post in postList" :key="post.id" class="home-post">
              <div class="home-post__head">
                <div class="home-post__avatar">{{ post.user_name[0] }}</div>
                <div class="home-post__meta">
                  <div class="home-post__author">{{ post.user_name }}</div>
                  <div class="home-post__time">{{ post.created_at }}</div>
                </div>
              </div>
              <div class="home-post__body">{{ post.content }}</div>
              <div v-if="post.images && post.images.length > 0" class="home-post__imgs">
                <img v-for="(img, idx) in post.images" :key="idx" :src="img" class="home-post__img" alt="" />
              </div>
              <div class="home-post__actions">
                <button type="button" class="home-post__action" @click="likePost(post)">
                  {{ post.is_liked ? '❤️' : '♡' }} {{ post.like_count }}
                </button>
              </div>
            </div>
            <div v-if="postList.length === 0 && !loadingPosts" class="home-empty">暂无本地动态，可在下方记录练习心得。</div>
          </section>

          <section class="home-compose surface-card">
            <div class="home-compose__tabs">
              <button type="button" class="home-tab home-tab--active">写记录</button>
            </div>
            <textarea v-model="postContent" class="home-compose__input" placeholder="记录此刻的练习心得" />
            <div class="home-compose__toolbar">
              <div class="home-compose__tools">
                <span title="图片" aria-hidden="true" @click="triggerImageUpload">&#128247;</span>
                <input ref="imageInput" type="file" accept="image/*" multiple style="display: none" @change="handleImageSelect" />
              </div>
              <button type="button" class="home-publish" @click="handlePublish" :disabled="publishing">保存</button>
            </div>
            <div v-if="selectedImages.length > 0" class="home-previews">
              <div v-for="(img, index) in selectedImages" :key="index" class="home-preview-item">
                <img :src="img.preview" :alt="img.name" />
                <button type="button" class="home-preview-remove" @click="removeImage(index)">×</button>
              </div>
            </div>
          </section>
        </div>

        <!-- 侧栏：工具 -->
        <aside class="home-aside">
          <section class="home-tools surface-card">
            <h2 class="home-aside-title">工具箱</h2>
            <div class="home-tools__grid">
              <button type="button" class="home-tool" @click="goToPositionQuery">
                <span class="home-tool__icon" aria-hidden="true">&#128269;</span>
                <span class="home-tool__label">岗位查找</span>
              </button>
              <button type="button" class="home-tool" @click="showHelp = true">
                <span class="home-tool__icon" aria-hidden="true">&#10067;</span>
                <span class="home-tool__label">帮助文档</span>
              </button>
            </div>
            <div class="home-job-search">
              <label class="home-job-search__label">岗位查询（数据库）</label>
              <select v-model="selectedJob" class="home-job-search__select">
                <option value="">请选择已入库岗位</option>
                <option
                  v-for="j in jobOptions"
                  :key="j.job_id ? `id-${j.job_id}` : j.job_name"
                  :value="j.job_name"
                >
                  {{ j.job_name }}
                </option>
              </select>
              <button type="button" class="home-job-search__btn" @click="startInterviewWithSelectedJob">
                用该岗位开始面试
              </button>
            </div>
          </section>
        </aside>
      </div>
    </div>

    <!-- 帮助文档弹窗 -->
    <div v-if="showHelp" class="help-modal" @click="showHelp = false">
      <div class="help-content surface-card" @click.stop>
        <div class="help-header">
          <h2>AI 模拟面试官帮助文档</h2>
          <button type="button" class="help-close" @click="showHelp = false">×</button>
        </div>
        <div class="help-body">
          <p class="help-intro">
            帮助文档核心围绕<b>用户怎么用</b>、<b>功能是什么</b>、<b>问题怎么解</b>展开，适配 AI 模拟面试官的使用场景，结构清晰、步骤明确，兼顾新手快速上手和进阶使用。
          </p>

          <section class="help-section">
            <h3>1. 文档说明（前言）</h3>
            <ul>
              <li><b>文档适用人群</b>：求职者、学生、职场备考者等</li>
              <li><b>文档更新版本 / 时间</b>：v1.0 - 2026 年 3 月</li>
              <li><b>核心用途</b>：快速掌握 AI 模拟面试官的功能使用、解决操作问题</li>
            </ul>
          </section>

          <section class="help-section">
            <h3>2. 功能简介</h3>
            <ul>
              <li><b>核心能力</b>：模拟行业 / 岗位面试、实时语音 / 文字问答、面试评价 / 反馈、错题复盘、简历匹配提问等</li>
              <li><b>特色功能</b>：岗位定制面试、压力型面试官、历史面试记录保存等</li>
            </ul>
          </section>

          <section class="help-section">
            <h3>3. 快速上手（核心步骤，新手必看）</h3>
            <p>分步骤写清从打开到完成一次面试的全流程：</p>
            <ol>
              <li>注册并登录个人账号</li>
              <li>选择目标行业 / 岗位（如互联网 - 产品经理、金融 - 风控）</li>
              <li>选择面试阶段、场景、难度和面试官风格</li>
              <li>开始面试，按提示完成文字、语音或视频作答</li>
              <li>面试结束，查看 AI 评价、问题解析、改进建议</li>
            </ol>
          </section>

          <section class="help-section">
            <h3>4. 功能详解</h3>
            <ul>
              <li><b>AI 模拟面试</b>：选择岗位后，AI 将扮演面试官进行全流程模拟面试</li>
              <li><b>智能简历优化</b>：上传简历，获取 AI 优化建议和匹配度分析</li>
              <li><b>面试题库</b>：按行业、岗位分类的面试题目集合</li>
              <li><b>成长轨迹</b>：记录面试历史，追踪能力提升轨迹</li>
            </ul>
          </section>

          <section class="help-section">
            <h3>5. 常见问题</h3>
            <ul>
              <li><b>Q: 如何开始第一次面试？</b><br/>A: 点击首页"AI 模拟面试"→选择岗位、面试场景和难度→开始面试</li>
              <li><b>Q: 如何查看历史面试记录？</b><br/>A: 在侧栏进入「面试历史」或「成长轨迹」可查看完整记录与 AI 评价</li>
              <li><b>Q: 支持语音面试吗？</b><br/>A: 支持，需授权麦克风权限，并确保服务端已配置 Whisper 和 FFmpeg</li>
            </ul>
          </section>

          <section class="help-section">
            <h3>6. 使用技巧</h3>
            <ul>
              <li>面试前建议先了解目标岗位的常见面试题型</li>
              <li>回答时尽量完整、清晰，AI 会根据回答质量给出更精准的评价</li>
              <li>面试结束后的评价报告包含详细的能力维度分析，建议仔细查看</li>
              <li>多次面试同一岗位可以明显看到能力提升轨迹</li>
            </ul>
          </section>

          <section class="help-section">
            <h3>7. 注意事项</h3>
            <ul>
              <li>使用语音面试时，请确保环境安静，麦克风正常工作</li>
              <li>面试过程中建议不要切换浏览器标签页，可能影响面试体验</li>
              <li>面试评价仅供参考，实际面试表现还需结合真实面试场景</li>
            </ul>
          </section>

          <section class="help-section">
            <h3>8. 联系支持</h3>
            <p>使用问题可在项目仓库查看说明或提交 Issue。</p>
          </section>

          <section class="help-section">
            <h3>9. 视频面试与表情分析</h3>
            <ul>
              <li>需在浏览器中授权摄像头与麦克风；录制格式一般为 WebM，后端会抽帧做非语言分析。</li>
              <li>视频画面分析使用 DeepSeek 的 <b>deepseek-flash</b>（支持看图）。请在后端 <code>.env</code> 配置 <code>DEEPSEEK_API_KEY</code>。知识库向量不走 DeepSeek，使用本地 bge 模型。</li>
              <li>界面上的「实时情感」为录制过程中的前端示意；每轮提交后的详细分析以后端返回为准。</li>
            </ul>
          </section>

          <section class="help-section">
            <h3>10. 成长轨迹与能力提升建议</h3>
            <ul>
              <li>在「成长轨迹」页可查看分数曲线；点击「生成提升建议」将基于历史面试报告生成练习计划、学习路线与<b>推荐学习链接</b>。</li>
              <li>系统会根据你的薄弱维度补充公开技术文档与社区链接，并展示简要的<b>能力知识图谱</b>便于对照复习路径。</li>
            </ul>
          </section>

          <section class="help-section">
            <h3>11. 讯飞虚拟人面试官（可选）</h3>
            <ul>
              <li>管理员可在后端 <code>.env</code> 中配置 <code>IFLYTEK_APP_ID</code>、<code>IFLYTEK_API_KEY</code>、<code>IFLYTEK_API_SECRET</code>、<code>IFLYTEK_VH_AVATAR_ID</code> 等参数，详见模板文件说明。</li>
              <li>视频面试启动时会尝试加载讯飞虚拟人直播流；前端使用 flv.js 直连 HTTP-FLV 地址并自动播放（静音）。若你填的是 RTMP 地址，前端会按同路径自动推断为 HTTP-FLV 地址。</li>
            </ul>
          </section>

          <section class="help-section">
            <h3>12. 隐私与免责声明</h3>
            <p>面试录音、录像仅用于本次模拟评估；AI 评价与学习建议仅供参考，不代表任何录用承诺。</p>
          </section>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { useRouter } from 'vue-router'
import { ref, onMounted } from 'vue'
import { getInterviewPositions } from '@/api/endpoints'
import { notifyError, notifySuccess, notifyWarning } from '@/utils/appNotify'

export default {
  name: 'HomePage',
  setup() {
    const router = useRouter()
    const showHelp = ref(false)

    const postContent = ref('')
    const publishing = ref(false)
    const selectedImages = ref([])
    const imageInput = ref(null)

    const postList = ref([])
    const loadingPosts = ref(false)
    const jobOptions = ref([])
    const selectedJob = ref('')

    const goToInterview = (path) => {
      router.push(`/interview/${path}`)
    }

    const goToPositionQuery = () => {
      router.push({ path: '/interview/knowledge', query: { tab: 'position' } })
    }

    const triggerImageUpload = () => {
      imageInput.value?.click()
    }

    const handleImageSelect = (event) => {
      const files = event.target.files
      if (!files || files.length === 0) return

      Array.from(files).forEach((file) => {
        const reader = new FileReader()
        reader.onload = (e) => {
          selectedImages.value.push({
            file: file,
            name: file.name,
            preview: e.target?.result,
          })
        }
        reader.readAsDataURL(file)
      })

      event.target.value = ''
    }

    const removeImage = (index) => {
      selectedImages.value.splice(index, 1)
    }

    const handlePublish = async () => {
      if (!postContent.value.trim() && selectedImages.value.length === 0) {
        notifyWarning('请输入内容或选择图片', '本地动态')
        return
      }

      publishing.value = true
      try {
        const currentUser = localStorage.getItem('ai-interview-user') || '匿名用户'
        const now = new Date()
        const timeStr = `${now.getMonth() + 1}月${now.getDate()}日 ${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`

        const newPost = {
          id: Date.now(),
          user_name: currentUser,
          content: postContent.value,
          images: selectedImages.value.map((img) => img.preview),
          created_at: timeStr,
          like_count: 0,
          is_liked: false,
        }

        postList.value.unshift(newPost)
        localStorage.setItem('community-posts', JSON.stringify(postList.value))

        notifySuccess('保存成功！', '本地动态')
        postContent.value = ''
        selectedImages.value = []
        if (imageInput.value) {
          imageInput.value.value = ''
        }
      } catch (error) {
        console.error('保存失败:', error)
        notifyError('保存失败，请重试', '本地动态')
      } finally {
        publishing.value = false
      }
    }

    const likePost = (post) => {
      if (post.is_liked) {
        post.like_count--
        post.is_liked = false
      } else {
        post.like_count++
        post.is_liked = true
      }

      localStorage.setItem('community-posts', JSON.stringify(postList.value))
    }

    const fetchPosts = async () => {
      loadingPosts.value = true
      try {
        const postsStr = localStorage.getItem('community-posts')
        if (postsStr) {
          const posts = JSON.parse(postsStr)
          postList.value = Array.isArray(posts) ? posts : []
        }
      } catch (error) {
        console.error('获取动态失败:', error)
        notifyError('加载动态失败', '本地动态')
      } finally {
        loadingPosts.value = false
      }
    }

    const fetchJobOptions = async () => {
      try {
        const data = await getInterviewPositions()
        const raw = Array.isArray(data?.positions) ? data.positions : []
        jobOptions.value = raw
          .map((p) => {
            if (p != null && typeof p === 'object') {
              const job_name = String(p.job_name || '').trim()
              const job_id = Number(p.job_id || 0)
              return job_name ? { job_id, job_name } : null
            }
            const s = String(p || '').trim()
            return s ? { job_id: 0, job_name: s } : null
          })
          .filter(Boolean)
        if (!selectedJob.value && jobOptions.value.length > 0) {
          selectedJob.value = jobOptions.value[0].job_name
        }
      } catch (error) {
        console.error('获取岗位列表失败:', error)
      }
    }

    const startInterviewWithSelectedJob = () => {
      const job = (selectedJob.value || '').trim()
      if (!job) {
        notifyWarning('请先选择岗位', '岗位查询')
        return
      }
      const row = jobOptions.value.find((x) => x.job_name === job)
      if (row && row.job_id > 0) {
        localStorage.setItem('active_job_id', String(row.job_id))
      }
      const existing = JSON.parse(localStorage.getItem('interview-config') || '{}')
      localStorage.setItem(
        'interview-config',
        JSON.stringify({
          ...existing,
          job,
          mode: existing.mode || 'text',
          difficulty: existing.difficulty || 'entry',
          language: existing.language || 'zh',
        }),
      )
      router.push('/interview/start')
    }

    onMounted(() => {
      fetchPosts()
      fetchJobOptions()
    })

    return {
      goToInterview,
      goToPositionQuery,
      postContent,
      publishing,
      selectedImages,
      imageInput,
      triggerImageUpload,
      handleImageSelect,
      removeImage,
      handlePublish,
      postList,
      loadingPosts,
      likePost,
      showHelp,
      jobOptions,
      selectedJob,
      startInterviewWithSelectedJob,
    }
  },
}
</script>

<style scoped>
.home-page {
  min-height: calc(100vh - 48px);
}

.home-hero {
  display: grid;
  grid-template-columns: 1.15fr 0.85fr;
  gap: clamp(20px, 4vw, 40px);
  padding: clamp(32px, 4.5vw, 48px);
  margin-bottom: var(--section-gap, 24px);
  align-items: center;
  overflow: hidden;
  position: relative;
  transition: transform 0.35s ease, box-shadow 0.35s ease;
  border-radius: var(--radius-lg);
  background: linear-gradient(135deg, #ffffff 0%, #f8fafc 42%, #f1f5f9 100%);
  border: 1px solid rgba(148, 163, 184, 0.2);
  box-shadow: var(--shadow-md);
}

.home-hero:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
}

.home-hero__eyebrow {
  margin: 0 0 12px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--color-primary);
}

.home-hero__title {
  margin: 0 0 16px;
  font-size: clamp(28px, 3vw, 36px);
  font-weight: 800;
  color: var(--color-text-primary);
  letter-spacing: -0.02em;
  line-height: 1.2;
}

.home-hero__desc {
  margin: 0 0 28px;
  font-size: 16px;
  line-height: 1.65;
  color: var(--color-text-secondary);
  max-width: 520px;
}

.home-hero__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.home-hero__btn {
  border: none;
  cursor: pointer;
  font-size: 15px;
  font-weight: 600;
  padding: 14px 28px;
  border-radius: 999px;
  transition: transform 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
}

.home-hero__btn--primary {
  color: #fff;
  background: var(--gradient-primary);
  box-shadow: 0 8px 24px rgba(37, 99, 235, 0.28);
}

.home-hero__btn--primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 28px rgba(37, 99, 235, 0.35);
}

.home-hero__btn--ghost {
  background: var(--color-primary-pale);
  color: var(--color-primary-dark);
  border: 1px solid rgba(37, 99, 235, 0.22);
}

.home-hero__btn--ghost:hover {
  background: #dbeafe;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.15);
}

.home-hero__visual {
  position: relative;
  min-height: 180px;
  display: flex;
  align-items: flex-end;
  justify-content: flex-end;
}

.home-hero__orb {
  position: absolute;
  inset: -30% -20% auto auto;
  width: min(320px, 90%);
  aspect-ratio: 1;
  border-radius: 50%;
  background: radial-gradient(circle at 30% 30%, rgba(147, 197, 253, 0.9), rgba(37, 99, 235, 0.35) 45%, transparent 70%);
  filter: blur(0px);
  opacity: 0.95;
  animation: orb-float 10s ease-in-out infinite;
}

@keyframes orb-float {
  0%,
  100% {
    transform: translate(0, 0) scale(1);
  }
  50% {
    transform: translate(-8px, 6px) scale(1.04);
  }
}

.home-hero__stats {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
  max-width: 260px;
}

.home-stat {
  padding: 14px 16px;
  border-radius: var(--radius-md);
  background: linear-gradient(135deg, rgba(239, 246, 255, 0.95), #fff);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-sm);
}

.home-stat__val {
  display: block;
  font-size: 15px;
  font-weight: 800;
  color: var(--color-primary-dark);
}

.home-stat__lab {
  font-size: 12px;
  color: var(--color-text-muted);
}

.home-grid {
  display: grid;
  grid-template-columns: 1fr min(300px, 32%);
  gap: var(--section-gap, 24px);
  align-items: start;
}

.home-main {
  display: flex;
  flex-direction: column;
  gap: var(--section-gap, 24px);
  min-width: 0;
}

.home-carousel {
  padding: 0;
  overflow: hidden;
  position: relative;
}

.home-carousel__img {
  width: 100%;
  height: clamp(200px, 28vw, 320px);
  object-fit: cover;
  display: block;
  transition: transform 0.6s ease;
}

.home-carousel:hover .home-carousel__img {
  transform: scale(1.02);
}

.home-carousel__cap {
  position: absolute;
  left: 16px;
  bottom: 16px;
  right: 16px;
  padding: 12px 16px;
  border-radius: var(--radius-md);
  background: rgba(15, 23, 42, 0.72);
  color: #fff;
  backdrop-filter: blur(8px);
  font-size: 13px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.home-carousel__cap span {
  opacity: 0.85;
  font-size: 11px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.home-feed,
.home-compose,
.home-tools {
  padding: clamp(18px, 2.2vw, 24px);
}

.home-section-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 18px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--color-border);
}

.home-section-title {
  margin: 0;
  font-size: 17px;
  font-weight: 700;
  color: var(--color-text-primary);
}

.home-section-sub {
  font-size: 12px;
  color: var(--color-text-muted);
}

.home-post {
  padding: 18px 0;
  border-bottom: 1px solid var(--color-border);
}

.home-post:last-of-type {
  border-bottom: none;
}

.home-post__head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.home-post__avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: linear-gradient(145deg, var(--color-primary-light), var(--color-primary-dark));
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: 700;
}

.home-post__author {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.home-post__time {
  font-size: 12px;
  color: var(--color-text-muted);
}

.home-post__body {
  font-size: 14px;
  line-height: 1.65;
  color: var(--color-text-secondary);
}

.home-post__imgs {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 10px;
}

.home-post__img {
  width: 96px;
  height: 96px;
  object-fit: cover;
  border-radius: var(--radius-sm);
  transition: transform 0.25s ease;
}

.home-post__img:hover {
  transform: scale(1.04);
}

.home-post__actions {
  display: flex;
  gap: 16px;
  margin-top: 12px;
}

.home-post__action {
  border: none;
  background: none;
  font-size: 13px;
  color: var(--color-text-secondary);
  cursor: pointer;
  padding: 0;
  transition: color 0.2s ease;
}

.home-post__action:hover {
  color: var(--color-primary);
}

.home-empty {
  text-align: center;
  color: var(--color-text-muted);
  padding: 36px 16px;
  font-size: 14px;
}

.home-compose__tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 14px;
}

.home-tab {
  border: none;
  padding: 8px 16px;
  border-radius: 999px;
  font-size: 13px;
  cursor: pointer;
  background: #f1f5f9;
  color: var(--color-text-secondary);
  transition: background 0.2s ease, color 0.2s ease;
}

.home-tab:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.home-tab--active {
  background: linear-gradient(135deg, var(--color-primary-light), var(--color-primary));
  color: #fff;
}

.home-compose__input {
  width: 100%;
  min-height: 100px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 12px 14px;
  font-size: 14px;
  font-family: inherit;
  resize: vertical;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.home-compose__input:focus {
  outline: none;
  border-color: rgba(37, 99, 235, 0.45);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}

.home-compose__toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 14px;
}

.home-compose__tools {
  display: flex;
  gap: 14px;
}

.home-compose__tools span {
  font-size: 20px;
  cursor: pointer;
  opacity: 0.72;
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.home-compose__tools span:hover {
  opacity: 1;
  transform: scale(1.06);
}

.home-publish {
  border: none;
  background: linear-gradient(135deg, var(--color-primary-light), var(--color-primary));
  color: #fff;
  padding: 10px 28px;
  border-radius: 999px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.home-publish:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(37, 99, 235, 0.3);
}

.home-publish:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.home-previews {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 14px;
}

.home-preview-item {
  position: relative;
  width: 88px;
  height: 88px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  border: 1px solid var(--color-border);
}

.home-preview-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.home-preview-remove {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  border: none;
  background: rgba(15, 23, 42, 0.65);
  color: #fff;
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
}

.home-aside {
  display: flex;
  flex-direction: column;
  gap: var(--section-gap, 24px);
  position: sticky;
  top: 16px;
}

.home-aside-title {
  margin: 0 0 14px;
  font-size: 16px;
  font-weight: 700;
  color: var(--color-primary-dark);
}

.home-tools__grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.home-job-search {
  margin-top: 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.home-job-search__label {
  font-size: 12px;
  color: var(--color-text-muted);
}

.home-job-search__select {
  width: 100%;
  border: 1px solid var(--color-border);
  border-radius: 10px;
  padding: 8px 10px;
  font-size: 13px;
  background: #fff;
}

.home-job-search__btn {
  border: none;
  border-radius: 999px;
  background: linear-gradient(135deg, var(--color-primary-light), var(--color-primary));
  color: #fff;
  font-size: 12px;
  padding: 8px 12px;
  cursor: pointer;
}

.home-tool {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 18px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: linear-gradient(180deg, #fff 0%, var(--color-primary-pale) 160%);
  cursor: pointer;
  transition: transform 0.22s ease, border-color 0.22s ease, box-shadow 0.22s ease;
}

.home-tool:hover {
  transform: translateY(-3px);
  border-color: rgba(37, 99, 235, 0.35);
  box-shadow: var(--shadow-md);
}

.home-tool__icon {
  font-size: 28px;
}

.home-tool__label {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-secondary);
}

/* 帮助弹窗 */
.help-modal {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.55);
  backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: 20px;
  animation: help-fade-in 0.28s ease;
}

.help-content {
  max-width: 900px;
  max-height: 86vh;
  width: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  animation: help-slide-in 0.32s ease;
}

.help-header {
  padding: 20px 24px;
  border-bottom: 1px solid var(--color-border);
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
  background: linear-gradient(90deg, var(--color-primary-pale), #fff);
}

.help-header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: var(--color-primary-dark);
}

.help-close {
  border: none;
  background: rgba(15, 23, 42, 0.06);
  width: 40px;
  height: 40px;
  border-radius: 50%;
  font-size: 24px;
  line-height: 1;
  cursor: pointer;
  color: var(--color-text-muted);
  transition: background 0.2s ease, color 0.2s ease;
}

.help-close:hover {
  background: rgba(239, 68, 68, 0.12);
  color: #b91c1c;
}

.help-body {
  padding: 24px 28px 32px;
  overflow-y: auto;
}

.help-intro {
  font-size: 14px;
  color: var(--color-text-secondary);
  line-height: 1.75;
  margin: 0 0 24px;
  padding: 14px 16px;
  background: var(--color-primary-pale);
  border-left: 4px solid var(--color-primary);
  border-radius: var(--radius-sm);
}

.help-section {
  margin-bottom: 26px;
}

.help-section h3 {
  font-size: 16px;
  margin: 0 0 12px;
  font-weight: 700;
  color: var(--color-text-primary);
  border-left: 4px solid var(--color-primary);
  padding-left: 12px;
}

.help-section ul,
.help-section ol {
  margin: 8px 0;
  padding-left: 22px;
}

.help-section li {
  font-size: 14px;
  color: var(--color-text-secondary);
  line-height: 1.75;
  margin-bottom: 8px;
}

.help-section b {
  color: var(--color-primary-dark);
}

.help-section p {
  font-size: 14px;
  color: var(--color-text-secondary);
  line-height: 1.65;
}

@keyframes help-fade-in {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@keyframes help-slide-in {
  from {
    opacity: 0;
    transform: translateY(16px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@media (max-width: 1024px) {
  .home-hero {
    grid-template-columns: 1fr;
  }
  .home-hero__visual {
    min-height: 140px;
  }
  .home-grid {
    grid-template-columns: 1fr;
  }
  .home-aside {
    position: static;
    gap: 16px;
  }
}

@media (max-width: 640px) {
  .home-tools__grid {
    grid-template-columns: 1fr;
  }
}
</style>
