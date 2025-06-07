<template>
  <div class="dashboard">
    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :xs="24" :sm="12" :md="6" v-for="(card, index) in statisticsCards" :key="index">
        <el-card class="stats-card" :class="card.class">
          <div class="card-content">
            <div class="card-value">{{ card.value }}</div>
            <div class="card-title">{{ card.title }}</div>
          </div>
          <div class="card-icon">
            <el-icon>
              <component :is="card.icon" />
            </el-icon>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="20" class="charts-row">
      <el-col :xs="24" :md="12">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>证书有效期分布</span>
            </div>
          </template>
          <div ref="expiryChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
      
      <el-col :xs="24" :md="12">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>证书类型分布</span>
            </div>
          </template>
          <div ref="typeChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 数据表格区域 -->
    <el-row :gutter="20" class="tables-row">
      <el-col :xs="24" :md="12">
        <el-card class="table-card">
          <template #header>
            <div class="card-header">
              <span>即将过期证书</span>
              <el-button type="text" @click="navigateTo('/certificates')">
                查看全部
              </el-button>
            </div>
          </template>
          <el-table :data="expiringCertificates" style="width: 100%">
            <el-table-column prop="domain" label="域名" />
            <el-table-column prop="expires_at" label="过期时间" width="120">
              <template #default="scope">
                {{ formatDate(scope.row.expires_at) }}
              </template>
            </el-table-column>
            <el-table-column prop="days_left" label="剩余天数" width="100">
              <template #default="scope">
                <el-tag :type="getDaysLeftTagType(scope.row.days_left)">
                  {{ scope.row.days_left }}天
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120">
              <template #default="scope">
                <el-button type="text" size="small" @click="renewCertificate(scope.row.id)">
                  续期
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      
      <el-col :xs="24" :md="12">
        <el-card class="table-card">
          <template #header>
            <div class="card-header">
              <span>最近告警</span>
              <el-button type="text" @click="navigateTo('/alerts')">
                查看全部
              </el-button>
            </div>
          </template>
          <el-table :data="recentAlerts" style="width: 100%">
            <el-table-column prop="type" label="类型" width="80">
              <template #default="scope">
                <el-tag :type="getAlertTypeTagType(scope.row.type)" size="small">
                  {{ getAlertTypeText(scope.row.type) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="message" label="消息" show-overflow-tooltip />
            <el-table-column prop="created_at" label="时间" width="120">
              <template #default="scope">
                {{ formatDate(scope.row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="80">
              <template #default="scope">
                <el-button type="text" size="small" @click="resolveAlert(scope.row.id)">
                  处理
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Document, Warning, Monitor, Bell } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import dayjs from 'dayjs'

const router = useRouter()

// 图表引用
const expiryChartRef = ref<HTMLDivElement>()
const typeChartRef = ref<HTMLDivElement>()

// 图表实例
let expiryChart: echarts.ECharts | null = null
let typeChart: echarts.ECharts | null = null

// 统计数据
const statisticsCards = reactive([
  {
    title: '证书总数',
    value: 24,
    icon: Document,
    class: 'blue-card'
  },
  {
    title: '即将过期',
    value: 5,
    icon: Warning,
    class: 'orange-card'
  },
  {
    title: '服务器总数',
    value: 8,
    icon: Monitor,
    class: 'green-card'
  },
  {
    title: '未处理告警',
    value: 3,
    icon: Bell,
    class: 'red-card'
  }
])

// 即将过期证书
const expiringCertificates = ref([
  {
    id: 1,
    domain: 'example.com',
    expires_at: '2025-06-20T00:00:00Z',
    days_left: 15
  },
  {
    id: 2,
    domain: 'api.example.com',
    expires_at: '2025-06-15T00:00:00Z',
    days_left: 10
  },
  {
    id: 3,
    domain: '*.test.com',
    expires_at: '2025-06-10T00:00:00Z',
    days_left: 5
  },
  {
    id: 4,
    domain: 'admin.example.org',
    expires_at: '2025-06-08T00:00:00Z',
    days_left: 3
  }
])

// 最近告警
const recentAlerts = ref([
  {
    id: 1,
    type: 'expiry',
    message: '证书 blog.example.net 将在 2 天后过期',
    created_at: '2025-06-05T08:00:00Z'
  },
  {
    id: 2,
    type: 'expiry',
    message: '证书 admin.example.org 将在 3 天后过期',
    created_at: '2025-06-05T07:30:00Z'
  },
  {
    id: 3,
    type: 'error',
    message: '证书 test.example.com 续期失败: DNS验证错误',
    created_at: '2025-06-04T15:20:00Z'
  }
])

// 初始化图表
const initCharts = () => {
  if (expiryChartRef.value) {
    expiryChart = echarts.init(expiryChartRef.value)
    expiryChart.setOption({
      tooltip: {
        trigger: 'item',
        formatter: '{b}: {c} ({d}%)'
      },
      legend: {
        orient: 'vertical',
        left: 'left'
      },
      series: [
        {
          name: '证书有效期',
          type: 'pie',
          radius: '70%',
          data: [
            { value: 16, name: '有效' },
            { value: 5, name: '即将过期' },
            { value: 3, name: '已过期' }
          ],
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowOffsetX: 0,
              shadowColor: 'rgba(0, 0, 0, 0.5)'
            }
          }
        }
      ]
    })
  }

  if (typeChartRef.value) {
    typeChart = echarts.init(typeChartRef.value)
    typeChart.setOption({
      tooltip: {
        trigger: 'item',
        formatter: '{b}: {c} ({d}%)'
      },
      legend: {
        orient: 'vertical',
        left: 'left'
      },
      series: [
        {
          name: '证书类型',
          type: 'pie',
          radius: '70%',
          data: [
            { value: 14, name: '单域名' },
            { value: 8, name: '通配符' },
            { value: 2, name: '多域名' }
          ],
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowOffsetX: 0,
              shadowColor: 'rgba(0, 0, 0, 0.5)'
            }
          }
        }
      ]
    })
  }
}

