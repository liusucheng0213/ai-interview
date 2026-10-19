 <template>
  <div class="resume-module page-container">
    <div class="function-detail-layout">
      <div class="function-sidebar surface-card">
        <div class="sidebar-header sidebar-header--compact">
          <span class="sidebar-title">简历工作台</span>
          <span class="sidebar-sub">生成 · 上传 · 优化</span>
        </div>
        <div class="function-list">
          <div
            class="function-nav-item"
            :class="{ active: selectedFunction === 'generate' }"
            @click="selectFunction('generate')"
          >
            <div class="nav-icon">✨</div>
            <span class="nav-text">AI 生成简历</span>
          </div>
          <div
            class="function-nav-item"
            :class="{ active: selectedFunction === 'upload' }"
            @click="selectFunction('upload')"
          >
            <div class="nav-icon">📤</div>
            <span class="nav-text">上传简历</span>
          </div>
          <div
            class="function-nav-item"
            :class="{ active: selectedFunction === 'optimize' }"
            @click="selectFunction('optimize')"
          >
            <div class="nav-icon">🤖</div>
            <span class="nav-text">AI 优化简历</span>
          </div>
        </div>
      </div>

      <div class="function-content surface-card">
        <!-- 上传简历区域 -->
        <div class="upload-section" v-if="selectedFunction === 'upload'">
          <h3 class="section-title">📄 上传简历</h3>
          <div class="upload-area" @dragover.prevent @drop.prevent="handleDrop">
            <input 
              type="file" 
              ref="fileInput" 
              accept=".pdf,.doc,.docx,.txt" 
              @change="handleFileSelect"
              style="display: none"
            />
            <div class="upload-content" v-if="!selectedFile">
              <div class="upload-icon">📤</div>
              <p class="upload-text">点击或拖拽上传简历</p>
              <p class="upload-hint">支持 PDF、Word、TXT 格式</p>
            </div>
            <div class="file-info" v-else>
              <div class="file-icon">📎</div>
              <div class="file-detail">
                <div class="file-name">{{ selectedFile.name }}</div>
                <div class="file-size">{{ formatFileSize(selectedFile.size) }}</div>
              </div>
              <button class="remove-btn" @click="removeFile">×</button>
            </div>
            <button class="upload-btn" @click="triggerUpload" v-if="!selectedFile">
              选择文件
            </button>
          </div>
          
          <!-- 智能扫描按钮 -->
          <div class="scan-section" v-if="selectedFile && !scanning && !resumeData">
            <button class="scan-btn" @click="startScanning" :disabled="!selectedFile">
              🤖 开始智能扫描
            </button>
          </div>
          
          <!-- 扫描中状态 -->
          <div class="scanning-section" v-if="scanning">
            <div class="scanning-animation">
              <div class="scanner-line"></div>
              <div class="scan-icon">🔍</div>
              <p class="scan-text">正在分析简历内容...</p>
              <p class="scan-subtext">AI 正在提取关键信息</p>
            </div>
          </div>
          
          <!-- 扫描完成：只显示电子版简历卡片，不显示 AI 评分 -->
          <div class="scanned-resume-result" v-if="resumeData && !scanning">
            <h3 class="section-title">📋 电子版简历</h3>
            <div class="resume-card resume-card--premium">
              <div class="card-header">
                <div class="avatar-placeholder">{{ getInitials(resumeData.basic_info.name) }}</div>
                <div class="basic-info">
                  <h2 class="name">{{ resumeData.basic_info.name }}</h2>
                  <p class="contact">
                    <span v-if="resumeData.basic_info.email">📧 {{ resumeData.basic_info.email }}</span>
                    <span v-if="resumeData.basic_info.phone">📱 {{ resumeData.basic_info.phone }}</span>
                  </p>
                </div>
              </div>

              <div class="card-content">
                <!-- 教育背景 -->
                <div class="card-section" v-if="resumeData.education && resumeData.education.length > 0">
                  <h4 class="card-section-title">🎓 教育背景</h4>
                  <div class="education-item" v-for="(edu, idx) in resumeData.education" :key="idx">
                    <div class="school">{{ edu.school }}</div>
                    <div class="degree">{{ edu.degree }} - {{ edu.major }}</div>
                    <div class="time">{{ edu.start_date }} - {{ edu.end_date || '至今' }}</div>
                  </div>
                </div>

                <!-- 工作经历 -->
                <div class="card-section" v-if="resumeData.experience && resumeData.experience.length > 0">
                  <h4 class="card-section-title">💼 工作经历</h4>
                  <div class="experience-item" v-for="(exp, idx) in resumeData.experience" :key="idx">
                    <div class="company">{{ exp.company }}</div>
                    <div class="position">{{ exp.position }}</div>
                    <div class="time">{{ exp.start_date }} - {{ exp.end_date || '至今' }}</div>
                    <ul class="achievements">
                      <li v-for="(achievement, i) in exp.achievements" :key="i">{{ achievement }}</li>
                    </ul>
                  </div>
                </div>

                <!-- 项目经验 -->
                <div class="card-section" v-if="resumeData.projects && resumeData.projects.length > 0">
                  <h4 class="card-section-title">🚀 项目经验</h4>
                  <div class="project-item" v-for="(proj, idx) in resumeData.projects" :key="idx">
                    <div class="project-name">{{ proj.name }}</div>
                    <div class="project-role">{{ proj.role }}</div>
                    <div class="project-desc">{{ proj.description }}</div>
                  </div>
                </div>

                <!-- 技能清单 -->
                <div class="card-section" v-if="resumeData.skills && resumeData.skills.length > 0">
                  <h4 class="card-section-title">🛠️ 技能清单</h4>
                  <div class="skills-container">
                    <span class="skill-tag" v-for="(skill, idx) in resumeData.skills" :key="idx">
                      {{ skill }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
</div>
        </div>

        <!-- AI 生成简历表单 -->
        <div class="generate-section" v-if="selectedFunction === 'generate'">
          <h3 class="section-title">✨ AI 生成简历</h3>
          <p class="form-hint">请填写基本信息，AI 将自动生成完整简历</p>
          
          <div class="generate-form">
            <!-- 基本信息 -->
            <div class="form-group">
              <h4 class="form-group-title">📝 基本信息</h4>
              <div class="form-row">
                <div class="form-item">
                  <label>姓名</label>
                  <el-input v-model="generateForm.name" placeholder="请输入姓名"></el-input>
                </div>
                <div class="form-item">
                  <label>性别</label>
                  <el-select v-model="generateForm.gender" placeholder="请选择性别" style="width: 100%">
                    <el-option label="男" value="male"></el-option>
                    <el-option label="女" value="female"></el-option>
                  </el-select>
                </div>
              </div>
              <div class="form-row">
                <div class="form-item">
                  <label>邮箱</label>
                  <el-input v-model="generateForm.email" placeholder="请输入邮箱"></el-input>
                </div>
                <div class="form-item">
                  <label>电话</label>
                  <el-input v-model="generateForm.phone" placeholder="请输入手机号码"></el-input>
                </div>
              </div>
              <div class="form-row">
                <div class="form-item">
                  <label>求职意向</label>
                  <el-input v-model="generateForm.job_target" placeholder="例如：前端开发工程师"></el-input>
                </div>
                <div class="form-item">
                  <label>工作年限</label>
                  <el-select v-model="generateForm.experience_years" placeholder="请选择" style="width: 100%">
                    <el-option label="应届生" value="fresh"></el-option>
                    <el-option label="1-3 年" value="1-3"></el-option>
                    <el-option label="3-5 年" value="3-5"></el-option>
                    <el-option label="5-10 年" value="5-10"></el-option>
                    <el-option label="10 年以上" value="10+"></el-option>
                  </el-select>
                </div>
              </div>
            </div>

            <!-- 教育背景 -->
            <div class="form-group">
              <div class="form-group-header">
                <h4 class="form-group-title">🎓 教育背景</h4>
                <el-button type="primary" size="small" @click="addEducation">+ 添加教育经历</el-button>
              </div>
              <div class="education-item" v-for="(edu, index) in generateForm.education" :key="index">
                <div class="form-row">
                  <div class="form-item">
                    <label>学校</label>
                    <el-input v-model="edu.school" placeholder="请输入学校名称"></el-input>
                  </div>
                  <div class="form-item">
                    <label>专业</label>
                    <el-input v-model="edu.major" placeholder="请输入专业"></el-input>
                  </div>
                </div>
                <div class="form-row">
                  <div class="form-item">
                    <label>学历</label>
                    <el-select v-model="edu.degree" placeholder="请选择" style="width: 100%">
                      <el-option label="高中" value="高中"></el-option>
                      <el-option label="大专" value="大专"></el-option>
                      <el-option label="本科" value="本科"></el-option>
                      <el-option label="硕士" value="硕士"></el-option>
                      <el-option label="博士" value="博士"></el-option>
                    </el-select>
                  </div>
                  <div class="form-item">
                    <label>开始时间</label>
                    <el-input v-model="edu.start_date" placeholder="YYYY-MM"></el-input>
                  </div>
                  <div class="form-item">
                    <label>结束时间</label>
                    <el-input v-model="edu.end_date" placeholder="YYYY-MM 或 至今"></el-input>
                  </div>
                  <div class="form-item">
                    <label>&nbsp;</label>
                    <el-button type="danger" size="small" @click="removeEducation(index)">删除</el-button>
                  </div>
                </div>
              </div>
            </div>

            <!-- 工作经历 -->
            <div class="form-group">
              <div class="form-group-header">
                <h4 class="form-group-title">💼 工作经历</h4>
                <el-button type="primary" size="small" @click="addExperience">+ 添加工作经历</el-button>
              </div>
              <div class="experience-item" v-for="(exp, index) in generateForm.experience" :key="index">
                <div class="form-row">
                  <div class="form-item">
                    <label>公司名称</label>
                    <el-input v-model="exp.company" placeholder="请输入公司名称"></el-input>
                  </div>
                  <div class="form-item">
                    <label>职位</label>
                    <el-input v-model="exp.position" placeholder="请输入职位"></el-input>
                  </div>
                </div>
                <div class="form-row">
                  <div class="form-item">
                    <label>开始时间</label>
                    <el-input v-model="exp.start_date" placeholder="YYYY-MM"></el-input>
                  </div>
                  <div class="form-item">
                    <label>结束时间</label>
                    <el-input v-model="exp.end_date" placeholder="YYYY-MM 或 至今"></el-input>
                  </div>
                  <div class="form-item">
                    <label>&nbsp;</label>
                    <el-button type="danger" size="small" @click="removeExperience(index)">删除</el-button>
                  </div>
                </div>
                <div class="form-item full-width">
                  <label>工作成就（每条成就另起一行）</label>
                  <el-input 
                    v-model="exp.achievements_text" 
                    type="textarea" 
                    :rows="3"
                    placeholder="例如：&#10;1. 负责公司官网前端开发&#10;2. 优化页面加载速度提升 40%&#10;3. 参与代码审查和技术文档编写"
                  ></el-input>
                </div>
              </div>
            </div>

            <!-- 项目经验 -->
            <div class="form-group">
              <div class="form-group-header">
                <h4 class="form-group-title">🚀 项目经验</h4>
                <el-button type="primary" size="small" @click="addProject">+ 添加项目经验</el-button>
              </div>
              <div class="project-item" v-for="(proj, index) in generateForm.projects" :key="index">
                <div class="form-row">
                  <div class="form-item">
                    <label>项目名称</label>
                    <el-input v-model="proj.name" placeholder="请输入项目名称"></el-input>
                  </div>
                  <div class="form-item">
                    <label>担任角色</label>
                    <el-input v-model="proj.role" placeholder="例如：前端负责人"></el-input>
                  </div>
                </div>
                <div class="form-item full-width">
                  <label>项目描述</label>
                  <el-input 
                    v-model="proj.description" 
                    type="textarea" 
                    :rows="3"
                    placeholder="请描述项目内容、技术栈和你的贡献"
                  ></el-input>
                </div>
                <div class="form-item full-width">
                  <label>&nbsp;</label>
                  <el-button type="danger" size="small" @click="removeProject(index)">删除</el-button>
                </div>
              </div>
            </div>

            <!-- 技能清单 -->
            <div class="form-group">
              <h4 class="form-group-title">🛠️ 技能清单</h4>
              <div class="skills-input">
                <el-input 
                  v-model="skillsInput" 
                  placeholder="输入技能后按回车或空格添加，例如：Vue.js、React、Java"
                  @keyup.enter="addSkill"
                  @keyup.space="addSkill"
                ></el-input>
                <div class="skills-tags">
                  <el-tag 
                    v-for="(skill, index) in generateForm.skills" 
                    :key="index"
                    closable
                    @close="removeSkill(index)"
                    class="skill-tag"
                  >
                    {{ skill }}
                  </el-tag>
                </div>
              </div>
            </div>

            <!-- 提交按钮 -->
            <div class="form-actions">
              <el-button type="primary" size="large" @click="submitGenerateForm" :loading="generating">
                ✨ 开始生成简历
              </el-button>
              <!-- 生成成功后显示下载按钮 -->
              <el-dropdown v-if="resumeData && resumeId" trigger="click" @command="(c) => downloadGeneratedResume(c)">
                <el-button type="success" size="large">
                  📥 下载简历 ▼
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="docx">Word (.docx)</el-dropdown-item>
                    <el-dropdown-item command="pdf">PDF (.pdf)</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>

            <Transition name="resume-preview-fade">
              <div v-if="resumeData && resumeId" class="generate-preview-wrap">
                <div class="generate-preview-head">
                  <h4 class="generate-preview-title">生成结果预览</h4>
                  <p class="generate-preview-sub">网页版精排预览；下载 Word 已统一为「微软雅黑」、规范行距与标题样式，便于打印与投递。</p>
                </div>

                <div class="cv-sheet cv-sheet--generated">
                  <header class="cv-sheet__hero">
                    <div class="cv-sheet__monogram" aria-hidden="true">{{ getInitials(resumeData.basic_info?.name) }}</div>
                    <div class="cv-sheet__hero-main">
                      <h1 class="cv-sheet__name">{{ resumeData.basic_info?.name || '候选人' }}</h1>
                      <p v-if="resumeData.basic_info?.job_target || generateForm.job_target" class="cv-sheet__intent">
                        {{ resumeData.basic_info?.job_target || generateForm.job_target }}
                      </p>
                      <div class="cv-sheet__chips">
                        <span v-if="resumeData.basic_info?.email" class="cv-chip">✉ {{ resumeData.basic_info.email }}</span>
                        <span v-if="resumeData.basic_info?.phone" class="cv-chip">☎ {{ resumeData.basic_info.phone }}</span>
                        <span v-if="generateForm.experience_years" class="cv-chip">经验 {{ generateForm.experience_years }}</span>
                      </div>
                    </div>
                  </header>

                  <div class="cv-sheet__grid">
                    <section v-if="resumeData.education?.length" class="cv-block">
                      <h2 class="cv-block__title"><span class="cv-block__dot"></span>教育背景</h2>
                      <div v-for="(edu, idx) in resumeData.education" :key="'g-edu-' + idx" class="cv-timeline-item">
                        <div class="cv-timeline-item__head">
                          <span class="cv-timeline-item__title">{{ edu.school }}</span>
                          <span class="cv-timeline-item__date">{{ edu.start_date }} — {{ edu.end_date || '至今' }}</span>
                        </div>
                        <p class="cv-timeline-item__sub">{{ edu.degree }} · {{ edu.major }}</p>
                      </div>
                    </section>

                    <section v-if="resumeData.experience?.length" class="cv-block">
                      <h2 class="cv-block__title"><span class="cv-block__dot"></span>工作经历</h2>
                      <div v-for="(exp, idx) in resumeData.experience" :key="'g-exp-' + idx" class="cv-timeline-item cv-timeline-item--exp">
                        <div class="cv-timeline-item__head">
                          <span class="cv-timeline-item__title">{{ exp.company }}</span>
                          <span class="cv-timeline-item__date">{{ exp.start_date }} — {{ exp.end_date || '至今' }}</span>
                        </div>
                        <p class="cv-timeline-item__role">{{ exp.position }}</p>
                        <ul v-if="exp.achievements?.length" class="cv-bullets">
                          <li v-for="(a, i) in exp.achievements" :key="i">{{ a }}</li>
                        </ul>
                      </div>
                    </section>

                    <section v-if="resumeData.projects?.length" class="cv-block">
                      <h2 class="cv-block__title"><span class="cv-block__dot"></span>项目经验</h2>
                      <div v-for="(proj, idx) in resumeData.projects" :key="'g-prj-' + idx" class="cv-project-card">
                        <div class="cv-project-card__top">
                          <span class="cv-project-card__name">{{ proj.name }}</span>
                          <span v-if="proj.role" class="cv-project-card__role">{{ proj.role }}</span>
                        </div>
                        <p class="cv-project-card__desc">{{ proj.description }}</p>
                      </div>
                    </section>

                    <section v-if="resumeData.skills?.length" class="cv-block cv-block--skills">
                      <h2 class="cv-block__title"><span class="cv-block__dot"></span>技能清单</h2>
                      <div class="cv-skill-cloud">
                        <span v-for="(skill, idx) in resumeData.skills" :key="'g-sk-' + idx" class="cv-skill-pill">{{ skill }}</span>
                      </div>
                    </section>
                  </div>
                </div>
              </div>
            </Transition>
          </div>
        </div>

        <!-- AI 优化简历：左边显示电子简历，右边显示优化建议 -->
        <div class="optimize-section" v-if="selectedFunction === 'optimize'">
          <!-- 未上传文件时提示 -->
          <div class="optimize-hint-section" v-if="!selectedFile">
            <div class="hint-card">
              <div class="hint-icon">📤</div>
              <h4>请先上传简历</h4>
              <p>AI 优化功能需要基于您的简历文件进行分析</p>
              <button class="btn-go-upload" @click="selectFunction('upload')">去上传简历</button>
            </div>
          </div>
          
          <!-- 已上传但未扫描 -->
          <div class="scan-section" v-if="selectedFile && !scanning && !resumeData">
            <button class="scan-btn" @click="startScanning" :disabled="!selectedFile">
              🤖 开始智能扫描
            </button>
          </div>
          
          <!-- 扫描中状态 -->
          <div class="scanning-section" v-if="scanning">
            <div class="scanning-animation">
              <div class="scanner-line"></div>
              <div class="scan-icon">🔍</div>
              <p class="scan-text">正在分析简历内容...</p>
              <p class="scan-subtext">AI 正在提取关键信息</p>
            </div>
          </div>
          
          <!-- 左右分屏布局：左边电子简历，右边优化预览 -->
          <div class="split-view" v-if="resumeData && !scanning">
            <!-- 左侧：原始电子简历卡片 -->
            <div class="original-resume-panel">
              <h3 class="section-title">📋 原始简历</h3>
              <div class="resume-card resume-card--premium">
                <div class="card-header">
                  <div class="avatar-placeholder">{{ getInitials(resumeData.basic_info.name) }}</div>
                  <div class="basic-info">
                    <h2 class="name">{{ resumeData.basic_info.name }}</h2>
                    <p class="contact">
                      <span v-if="resumeData.basic_info.email">📧 {{ resumeData.basic_info.email }}</span>
                      <span v-if="resumeData.basic_info.phone">📱 {{ resumeData.basic_info.phone }}</span>
                    </p>
                  </div>
                </div>

                <div class="card-content">
                  <!-- 教育背景 -->
                  <div class="card-section" v-if="resumeData.education && resumeData.education.length > 0">
                    <h4 class="card-section-title">🎓 教育背景</h4>
                    <div class="education-item" v-for="(edu, idx) in resumeData.education" :key="idx">
                      <div class="school">{{ edu.school }}</div>
                      <div class="degree">{{ edu.degree }} - {{ edu.major }}</div>
                      <div class="time">{{ edu.start_date }} - {{ edu.end_date || '至今' }}</div>
                    </div>
                  </div>

                  <!-- 工作经历 -->
                  <div class="card-section" v-if="resumeData.experience && resumeData.experience.length > 0">
                    <h4 class="card-section-title">💼 工作经历</h4>
                    <div class="experience-item" v-for="(exp, idx) in resumeData.experience" :key="idx">
                      <div class="company">{{ exp.company }}</div>
                      <div class="position">{{ exp.position }}</div>
                      <div class="time">{{ exp.start_date }} - {{ exp.end_date || '至今' }}</div>
                      <ul class="achievements">
                        <li v-for="(achievement, i) in exp.achievements" :key="i">{{ achievement }}</li>
                      </ul>
                    </div>
                  </div>

                  <!-- 项目经验 -->
                  <div class="card-section" v-if="resumeData.projects && resumeData.projects.length > 0">
                    <h4 class="card-section-title">🚀 项目经验</h4>
                    <div class="project-item" v-for="(proj, idx) in resumeData.projects" :key="idx">
                      <div class="project-name">{{ proj.name }}</div>
                      <div class="project-role">{{ proj.role }}</div>
                      <div class="project-desc">{{ proj.description }}</div>
                    </div>
                  </div>

                  <!-- 技能清单 -->
                  <div class="card-section" v-if="resumeData.skills && resumeData.skills.length > 0">
                    <h4 class="card-section-title">🛠️ 技能清单</h4>
                    <div class="skills-container">
                      <span class="skill-tag" v-for="(skill, idx) in resumeData.skills" :key="idx">
                        {{ skill }}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
              
              <!-- AI 优化的按钮 -->
              <div class="optimize-actions">
                <button class="btn-optimize" @click="optimizeResume" :disabled="optimizing">
                  <span class="btn-icon">{{ optimizing ? '⏳' : '🤖' }}</span>
                  <span class="btn-text">{{ optimizing ? 'AI 优化中...' : 'AI 优化预览' }}</span>
                </button>
              </div>
            </div>
            
            <!-- 右侧：AI 优化后的预览（卡片式简历） -->
            <div class="optimized-resume-panel" v-if="optimizedResumeData">
              <h3 class="section-title">✨ 优化后预览</h3>
              <div class="resume-card resume-card--premium">
                <div class="card-header">
                  <div class="avatar-placeholder">{{ getInitials(optimizedResumeData.basic_info.name) }}</div>
                  <div class="basic-info">
                    <h2 class="name">{{ optimizedResumeData.basic_info.name }}</h2>
                    <p class="contact">
                      <span v-if="optimizedResumeData.basic_info.email">📧 {{ optimizedResumeData.basic_info.email }}</span>
                      <span v-if="optimizedResumeData.basic_info.phone">📱 {{ optimizedResumeData.basic_info.phone }}</span>
                    </p>
                  </div>
                </div>

                <div class="card-content">
                  <!-- 教育背景 -->
                  <div class="card-section" v-if="optimizedResumeData.education && optimizedResumeData.education.length > 0">
                    <h4 class="card-section-title">🎓 教育背景</h4>
                    <div class="education-item" v-for="(edu, idx) in optimizedResumeData.education" :key="idx">
                      <div class="school">{{ edu.school }}</div>
                      <div class="degree">{{ edu.degree }} - {{ edu.major }}</div>
                      <div class="time">{{ edu.start_date }} - {{ edu.end_date || '至今' }}</div>
                    </div>
                  </div>

                  <!-- 工作经历 -->
                  <div class="card-section" v-if="optimizedResumeData.experience && optimizedResumeData.experience.length > 0">
                    <h4 class="card-section-title">💼 工作经历</h4>
                    <div class="experience-item" v-for="(exp, idx) in optimizedResumeData.experience" :key="idx">
                      <div class="company">{{ exp.company }}</div>
                      <div class="position">{{ exp.position }}</div>
                      <div class="time">{{ exp.start_date }} - {{ exp.end_date || '至今' }}</div>
                      <ul class="achievements">
                        <li v-for="(achievement, i) in exp.achievements" :key="i">{{ achievement }}</li>
                      </ul>
                    </div>
                  </div>

                  <!-- 项目经验 -->
                  <div class="card-section" v-if="optimizedResumeData.projects && optimizedResumeData.projects.length > 0">
                    <h4 class="card-section-title">🚀 项目经验</h4>
                    <div class="project-item" v-for="(proj, idx) in optimizedResumeData.projects" :key="idx">
                      <div class="project-name">{{ proj.name }}</div>
                      <div class="project-role">{{ proj.role }}</div>
                      <div class="project-desc">{{ proj.description }}</div>
                    </div>
                  </div>

                  <!-- 技能清单 -->
                  <div class="card-section" v-if="optimizedResumeData.skills && optimizedResumeData.skills.length > 0">
                    <h4 class="card-section-title">🛠️ 技能清单</h4>
                    <div class="skills-container">
                      <span class="skill-tag" v-for="(skill, idx) in optimizedResumeData.skills" :key="idx">
                        {{ skill }}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
              
              <!-- 操作按钮 -->
              <div class="action-buttons">
                <el-dropdown trigger="click" @command="(c) => downloadOptimizedResume(c)">
                  <button type="button" class="btn-download">
                    📥 下载简历 ▼
                  </button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="docx">Word (.docx)</el-dropdown-item>
                      <el-dropdown-item command="pdf">PDF (.pdf)</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
                <button class="btn-regenerate" @click="optimizeResume">
                  🔄 重新优化
                </button>
              </div>
            </div>

            <!-- 右侧占位提示（优化前） -->
            <div class="optimized-placeholder-panel" v-if="!optimizedResumeData && !optimizing">
              <div class="placeholder-inner">
                <div class="placeholder-icon">✨</div>
                <p class="placeholder-title">点击左侧按钮开始 AI 优化</p>
                <p class="placeholder-hint">AI 将基于您的简历内容进行专业优化，包括 STAR 法则改写、量化成果、关键词优化等</p>
              </div>
            </div>

            <!-- 右侧加载中 -->
            <div class="optimized-placeholder-panel" v-if="optimizing">
              <div class="placeholder-inner">
                <div class="placeholder-icon optimizing-spin">🤖</div>
                <p class="placeholder-title">AI 正在优化中...</p>
                <p class="placeholder-hint">正在分析简历内容并生成优化建议，请稍候</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { notifyError, notifyInfo, notifySuccess, notifyWarning } from '@/utils/appNotify'
import {
  uploadResumeApi,
  analyzeResumeApi,
  generateResume as generateResumeApi,
  optimizeAndDownloadResumeApi,
  downloadResumeDocx,
  downloadResume,
} from '@/api/endpoints'

const fileInput = ref(null)
const selectedFile = ref(null)
const previewUrl = ref('')  // PDF 预览 URL
const scanning = ref(false)
const resumeData = ref(null)
const resumeId = ref(null)  // 保存简历 ID（整数类型），用于下载
const selectedFunction = ref('generate')  // 当前选择的功能：upload, generate, optimize
const optimizing = ref(false)  // AI 优化中状态
const optimizedResumeData = ref(null)  // AI 优化后的结构化简历数据（用于卡片渲染）
const optimizedText = ref(null)  // AI 优化后的文本内容（用于下载）

// AI 生成简历表单数据
const generateForm = reactive({
  name: '',
  gender: '',
  email: '',
  phone: '',
  job_target: '',
  experience_years: '',
  education: [],
  experience: [],
  projects: [],
  skills: []
})

const skillsInput = ref('')
const generating = ref(false)
const route = useRoute()

// 从个人信息自动填充
onMounted(() => {
  const focus = route.query.focus
  if (focus === 'upload' || focus === 'generate' || focus === 'optimize') {
    selectedFunction.value = focus
  } else {
    selectedFunction.value = 'generate'
  }

  const userProfile = localStorage.getItem('ai-interview-user-profile')
  if (userProfile) {
    try {
      const profile = JSON.parse(userProfile)
      generateForm.name = profile.username || ''
      generateForm.email = profile.email || ''
      generateForm.gender = profile.gender || ''
    } catch (e) {
      console.error('解析个人信息失败:', e)
    }
  }
  
  // 尝试从本地加载之前保存的简历 ID
  const savedId = localStorage.getItem('ai-resume-id')
  if (savedId) {
    resumeId.value = parseInt(savedId)
    notifyInfo(`已加载之前的简历 ID: ${resumeId.value}`, '简历工作台')
  }
})

// 添加教育经历
const addEducation = () => {
  generateForm.education.push({
    school: '',
    major: '',
    degree: '',
    start_date: '',
    end_date: ''
  })
}

// 删除教育经历
const removeEducation = (index) => {
  generateForm.education.splice(index, 1)
}

// 添加工作经历
const addExperience = () => {
  generateForm.experience.push({
    company: '',
    position: '',
    start_date: '',
    end_date: '',
    achievements_text: ''
  })
}

// 删除工作经历
const removeExperience = (index) => {
  generateForm.experience.splice(index, 1)
}

// 添加项目经验
const addProject = () => {
  generateForm.projects.push({
    name: '',
    role: '',
    description: ''
  })
}

// 删除项目经验
const removeProject = (index) => {
  generateForm.projects.splice(index, 1)
}

// 添加技能
const addSkill = () => {
  const skill = skillsInput.value.trim()
  if (skill) {
    // 支持中文逗号分隔
    const skills = skill.split(/[,,,]/).filter(s => s.trim())
    skills.forEach(s => {
      if (!generateForm.skills.includes(s.trim())) {
        generateForm.skills.push(s.trim())
      }
    })
    skillsInput.value = ''
  }
}

// 删除技能
const removeSkill = (index) => {
  generateForm.skills.splice(index, 1)
}

// 提交生成简历表单
const submitGenerateForm = async () => {
  // 验证必填字段
  if (!generateForm.name) {
    notifyError('请输入姓名', 'AI 生成简历')
    return
  }
  if (!generateForm.email) {
    notifyError('请输入邮箱', 'AI 生成简历')
    return
  }
  if (generateForm.education.length === 0) {
    notifyError('请至少添加一条教育经历', 'AI 生成简历')
    return
  }

  generating.value = true
  
  try {
    // 准备工作经历数据（将 achievements_text 转换为数组）
    const experienceData = generateForm.experience.map(exp => ({
      company: exp.company,
      position: exp.position,
      start_date: exp.start_date,
      end_date: exp.end_date,
      achievements: exp.achievements_text ? exp.achievements_text.split('\n').filter(line => line.trim()) : []
    }))

    // 构建提交数据
    const submitData = {
      name: generateForm.name,
      gender: generateForm.gender,
      email: generateForm.email,
      phone: generateForm.phone,
      job_target: generateForm.job_target,
      experience_years: generateForm.experience_years,
      education: generateForm.education,
      experience: experienceData,
      projects: generateForm.projects,
      skills: generateForm.skills
    }

    const res = await generateResumeApi(submitData)
    // 后端用 success_response 包装，结构为 {code, message, data: {...}}
    const payload = res?.data || res
    
    if (payload) {
      resumeData.value = normalizeResumeData(payload)
      resumeId.value = payload.resume_id || payload.id
      optimizedText.value = generateResumeText(resumeData.value)
      notifySuccess('简历生成成功！', 'AI 生成简历')
    } else {
      throw new Error('生成失败')
    }
  } catch (error) {
    console.error('简历生成失败:', error)
    notifyError('简历生成失败，请稍后重试', 'AI 生成简历')
  } finally {
    generating.value = false
  }
}

// 选择功能
const selectFunction = (funcName) => {
  selectedFunction.value = funcName
  if (funcName === 'upload') {
    // 上传简历功能，显示上传界面
    notifyInfo('请在下方上传简历', '简历工作台')
  } else if (funcName === 'generate') {
    // AI 生成简历 - 显示表单让用户填写信息
    notifyInfo('请填写简历基本信息', '简历工作台')
  } else if (funcName === 'optimize') {
    // AI 优化简历 - 检查是否已上传
    if (selectedFile.value) {
      // 已上传，提示开始优化
      notifyInfo('请点击按钮开始 AI 优化', '简历工作台')
    } else {
      notifyWarning('请先上传简历文件', '简历工作台')
    }
  }
}

// 触发文件选择
const triggerUpload = () => {
  fileInput.value?.click()
}

// 处理文件选择
const handleFileSelect = (event) => {
  const file = event.target.files[0]
  if (file) {
    validateAndSetFile(file)
    // 保存文件信息到本地
    localStorage.setItem('ai-resume-file-info', JSON.stringify({
      name: file.name,
      size: file.size,
      type: file.type
    }))
  }
  // 清空 input，允许重复选择同一文件
  event.target.value = ''
}

// 处理拖拽上传
const handleDrop = (event) => {
  const file = event.dataTransfer.files[0]
  if (file) {
    validateAndSetFile(file)
    // 保存文件信息到本地
    localStorage.setItem('ai-resume-file-info', JSON.stringify({
      name: file.name,
      size: file.size,
      type: file.type
    }))
  }
}

// 验证并设置文件
const validateAndSetFile = (file) => {
  const allowedTypes = ['.pdf', '.doc', '.docx', '.txt']
  const fileExt = '.' + file.name.split('.').pop().toLowerCase()
  
  if (!allowedTypes.includes(fileExt)) {
    notifyError('仅支持 PDF、Word、TXT 格式的简历文件', '文件格式')
    return
  }
  
  if (file.size > 10 * 1024 * 1024) {
    notifyError('文件大小不能超过 10MB', '文件校验')
    return
  }
  
  selectedFile.value = file
  
  // 生成 PDF 预览 URL
  if (file.type === 'application/pdf') {
    previewUrl.value = URL.createObjectURL(file)
  } else {
    previewUrl.value = ''
  }
  
  notifySuccess(`已选择：${file.name}`, '简历上传')
}

// 删除简历相关本地数据
const clearResumeLocal = () => {
  localStorage.removeItem('ai-resume-id')
  localStorage.removeItem('ai-resume-file-info')
}

// 移除文件
const removeFile = () => {
  selectedFile.value = null
  resumeData.value = null
  resumeId.value = null
  optimizedResumeData.value = null
  optimizedText.value = null
  clearResumeLocal()
}

// 格式化文件大小
const formatFileSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
}

