<template>
  <div class="footer-container">
    <div class="footer-content">
      <!-- 第一行：标题 -->
      <div class="footer-top">
        <div class="site-info">
          <span class="site-name">AI 模拟面试中心</span>
          <span class="divider">|</span>
          <span class="slogan">让 AI 成为你的专属面试教练</span>
        </div>
      </div>
      
      <!-- 第二行：版权和技术 -->
      <div class="footer-bottom">
        <span class="copyright">2026 服务外包创新创业大赛参赛团队 版权所有</span>
        <span class="divider">|</span>
        <span class="tech-stack">技术支持：FastAPI + Vue 3 + MySQL</span>
        <span class="divider">|</span>
        <a href="https://github.com/liusucheng0213/ai-interview" target="_blank" rel="noopener noreferrer" class="github-link">项目仓库</a>
      </div>
    </div>
  </div>
</template>

<script setup>
</script>

<style scoped>
.footer-container {
  background: linear-gradient(to bottom, #e8f4ff, #d6ebff);
  padding: 20px 0;
  margin-top: auto;
  border-top: 1px solid #c4e0ff;
  width: 100%;
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 100;
}

.footer-content {
  width: 100%;
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 40px;
}

.footer-top {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.site-info {
  text-align: center;
  font-size: 14px;
  color: #5a6c7d;
}

.site-name {
  font-weight: 600;
}

.slogan {
  color: #8a9cae;
  font-weight: 400;
}

.divider {
  color: #b8d0e8;
  margin: 0 8px;
}

.footer-bottom {
  text-align: center;
  padding-top: 12px;
  border-top: 1px solid #c4e0ff;
  font-size: 11px;
  color: #9fb3c8;
}

.github-link {
  color: #4299e1;
  text-decoration: none;
}

.github-link:hover {
  text-decoration: underline;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .footer-container {
    padding: 15px 0;
  }
  
  .footer-content {
    padding: 0 15px;
  }
  
  .site-info {
    font-size: 12px;
  }
  
  .footer-bottom {
    font-size: 10px;
  }
}
</style>
