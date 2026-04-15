<template>
  <router-view />
</template>

<script setup>
/**
 * App.vue 保持简洁，确保护航路由逻辑
 * 全局样式或全局状态初始化建议放在 main.js 或具体 Layout 中
 */
</script>

<style>
/* 确保全屏背景色和滚动条行为一致 */
#app {
  width: 100%;
  height: 100vh;
  margin: 0;
  padding: 0;
}

body, html {
  margin: 0;
  padding: 0;
  overflow: hidden; /* 由内部 Layout 处理滚动 */
  background-color: #0f172a; /* 配合登录页和整体暗色主题 */
}
</style>