// 获取文件类型提示
const getFileTypeHint = (file) => {
  const ext = '.' + file.name.split('.').pop().toLowerCase()
  if (ext === '.doc' || ext === '.docx') {
    return 'Word 文档，建议在浏览器中打开查看'
  } else if (ext === '.txt') {
    return '文本文件，可直接查看内容'
  }
  return '文件格式'
}

// 获取姓名的首字母
const getInitials = (name) => {
  if (!name) return ''
  return name.charAt(0).toUpperCase()
}

// 下载原简历
const downloadOriginalResume = async (format = 'docx') => {
  if (!resumeId.value) {
    notifyWarning('未找到简历 ID，请重新上传', '下载原简历')
    return
  }
  
  try {
    const blob = await downloadResume(resumeId.value, format)
    const ext = format === 'pdf' ? 'pdf' : 'docx'
    
    // 创建下载链接
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `原简历_${resumeData.value.basic_info.name}_${new Date().getTime()}.${ext}`
    document.body.appendChild(link)
    link.click()
    
    // 清理
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    
    notifySuccess('原简历下载成功！', '下载原简历')
  } catch (error) {
    console.error('下载失败:', error)
    notifyError('下载失败，请重试', '下载原简历')
  }
}

// AI 优化简历并预览
const optimizeResume = async () => {
  if (!resumeData.value) {
    notifyWarning('请先上传并分析简历', 'AI 优化')
    return
  }
  
  optimizing.value = true
  
  try {
    const res = await optimizeAndDownloadResumeApi(resumeData.value)
    // 后端用 success_response 包装，结构为 {code, message, data: {optimized_resume, optimized_text}}
    const payload = res?.data || res
    
    if (payload && payload.optimized_resume) {
      optimizedResumeData.value = normalizeResumeData(payload.optimized_resume)
      optimizedText.value = payload.optimized_text || generateResumeText(payload.optimized_resume)
      notifySuccess('AI 优化完成，请查看右侧预览', 'AI 优化')
    } else {
      throw new Error('优化失败，未返回内容')
    }
  } catch (error) {
    console.error('AI 优化失败:', error)
    optimizedResumeData.value = { ...resumeData.value }
    optimizedText.value = generateResumeText(resumeData.value)
    notifyWarning('AI 优化暂时不可用，已显示原简历预览', 'AI 优化')
  } finally {
    optimizing.value = false
  }
}

