<template>
  <div class="domain-monitoring-chart">
    <el-card class="chart-card">
      <template #header>
        <div class="card-header">
          <span>域名监控趋势</span>
          <div class="chart-controls">
            <el-select v-model="timeRange" @change="fetchChartData" size="small">
              <el-option label="最近24小时" value="24h" />
              <el-option label="最近7天" value="7d" />
              <el-option label="最近30天" value="30d" />
            </el-select>
            <el-button size="small" @click="refreshChart" :loading="loading">
              刷新
            </el-button>
          </div>
        </div>
      </template>

      <div class="chart-content" v-loading="loading">
        <!-- 响应时间趋势图 -->
        <div class="chart-section">
          <h4>DNS响应时间趋势</h4>
          <div ref="responseTimeChartRef" class="chart-container"></div>
        </div>

        <!-- 可用性统计 -->
        <div class="chart-section">
          <h4>域名可用性统计</h4>
          <div class="availability-stats">
            <div class="stat-item">
              <div class="stat-value success">{{ availabilityStats.success_rate }}%</div>
              <div class="stat-label">成功率</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ availabilityStats.avg_response_time }}ms</div>
              <div class="stat-label">平均响应时间</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ availabilityStats.total_checks }}</div>
              <div class="stat-label">总检查次数</div>
            </div>
            <div class="stat-item">
              <div class="stat-value error">{{ availabilityStats.failed_checks }}</div>
              <div class="stat-label">失败次数</div>
            </div>
          </div>
        </div>

        <!-- 状态分布饼图 -->
        <div class="chart-section">
          <h4>检查状态分布</h4>
          <div ref="statusChartRef" class="chart-container small"></div>
        </div>

        <!-- 最近检查记录 -->
        <div class="chart-section">
          <h4>最近检查记录</h4>
          <el-timeline>
            <el-timeline-item
              v-for="(record, index) in recentChecks"
              :key="index"
              :timestamp="formatTime(record.created_at)"
              :type="getTimelineType(record.status)"
            >
              <div class="timeline-content">
                <div class="check-info">
                  <el-tag :type="getStatusType(record.status)" size="small">
                    {{ getStatusText(record.status) }}
                  </el-tag>
                  <span class="check-type">{{ getCheckTypeText(record.check_type) }}</span>
                  <span v-if="record.response_time" class="response-time">
                    {{ record.response_time }}ms
                  </span>
                </div>
                <div v-if="record.error_message" class="error-message">
                  {{ record.error_message }}
                </div>
              </div>
            </el-timeline-item>
          </el-timeline>

          <div v-if="recentChecks.length === 0" class="no-data">
            暂无检查记录
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { certificateApi } from '@/api/certificate'
import type { Certificate } from '@/types/certificate'
import dayjs from 'dayjs'

interface Props {
  certificate: Certificate
}

const props = defineProps<Props>()

// 响应式数据
const loading = ref(false)
const timeRange = ref('24h')
const responseTimeChartRef = ref()
const statusChartRef = ref()

let responseTimeChart: echarts.ECharts | null = null
let statusChart: echarts.ECharts | null = null

// 图表数据
const chartData = reactive({
  response_times: [],
  status_distribution: [],
  timestamps: []
})

// 可用性统计
const availabilityStats = reactive({
  success_rate: 0,
  avg_response_time: 0,
  total_checks: 0,
  failed_checks: 0
})

// 最近检查记录
const recentChecks = ref([])

// 方法
const fetchChartData = async () => {
  try {
    loading.value = true
    
    const response = await certificateApi.getDomainMonitoringChart(props.certificate.id, {
      time_range: timeRange.value
    })
    
    const data = response.data
    
    // 更新图表数据
    Object.assign(chartData, {
      response_times: data.response_times || [],
      status_distribution: data.status_distribution || [],
      timestamps: data.timestamps || []
    })
    
    // 更新统计数据
    Object.assign(availabilityStats, {
      success_rate: data.success_rate || 0,
      avg_response_time: data.avg_response_time || 0,
      total_checks: data.total_checks || 0,
      failed_checks: data.failed_checks || 0
    })
    
    // 更新最近检查记录
    recentChecks.value = data.recent_checks || []
    
    // 更新图表
    await nextTick()
    updateCharts()
    
  } catch (error) {
    console.error('获取图表数据失败:', error)
    ElMessage.error('获取图表数据失败')
  } finally {
    loading.value = false
  }
}