// 窗口大小改变时重新调整图表
const handleResize = () => {
  expiryChart?.resize()
  typeChart?.resize()
}

// 格式化日期
const formatDate = (dateString: string) => {
  return dayjs(dateString).format('MM-DD HH:mm')
}

// 获取剩余天数标签类型
const getDaysLeftTagType = (days: number) => {
  if (days <= 3) return 'danger'
  if (days <= 7) return 'warning'
  return 'success'
}

// 获取告警类型标签类型
const getAlertTypeTagType = (type: string) => {
  switch (type) {
    case 'expiry': return 'warning'
    case 'error': return 'danger'
    case 'revoke': return 'info'
    default: return 'info'
  }
}

// 获取告警类型文本
const getAlertTypeText = (type: string) => {
  switch (type) {
    case 'expiry': return '过期'
    case 'error': return '错误'
    case 'revoke': return '吊销'
    default: return type
  }
}

// 导航到指定页面
const navigateTo = (path: string) => {
  router.push(path)
}

// 续期证书
const renewCertificate = (id: number) => {
  ElMessage.success('证书续期任务已提交')
  console.log('续期证书:', id)
}

// 处理告警
const resolveAlert = (id: number) => {
  ElMessage.success('告警已处理')
  console.log('处理告警:', id)
}

onMounted(() => {
  initCharts()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  expiryChart?.dispose()
  typeChart?.dispose()
})
</script>

<style scoped>
.dashboard {
  padding: 0;
}

.stats-row {
  margin-bottom: 20px;
}

.stats-card {
  height: 120px;
  cursor: pointer;
  transition: transform 0.2s;
}

.stats-card:hover {
  transform: translateY(-2px);
}

.stats-card.blue-card {
  background: linear-gradient(135deg, #409eff, #36cfc9);
  color: white;
}

.stats-card.orange-card {
  background: linear-gradient(135deg, #ff9800, #ff5722);
  color: white;
}

.stats-card.green-card {
  background: linear-gradient(135deg, #4caf50, #8bc34a);
  color: white;
}

.stats-card.red-card {
  background: linear-gradient(135deg, #f44336, #e91e63);
  color: white;
}

.stats-card :deep(.el-card__body) {
  padding: 20px;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-content {
  display: flex;
  flex-direction: column;
}

.card-value {
  font-size: 28px;
  font-weight: bold;
  margin-bottom: 5px;
}

.card-title {
  font-size: 16px;
  opacity: 0.9;
}

.card-icon {
  font-size: 48px;
  opacity: 0.8;
}

.charts-row {
  margin-bottom: 20px;
}

.chart-card {
  margin-bottom: 20px;
}

.chart-container {
  height: 300px;
}

.tables-row {
  margin-bottom: 20px;
}

.table-card {
  margin-bottom: 20px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .stats-card {
    margin-bottom: 15px;
  }
  
  .chart-container {
    height: 250px;
  }
}
</style>