// 下载优化版简历（Word / PDF）
const downloadOptimizedResume = async (format = 'docx') => {
  if (!optimizedResumeData.value) {
    notifyWarning('请先点击 AI 优化预览', '下载优化简历')
    return
  }

  try {
    notifyInfo(format === 'pdf' ? '正在生成 PDF…' : '正在生成 Word…', '下载优化简历')
    const response = await downloadResumeDocx(optimizedResumeData.value, format)
    const blob = response instanceof Blob ? response : (response?.data instanceof Blob ? response.data : new Blob([response.data]))
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    const name = optimizedResumeData.value?.basic_info?.name || '简历'
    const ext = format === 'pdf' ? 'pdf' : 'docx'
    link.download = `优化版简历_${name}.${ext}`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    notifySuccess('简历已下载', '下载优化简历')
  } catch (error) {
    console.error('下载失败:', error)
    notifyError('下载失败，请重试', '下载优化简历')
  }
}

// 下载生成的简历（Word / PDF）
const downloadGeneratedResume = async (format = 'docx') => {
  if (!resumeData.value) {
    notifyWarning('请先生成简历', '下载生成简历')
    return
  }

  try {
    notifyInfo(format === 'pdf' ? '正在生成 PDF…' : '正在生成 Word…', '下载生成简历')
    const docxPayload = JSON.parse(JSON.stringify(resumeData.value))
    docxPayload.basic_info = { ...(docxPayload.basic_info || {}) }
    if (generateForm.job_target && !docxPayload.basic_info.job_target) {
      docxPayload.basic_info.job_target = generateForm.job_target
    }
    const response = await downloadResumeDocx(docxPayload, format)
    const blob = response instanceof Blob ? response : (response?.data instanceof Blob ? response.data : new Blob([response.data]))
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    const name = resumeData.value?.basic_info?.name || '简历'
    const ext = format === 'pdf' ? 'pdf' : 'docx'
    link.download = `AI生成简历_${name}.${ext}`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    notifySuccess('简历已下载', '下载生成简历')
  } catch (error) {
    console.error('下载失败:', error)
    notifyError('下载失败，请重试', '下载生成简历')
  }
}