const initCharts = () => {
  // 初始化响应时间图表
  if (responseTimeChartRef.value) {
    responseTimeChart = echarts.init(responseTimeChartRef.value)
    
    const responseTimeOption = {
      tooltip: {
        trigger: 'axis',
        formatter: (params: any) => {
          const point = params[0]
          return `${point.name}<br/>响应时间: ${point.value}ms`
        }
      },
      xAxis: {
        type: 'category',
        data: chartData.timestamps,
        axisLabel: {
          formatter: (value: string) => dayjs(value).format('MM-DD HH:mm')
        }
      },
      yAxis: {
        type: 'value',
        name: '响应时间 (ms)',
        min: 0
      },
      series: [{
        name: '响应时间',
        type: 'line',
        data: chartData.response_times,
        smooth: true,
        lineStyle: {
          color: '#409EFF'
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [{
              offset: 0, color: 'rgba(64, 158, 255, 0.3)'
            }, {
              offset: 1, color: 'rgba(64, 158, 255, 0.1)'
            }]
          }
        }
      }]
    }
    
    responseTimeChart.setOption(responseTimeOption)
  }
  
  // 初始化状态分布图表
  if (statusChartRef.value) {
    statusChart = echarts.init(statusChartRef.value)
    
    const statusOption = {
      tooltip: {
        trigger: 'item',
        formatter: '{a} <br/>{b}: {c} ({d}%)'
      },
      legend: {
        orient: 'vertical',
        left: 'left'
      },
      series: [{
        name: '检查状态',
        type: 'pie',
        radius: '50%',
        data: chartData.status_distribution,
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)'
          }
        }
      }]
    }
    
    statusChart.setOption(statusOption)
  }
}

const updateCharts = () => {
  if (responseTimeChart) {
    responseTimeChart.setOption({
      xAxis: {
        data: chartData.timestamps.map(t => dayjs(t).format('MM-DD HH:mm'))
      },
      series: [{
        data: chartData.response_times
      }]
    })
  }
  
  if (statusChart) {
    statusChart.setOption({
      series: [{
        data: chartData.status_distribution
      }]
    })
  }
}

const refreshChart = () => {
  fetchChartData()
}

const resizeCharts = () => {
  if (responseTimeChart) {
    responseTimeChart.resize()
  }
  if (statusChart) {
    statusChart.resize()
  }
}

// 辅助方法
const getStatusType = (status: string) => {
  switch (status) {
    case 'success': return 'success'
    case 'failed': return 'danger'
    case 'timeout': return 'warning'
    default: return 'info'
  }
}

const getStatusText = (status: string) => {
  switch (status) {
    case 'success': return '成功'
    case 'failed': return '失败'
    case 'timeout': return '超时'
    default: return status
  }
}

const getCheckTypeText = (type: string) => {
  switch (type) {
    case 'dns': return 'DNS检查'
    case 'reachability': return '可达性检查'
    default: return type
  }
}

const getTimelineType = (status: string) => {
  switch (status) {
    case 'success': return 'success'
    case 'failed': return 'danger'
    case 'timeout': return 'warning'
    default: return 'info'
  }
}

const formatTime = (time: string) => {
  return dayjs(time).format('YYYY-MM-DD HH:mm:ss')
}

// 生命周期
onMounted(() => {
  fetchChartData().then(() => {
    nextTick(() => {
      initCharts()
    })
  })
  
  // 监听窗口大小变化
  window.addEventListener('resize', resizeCharts)
})

onUnmounted(() => {
  // 销毁图表实例
  if (responseTimeChart) {
    responseTimeChart.dispose()
  }
  if (statusChart) {
    statusChart.dispose()
  }
  
  // 移除事件监听
  window.removeEventListener('resize', resizeCharts)
})
</script>

<style scoped>
.domain-monitoring-chart {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chart-controls {
  display: flex;
  gap: 10px;
  align-items: center;
}

.chart-content {
  min-height: 400px;
}

.chart-section {
  margin-bottom: 30px;
}

.chart-section h4 {
  margin: 0 0 15px 0;
  color: #303133;
  font-size: 14px;
}

.chart-container {
  height: 300px;
  width: 100%;
}

.chart-container.small {
  height: 200px;
}

.availability-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 20px;
  margin: 20px 0;
}

.stat-item {
  text-align: center;
  padding: 15px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 5px;
}

.stat-value.success {
  color: #67c23a;
}

.stat-value.error {
  color: #f56c6c;
}

.stat-label {
  font-size: 12px;
  color: #909399;
}

.timeline-content {
  padding: 5px 0;
}

.check-info {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 5px;
}

.check-type {
  font-size: 12px;
  color: #606266;
}

.response-time {
  font-size: 12px;
  color: #909399;
}

.error-message {
  font-size: 12px;
  color: #f56c6c;
  margin-top: 5px;
}

.no-data {
  text-align: center;
  color: #909399;
  padding: 20px;
}
</style>
