<template>
  <div id="app">
    <router-view />
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

onMounted(() => {
  // 初始化认证状态
  authStore.initAuth()
})
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
  background-color: #f5f7fa;
  color: #303133;
}

#app {
  height: 100vh;
  overflow: hidden;
}

/* 全局样式 */
.page-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.table-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.table-toolbar .left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.table-toolbar .right {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .page-container {
    padding: 10px;
  }
  
  .table-toolbar {
    flex-direction: column;
    gap: 10px;
    align-items: stretch;
  }
  
  .table-toolbar .left,
  .table-toolbar .right {
    justify-content: center;
  }
}
</style>