// 根据结构化数据生成可下载文本
const generateResumeText = (data) => {
  if (!data) return ''
  const info = data.basic_info || {}
  const eduLines = (data.education || []).map(
    edu => `  ${edu.school}  ${edu.degree}  ${edu.major}  ${edu.start_date} - ${edu.end_date || '至今'}`
  ).join('\n')
  const expLines = (data.experience || []).map(exp => {
    const achievements = Array.isArray(exp.achievements)
      ? exp.achievements.map(a => `    - ${a}`).join('\n')
      : (exp.achievements ? `    ${exp.achievements}` : '')
    return `  ${exp.company}  ${exp.position}  ${exp.start_date} - ${exp.end_date || '至今'}\n${achievements}`
  }).join('\n\n')
  const projLines = (data.projects || []).map(
    proj => `  ${proj.name}（${proj.role}）\n  ${proj.description}`
  ).join('\n\n')
  return `简历

基本信息：
  姓名：${info.name || ''}
  邮箱：${info.email || ''}
  电话：${info.phone || ''}

教育背景：
${eduLines || '  暂无'}

工作经历：
${expLines || '  暂无'}

项目经验：
${projLines || '  暂无'}

技能清单：
  ${(data.skills || []).join('、')}
`
}



// 获取评分等级样式
const getScoreClass = (score) => {
  if (score >= 80) return 'excellent'
  if (score >= 60) return 'good'
  return 'average'
}





// 规范化简历数据（将 achievements 统一为数组，处理后端/前端格式差异）
const normalizeResumeData = (data) => {
  if (!data) return data
  const normalized = { ...data }
  if (normalized.experience) {
    normalized.experience = normalized.experience.map(exp => ({
      ...exp,
      achievements: Array.isArray(exp.achievements)
        ? exp.achievements
        : (exp.achievements ? exp.achievements.split(/[\n。；;]/).map(s => s.trim()).filter(Boolean) : [])
    }))
  }
  return normalized
}

// 开始扫描
const startScanning = async () => {
  if (!selectedFile.value) {
    notifyWarning('请先选择简历文件', '简历上传')
    return
  }

  scanning.value = true
  
  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    
    const res = await analyzeResumeApi(formData)
    // 后端用 success_response 包装，axios 返回 response.data，结构为 {code, message, data: {...}}
    const payload = res?.data || res
    
    if (payload) {
      resumeData.value = normalizeResumeData(payload)
      resumeId.value = payload.resume_id || payload.id
      
      if (resumeId.value) {
        localStorage.setItem('ai-resume-id', String(resumeId.value))
      }
      notifySuccess('简历分析完成！', '简历分析')
    } else {
      throw new Error('分析失败')
    }
  } catch (error) {
    console.error('简历分析失败:', error)
    simulateResumeData()
    resumeId.value = Date.now()
    localStorage.setItem('ai-resume-id', String(resumeId.value))
    notifyWarning('AI 分析暂时不可用，已显示示例数据', '简历分析')
  } finally {
    scanning.value = false
  }
}

// 模拟简历数据（用于测试）
const simulateResumeData = () => {
  resumeData.value = {
    basic_info: {
      name: '张三',
      email: 'zhangsan@example.com',
      phone: '138****8888'
    },
    education: [
      {
        school: 'XX 大学',
        degree: '本科',
        major: '计算机科学与技术',
        start_date: '2019.09',
        end_date: '2023.06'
      }
    ],
    experience: [
      {
        company: 'XX 科技有限公司',
        position: '前端开发实习生',
        start_date: '2022.06',
        end_date: '2022.12',
        achievements: [
          '负责公司官网的前端开发，使用 Vue.js 框架',
          '优化页面加载速度，提升用户体验',
          '参与代码审查和技术文档编写'
        ]
      }
    ],
    projects: [
      {
        name: '在线面试系统',
        role: '前端负责人',
        description: '基于 Vue3 + FastAPI 的在线面试平台，支持文本、语音、视频多种面试模式'
      }
    ],
    skills: ['Vue.js', 'React', 'JavaScript', 'TypeScript', 'HTML/CSS', 'Node.js'],
    ai_analysis: {
      overall_score: 78,
      strengths: [
        '项目经验与求职方向匹配度高',
        '技术栈较为全面，涵盖主流前端框架',
        '有实际的公司实习经历'
      ],
      weaknesses: [
        '缺少量化成果，如性能提升百分比',
        '项目描述过于简单，缺乏技术细节',
        '技能清单缺少熟练程度说明'
      ],
      suggestions: [
        '在工作经历中添加具体的数据指标，如"页面加载速度提升 40%"',
        '详细描述项目中使用的技术方案和解决的难题',
        '在技能清单中标注熟练程度，如"精通"、"熟悉"、"了解"',
        '增加开源项目或个人技术博客链接，展示技术热情',
        '调整简历排版，突出重点信息，提高可读性'
      ],
      recommended_keywords: [
        '组件化开发',
        '性能优化',
        '响应式设计',
        'RESTful API',
        'Git 版本控制',
        '敏捷开发'
      ]
    }
  }
}

</script>

<style scoped>
/* 功能选择提示 */
.function-select-hint {
  text-align: center;
  margin-bottom: 25px;
  padding: 15px 0;
}

.function-select-hint p {
  font-size: 18px;
  color: #2c3e50;
  font-weight: 500;
  margin: 0;
  display: inline-block;
  padding: 10px 25px;
  background: linear-gradient(135deg, #e8f5e9 0%, #f0f7ff 100%);
  border-radius: 25px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

/* 功能卡片容器 - 横向排列 */
.function-cards-container {
  display: flex !important;
  flex-direction: row !important;
  gap: 20px;
  margin-bottom: 30px;
  justify-content: center;
  align-items: stretch;
  width: 100%;
  max-width: 1200px;
  margin-left: auto;
  margin-right: auto;
}

.function-card {
  flex: 1;
  max-width: 350px;
  min-width: 280px;
  background: #fff;
  border-radius: 12px;
  padding: 40px 30px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  border: 2px solid transparent;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.function-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
  border-color: #42b983;
}

.card-icon {
  font-size: 64px;
  margin-bottom: 15px;
}

.card-title {
  font-size: 20px;
  color: #2c3e50;
  margin-bottom: 10px;
  font-weight: 600;
}

.card-desc {
  font-size: 14px;
  color: #666;
  line-height: 1.6;
}

/* 选择功能后的布局：左侧导航，右侧内容 */
.function-detail-layout {
  display: flex;
  gap: 20px;
  min-height: calc(100vh - 180px);
  height: auto;
  align-items: stretch;
}

/* 左侧功能导航栏 */
.function-sidebar {
  width: 240px;
  flex-shrink: 0;
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  margin-bottom: 20px;
  padding-bottom: 20px;
  border-bottom: 1px solid #e6e6e6;
}

.sidebar-header--compact {
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--color-border, #e2e8f0);
}

.sidebar-title {
  display: block;
  font-size: 15px;
  font-weight: 800;
  color: var(--color-text-primary, #0f172a);
  letter-spacing: -0.02em;
}

.sidebar-sub {
  display: block;
  margin-top: 6px;
  font-size: 12px;
  color: var(--color-text-muted, #64748b);
}

.btn-back-functions {
  background: linear-gradient(135deg, #42b983 0%, #3aa876 100%);
  color: #fff;
  border: none;
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s;
  width: 100%;
}

.btn-back-functions:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(66, 185, 131, 0.3);
}

.function-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.function-nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 15px 20px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
  background: #f8f9fa;
  border: 2px solid transparent;
}

.function-nav-item:hover {
  background: #e8f5e9;
  transform: translateX(5px);
}

.function-nav-item.active {
  background: linear-gradient(135deg, #e8f5e9 0%, #f0f7ff 100%);
  border-color: #42b983;
  box-shadow: 0 2px 8px rgba(66, 185, 131, 0.2);
}

.nav-icon {
  font-size: 24px;
}

.nav-text {
  font-size: 15px;
  font-weight: 500;
  color: #2c3e50;
}

/* 右侧内容区 */
.function-content {
  flex: 1;
  background: #fff;
  border-radius: 12px;
  padding: 30px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  overflow-y: auto;
  min-height: 0;
}

.section-title {
  font-size: 18px;
  color: #2c3e50;
  margin-bottom: 20px;
  font-weight: 600;
}

/* 上传区域 */
.upload-section {
  margin-bottom: 30px;
}

.upload-area {
  background: #fff;
  border: 2px dashed #d0d0d0;
  border-radius: 12px;
  padding: 60px 40px;
  text-align: center;
  transition: all 0.3s;
  cursor: pointer;
}

.upload-area:hover {
  border-color: #42b983;
  background: #f9fff9;
}

.upload-content {
  margin-bottom: 20px;
}

.upload-icon {
  font-size: 64px;
  margin-bottom: 15px;
}

.upload-text {
  font-size: 16px;
  color: #2c3e50;
  margin-bottom: 8px;
}

.upload-hint {
  font-size: 13px;
  color: #999;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 8px;
  margin-bottom: 20px;
}

.file-icon {
  font-size: 40px;
}

.file-detail {
  flex: 1;
  text-align: left;
}

.file-name {
  font-size: 14px;
  color: #2c3e50;
  font-weight: 500;
  margin-bottom: 4px;
}

.file-size {
  font-size: 12px;
  color: #999;
}

.remove-btn {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: #ff6b6b;
  color: #fff;
  border: none;
  cursor: pointer;
  font-size: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s;
}

.remove-btn:hover {
  background: #ff5252;
  transform: scale(1.1);
}

.upload-btn {
  background: #42b983;
  color: #fff;
  border: none;
  padding: 12px 40px;
  border-radius: 25px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s;
}

.upload-btn:hover {
  background: #3aa876;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(66, 185, 131, 0.3);
}

/* AI 生成简历表单 */
.generate-section {
  background: #fff;
  border-radius: 12px;
  padding: 40px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  max-height: none;
  overflow-y: auto;
}

.generate-form {
  margin-top: 20px;
}

.form-hint {
  font-size: 14px;
  color: #666;
  text-align: center;
  margin-bottom: 30px;
}

.form-group {
  margin-bottom: 30px;
  padding-bottom: 30px;
  border-bottom: 1px solid #e6e6e6;
}

.form-group:last-child {
  border-bottom: none;
}

.form-group-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.form-group-title {
  font-size: 18px;
  color: #2c3e50;
  font-weight: 600;
  margin-bottom: 15px;
}

.form-row {
  display: flex;
  gap: 15px;
  margin-bottom: 15px;
}

.form-item {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.form-item.full-width {
  flex: 100%;
}

.form-item label {
  font-size: 14px;
  color: #555;
  margin-bottom: 8px;
  font-weight: 500;
}

.form-item .el-input,
.form-item .el-select {
  width: 100%;
}

.form-item textarea {
  resize: vertical;
}

.education-item,
.experience-item,
.project-item {
  background: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 15px;
  border: 1px solid #e9ecef;
}

.skills-input .el-input {
  margin-bottom: 15px;
}

.skills-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.skill-tag {
  margin-right: 0;
}

.form-actions {
  display: flex;
  justify-content: center;
  gap: 15px;
  margin-top: 40px;
  padding-top: 30px;
  border-top: 1px solid #e6e6e6;
}

/* 优化提示卡片 */
.optimize-hint-section {
  background: #fff;
  border-radius: 12px;
  padding: 60px 40px;
  text-align: center;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.hint-card {
  max-width: 400px;
  margin: 0 auto;
}

.hint-icon {
  font-size: 64px;
  margin-bottom: 20px;
}

.hint-card h4 {
  font-size: 20px;
  color: #2c3e50;
  margin-bottom: 10px;
}

.hint-card p {
  font-size: 14px;
  color: #666;
  margin-bottom: 25px;
}

.btn-go-upload {
  background: linear-gradient(135deg, #42b983 0%, #3aa876 100%);
  color: #fff;
  border: none;
  padding: 12px 40px;
  border-radius: 25px;
  font-size: 15px;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-go-upload:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(66, 185, 131, 0.3);
}

/* AI 优化按钮样式 */
.btn-optimize {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  border: none;
  padding: 14px 32px;
  border-radius: 25px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
  margin-top: 20px;
  width: 100%;
}

.btn-optimize:hover:not(:disabled) {
  transform: translateY(-3px);
  box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
  background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
}

.btn-optimize:active:not(:disabled) {
  transform: translateY(-1px);
}

.btn-optimize:disabled {
  background: linear-gradient(135deg, #a0aec0 0%, #718096 100%);
  cursor: not-allowed;
  box-shadow: none;
}

.btn-optimize .btn-icon {
  font-size: 20px;
  animation: btnPulse 2s ease-in-out infinite;
}

@keyframes btnPulse {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.1);
  }
}

.btn-optimize .btn-text {
  letter-spacing: 0.5px;
}

/* 扫描按钮 */
.scan-section {
  text-align: center;
  margin: 30px 0;
}

.scan-btn {
  background: linear-gradient(135deg, #42b983 0%, #3aa876 100%);
  color: #fff;
  border: none;
  padding: 15px 60px;
  border-radius: 30px;
  font-size: 18px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 4px 12px rgba(66, 185, 131, 0.3);
}

.scan-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(66, 185, 131, 0.4);
}

.scan-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
}

/* 扫描中动画 */
.scanning-section {
  background: #fff;
  border-radius: 12px;
  padding: 80px 40px;
  text-align: center;
}

.scanning-animation {
  position: relative;
  max-width: 400px;
  margin: 0 auto;
}

.scanner-line {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, transparent, #42b983, transparent);
  animation: scan 2s ease-in-out infinite;
}

@keyframes scan {
  0%, 100% { top: 0; }
  50% { top: 100%; }
}

.scan-icon {
  font-size: 80px;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.1); opacity: 0.7; }
}

.scan-text {
  font-size: 18px;
  color: #2c3e50;
  margin-top: 30px;
  font-weight: 500;
}

.scan-subtext {
  font-size: 14px;
  color: #999;
  margin-top: 10px;
}

/* 结果区域 - 左右分屏布局 */
.result-section {
  display: flex;
  flex-direction: row;
  gap: 30px;
  margin-top: 30px;
}

/* 左右分屏布局 - AI 优化专用 */
.split-view {
  display: flex;
  gap: 30px;
  width: 100%;
}

.original-resume-panel {
  flex: 1;
  min-width: 0;
  background: #fff;
  border-radius: 12px;
  padding: 30px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.original-resume-panel .section-title {
  margin-bottom: 20px;
}

.resume-card-section {
  flex: 1;
  min-width: 0;
  background: #fff;
  border-radius: 12px;
  padding: 30px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.resume-card {
  border: 1px solid rgba(226, 232, 240, 0.95);
  border-radius: 12px;
  padding: 25px;
  background: linear-gradient(160deg, #ffffff 0%, #f8fafc 55%, #f1f5f9 100%);
  transition: box-shadow 0.35s ease, transform 0.35s ease;
}

.resume-card--premium {
  position: relative;
  overflow: hidden;
  border: 1px solid rgba(148, 163, 184, 0.35);
  border-radius: 14px;
  box-shadow:
    0 4px 28px rgba(15, 23, 42, 0.07),
    0 0 0 1px rgba(255, 255, 255, 0.6) inset;
}

.resume-card--premium::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #38bdf8, #3b82f6, #6366f1);
  border-radius: 14px 14px 0 0;
}

.resume-card--premium:hover {
  box-shadow:
    0 12px 40px rgba(37, 99, 235, 0.12),
    0 0 0 1px rgba(255, 255, 255, 0.7) inset;
  transform: translateY(-2px);
}

.generate-preview-wrap {
  margin-top: 28px;
  padding: 28px 24px 24px;
  border-radius: 18px;
  border: 1px solid rgba(147, 197, 253, 0.45);
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.95) 0%, rgba(239, 246, 255, 0.9) 50%, rgba(224, 242, 254, 0.5) 100%);
  box-shadow:
    0 12px 40px rgba(37, 99, 235, 0.08),
    0 0 0 1px rgba(255, 255, 255, 0.7) inset;
  position: relative;
  overflow: hidden;
}

.generate-preview-wrap::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #38bdf8, #3b82f6, #818cf8, #38bdf8);
  background-size: 200% 100%;
  animation: preview-accent-flow 8s linear infinite;
}

@keyframes preview-accent-flow {
  0% { background-position: 0% 50%; }
  100% { background-position: 200% 50%; }
}

.generate-preview-head {
  position: relative;
  z-index: 1;
}

.generate-preview-title {
  font-size: 18px;
  color: #0f172a;
  margin: 0 0 8px;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.generate-preview-sub {
  font-size: 13px;
  color: #64748b;
  margin: 0 0 20px;
  line-height: 1.55;
}

/* —— AI 生成简历：独立版式（杂志风 A4 感） —— */
.cv-sheet {
  position: relative;
  z-index: 1;
  max-width: 820px;
  margin: 0 auto;
  background: linear-gradient(165deg, #ffffff 0%, #f8fafc 38%, #f1f5f9 100%);
  border-radius: 20px;
  border: 1px solid rgba(148, 163, 184, 0.35);
  box-shadow:
    0 20px 50px rgba(15, 23, 42, 0.08),
    0 0 0 1px rgba(255, 255, 255, 0.9) inset;
  overflow: hidden;
  animation: cv-sheet-in 0.6s cubic-bezier(0.22, 1, 0.36, 1) both;
}

@keyframes cv-sheet-in {
  from {
    opacity: 0;
    transform: translateY(14px) scale(0.99);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.cv-sheet--generated::before {
  content: '';
  display: block;
  height: 5px;
  background: linear-gradient(90deg, #0ea5e9, #3b82f6, #6366f1, #8b5cf6);
  background-size: 180% 100%;
  animation: cv-topbar-flow 10s linear infinite;
}

@keyframes cv-topbar-flow {
  0% { background-position: 0% 50%; }
  100% { background-position: 200% 50%; }
}

.cv-sheet__hero {
  display: flex;
  align-items: stretch;
  gap: 0;
  padding: 28px 32px 24px;
  background:
    radial-gradient(ellipse 90% 120% at 100% 0%, rgba(59, 130, 246, 0.12), transparent 55%),
    linear-gradient(135deg, rgba(239, 246, 255, 0.95) 0%, rgba(255, 255, 255, 0.5) 100%);
  border-bottom: 1px solid rgba(226, 232, 240, 0.9);
}

.cv-sheet__monogram {
  width: 96px;
  min-width: 96px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 34px;
  font-weight: 800;
  letter-spacing: -0.04em;
  color: #fff;
  background: linear-gradient(145deg, #1d4ed8 0%, #3b82f6 45%, #6366f1 100%);
  border-radius: 16px;
  margin-right: 24px;
  box-shadow: 0 10px 28px rgba(37, 99, 235, 0.35);
}

.cv-sheet__hero-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 8px;
}

.cv-sheet__name {
  margin: 0;
  font-size: 28px;
  font-weight: 800;
  color: #0f172a;
  letter-spacing: -0.03em;
  line-height: 1.2;
}

.cv-sheet__intent {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #2563eb;
}

.cv-sheet__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 4px;
}

.cv-chip {
  font-size: 12px;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.85);
  border: 1px solid rgba(147, 197, 253, 0.65);
  color: #475569;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
}

.cv-sheet__grid {
  padding: 22px 32px 32px;
  display: flex;
  flex-direction: column;
  gap: 22px;
}

.cv-block__title {
  margin: 0 0 14px;
  font-size: 14px;
  font-weight: 800;
  color: #1e40af;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  display: flex;
  align-items: center;
  gap: 10px;
}

.cv-block__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: linear-gradient(135deg, #3b82f6, #6366f1);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
}

.cv-timeline-item {
  padding: 14px 16px;
  margin-bottom: 10px;
  border-radius: 12px;
  background: linear-gradient(90deg, rgba(248, 250, 252, 0.95) 0%, rgba(255, 255, 255, 0.6) 100%);
  border: 1px solid rgba(226, 232, 240, 0.85);
  border-left: 3px solid #3b82f6;
}

.cv-timeline-item:last-child {
  margin-bottom: 0;
}

.cv-timeline-item__head {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: baseline;
  gap: 8px;
}

.cv-timeline-item__title {
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
}

.cv-timeline-item__date {
  font-size: 12px;
  color: #64748b;
  font-variant-numeric: tabular-nums;
}

.cv-timeline-item__sub,
.cv-timeline-item__role {
  margin: 6px 0 0;
  font-size: 13px;
  color: #475569;
  line-height: 1.5;
}

.cv-bullets {
  margin: 10px 0 0;
  padding-left: 1.1em;
  color: #334155;
  font-size: 13px;
  line-height: 1.65;
}

.cv-bullets li {
  margin-bottom: 4px;
}

.cv-project-card {
  padding: 14px 16px;
  margin-bottom: 12px;
  border-radius: 12px;
  background: #fff;
  border: 1px solid rgba(226, 232, 240, 0.95);
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.04);
}

.cv-project-card:last-child {
  margin-bottom: 0;
}

.cv-project-card__top {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.cv-project-card__name {
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
}

.cv-project-card__role {
  font-size: 12px;
  padding: 2px 10px;
  border-radius: 6px;
  background: rgba(99, 102, 241, 0.1);
  color: #4f46e5;
  font-weight: 600;
}

.cv-project-card__desc {
  margin: 0;
  font-size: 13px;
  color: #475569;
  line-height: 1.65;
}

.cv-skill-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.cv-skill-pill {
  font-size: 12px;
  font-weight: 600;
  padding: 8px 14px;
  border-radius: 10px;
  background: linear-gradient(135deg, rgba(219, 234, 254, 0.9), rgba(224, 231, 255, 0.85));
  color: #1e40af;
  border: 1px solid rgba(129, 140, 248, 0.35);
}

@media (max-width: 640px) {
  .cv-sheet__hero {
    flex-direction: column;
    padding: 20px;
  }
  .cv-sheet__monogram {
    width: 100%;
    min-width: 0;
    height: 72px;
    margin-right: 0;
    margin-bottom: 12px;
  }
  .cv-sheet__grid {
    padding: 18px 16px 24px;
  }
}

.resume-preview-fade-enter-active,
.resume-preview-fade-leave-active {
  transition: opacity 0.4s ease, transform 0.4s ease;
}

.resume-preview-fade-enter-from,
.resume-preview-fade-leave-to {
  opacity: 0;
  transform: translateY(10px);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 20px;
  padding-bottom: 20px;
  border-bottom: 2px solid transparent;
  background: linear-gradient(90deg, rgba(59, 130, 246, 0.06), transparent 65%);
  margin-bottom: 20px;
  border-radius: 0 0 8px 8px;
  position: relative;
}

.card-header::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 2px;
  background: linear-gradient(90deg, #3b82f6, #6366f1 45%, transparent);
  border-radius: 2px;
  opacity: 0.85;
}

.avatar-placeholder {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: linear-gradient(145deg, #38bdf8, #3b82f6 40%, #4f46e5);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  font-weight: 600;
  box-shadow: 0 6px 20px rgba(59, 130, 246, 0.35);
  border: 3px solid rgba(255, 255, 255, 0.5);
}

.basic-info .name {
  font-size: 24px;
  color: #2c3e50;
  margin: 0 0 8px 0;
  font-weight: 600;
}

.contact {
  font-size: 14px;
  color: #666;
}

.contact span {
  margin-right: 15px;
}

.card-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.card-section {
  padding: 14px 16px 16px;
  margin-bottom: 12px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.9);
  border-radius: 10px;
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.9) 0%, rgba(255, 255, 255, 0.4) 100%);
  box-shadow: 0 1px 0 rgba(255, 255, 255, 0.8) inset;
}

.card-section:last-child {
  border-bottom: none;
  margin-bottom: 0;
}

.card-section-title {
  font-size: 15px;
  color: #1d4ed8;
  margin-bottom: 12px;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.education-item,
.experience-item,
.project-item {
  margin-bottom: 15px;
  padding: 12px 14px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.72);
  border-left: 3px solid #93c5fd;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
}

.school,
.company,
.project-name {
  font-size: 15px;
  color: #2c3e50;
  font-weight: 500;
  margin-bottom: 4px;
}

.degree,
.position,
.project-role {
  font-size: 14px;
  color: #666;
  margin-bottom: 4px;
}

.time {
  font-size: 13px;
  color: #999;
  margin-bottom: 8px;
}

.achievements {
  margin: 8px 0 0 20px;
  padding: 0;
}

.achievements li {
  font-size: 13px;
  color: #555;
  line-height: 1.6;
  margin-bottom: 4px;
}

.project-desc {
  font-size: 13px;
  color: #555;
  line-height: 1.6;
}

.skills-container {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.skill-tag {
  background: linear-gradient(135deg, #eff6ff 0%, #e0e7ff 100%);
  color: #1e293b;
  padding: 7px 15px;
  border-radius: 999px;
  font-size: 13px;
  border: 1px solid rgba(99, 102, 241, 0.35);
  box-shadow: 0 2px 6px rgba(59, 130, 246, 0.12);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.skill-tag:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.2);
}

/* AI 优化后简历面板 */
.optimized-resume-panel {
  flex: 1;
  min-width: 0;
  background: #fff;
  border-radius: 12px;
  padding: 30px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  border: 2px solid #e8f5e9;
}

/* 占位面板（优化前/优化中） */
.optimized-placeholder-panel {
  flex: 1;
  min-width: 0;
  background: #fafbff;
  border-radius: 12px;
  padding: 30px;
  border: 2px dashed #c8d8ff;
  display: flex;
  align-items: center;
  justify-content: center;
}

.placeholder-inner {
  text-align: center;
  max-width: 280px;
}

.placeholder-icon {
  font-size: 64px;
  margin-bottom: 16px;
  display: block;
}

.optimizing-spin {
  animation: spinPulse 1.5s ease-in-out infinite;
}

@keyframes spinPulse {
  0%, 100% { transform: scale(1) rotate(0deg); }
  50% { transform: scale(1.15) rotate(10deg); }
}

.placeholder-title {
  font-size: 16px;
  font-weight: 600;
  color: #2c3e50;
  margin-bottom: 10px;
}

.placeholder-hint {
  font-size: 13px;
  color: #999;
  line-height: 1.6;
}

/* AI 建议区域 */
.ai-suggestions-section {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.suggestion-cards {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.score-card {
  background: linear-gradient(135deg, #42b983 0%, #3aa876 100%);
  border-radius: 12px;
  padding: 25px;
  text-align: center;
  color: #fff;
}

.score-circle {
  width: 100px;
  height: 100px;
  border-radius: 50%;
  border: 4px solid rgba(255, 255, 255, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 10px;
  font-size: 32px;
  font-weight: 600;
}

.score-circle.excellent {
  background: rgba(255, 255, 255, 0.2);
}

.score-circle.good {
  background: rgba(255, 255, 255, 0.15);
}

.score-circle.average {
  background: rgba(255, 255, 255, 0.1);
}

.score-text {
  font-size: 14px;
  opacity: 0.9;
}

.suggestion-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  border-left: 4px solid;
}

.suggestion-card.strengths {
  border-left-color: #42b983;
}

.suggestion-card.improvements {
  border-left-color: #ffa502;
}

.suggestion-card.suggestions {
  border-left-color: #42b983;
}

.suggestion-card.keywords {
  border-left-color: #6c5ce7;
}

.suggestion-title {
  font-size: 16px;
  color: #2c3e50;
  margin-bottom: 12px;
  font-weight: 600;
}

.suggestion-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.suggestion-list li {
  font-size: 14px;
  color: #555;
  line-height: 1.8;
  padding: 6px 0;
}

.suggestion-details {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.suggestion-item {
  display: flex;
  gap: 10px;
  align-items: flex-start;
}

.suggestion-icon {
  font-size: 18px;
  flex-shrink: 0;
}

.suggestion-content {
  font-size: 14px;
  color: #555;
  line-height: 1.6;
  flex: 1;
}

.keyword-container {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}

.keyword-tag {
  background: #f0f0f0;
  color: #2c3e50;
  padding: 6px 12px;
  border-radius: 15px;
  font-size: 13px;
  border: 1px solid #ddd;
  transition: all 0.3s;
}

.keyword-tag.recommended {
  background: #f3e5f5;
  color: #6c5ce7;
  border-color: #6c5ce7;
}

.keyword-hint {
  font-size: 12px;
  color: #999;
  margin: 0;
}

/* 优化预览文本 */
.optimized-preview-text {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 20px;
  border: 1px solid #e9ecef;
}

.optimized-preview-text pre {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 14px;
  line-height: 1.8;
  color: #2c3e50;
  white-space: pre-wrap;
  word-wrap: break-word;
  margin: 0;
}

/* 操作按钮 */
.action-buttons {
  display: flex;
  gap: 15px;
  margin-top: 10px;
}

.btn-back,
.btn-download,
.btn-regenerate {
  flex: 1;
  padding: 14px;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-back {
  background: #f0f0f0;
  color: #2c3e50;
}

.btn-back:hover {
  background: #e0e0e0;
  transform: translateY(-2px);
}

.btn-download {
  background: linear-gradient(135deg, #42b983 0%, #3aa876 100%);
  color: #fff;
}

.btn-download:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(66, 185, 131, 0.3);
}

.btn-regenerate {
  background: #f0f0f0;
  color: #2c3e50;
}

.btn-regenerate:hover {
  background: #e0e0e0;
  transform: translateY(-2px);
}

/* 空状态 */
.empty-state {
  background: #fff;
  border-radius: 12px;
  padding: 100px 40px;
  text-align: center;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  margin-top: 30px;
}

.empty-icon {
  font-size: 80px;
  margin-bottom: 20px;
}

.empty-text {
  font-size: 18px;
  color: #2c3e50;
  margin-bottom: 8px;
  font-weight: 500;
}

.empty-subtext {
  font-size: 14px;
  color: #999;
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .function-detail-layout {
    flex-direction: column;
    min-height: auto;
  }
  .function-sidebar {
    width: 100%;
  }
  .split-view {
    flex-direction: column;
    gap: 18px;
  }
  .function-cards-container {
    flex-direction: column;
    align-items: center;
  }
  
  .function-card {
    max-width: 100%;
  }
  
  .result-section {
    grid-template-columns: 1fr;
  }
}
</style>
