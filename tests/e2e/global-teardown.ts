/**
 * Playwright全局清理
 * 在所有测试运行后执行的清理操作
 */

import { FullConfig } from '@playwright/test'
import fs from 'fs'
import path from 'path'

async function globalTeardown(config: FullConfig) {
  console.log('🧹 开始E2E测试全局清理...')
  
  // 清理测试数据
  await cleanupTestData()
  
  // 清理认证状态文件
  await cleanupAuthStates()
  
  // 清理临时文件
  await cleanupTempFiles()
  
  console.log('✅ E2E测试全局清理完成')
}

/**
 * 清理测试数据
 */
async function cleanupTestData() {
  console.log('🗑️ 清理测试数据...')
  
  try {
    // 删除测试用户
    const deleteUserResponse = await fetch('http://localhost:5000/api/v1/users/testuser', {
      method: 'DELETE',
      headers: {
        'Authorization': 'Bearer admin_token' // 需要管理员权限
      }
    })
    
    if (deleteUserResponse.ok) {
      console.log('✅ 测试用户已删除')
    }
    
    // 清理测试服务器
    const serversResponse = await fetch('http://localhost:5000/api/v1/servers', {
      headers: {
        'Authorization': 'Bearer admin_token'
      }
    })
    
    if (serversResponse.ok) {
      const servers = await serversResponse.json()
      for (const server of servers.data.items) {
        if (server.name.includes('test')) {
          await fetch(`http://localhost:5000/api/v1/servers/${server.id}`, {
            method: 'DELETE',
            headers: {
              'Authorization': 'Bearer admin_token'
            }
          })
        }
      }
      console.log('✅ 测试服务器已清理')
    }
    
    // 清理测试证书
    const certificatesResponse = await fetch('http://localhost:5000/api/v1/certificates', {
      headers: {
        'Authorization': 'Bearer admin_token'
      }
    })
    
    if (certificatesResponse.ok) {
      const certificates = await certificatesResponse.json()
      for (const cert of certificates.data.items) {
        if (cert.domain.includes('test') || cert.domain.includes('example')) {
          await fetch(`http://localhost:5000/api/v1/certificates/${cert.id}`, {
            method: 'DELETE',
            headers: {
              'Authorization': 'Bearer admin_token'
            }
          })
        }
      }
      console.log('✅ 测试证书已清理')
    }
    
  } catch (error) {
    console.warn('⚠️ 测试数据清理失败:', error.message)
  }
}

/**
 * 清理认证状态文件
 */
async function cleanupAuthStates() {
  console.log('🔐 清理认证状态文件...')
  
  const authFiles = [
    'tests/e2e/auth-state.json',
    'tests/e2e/user-auth-state.json'
  ]
  
  for (const file of authFiles) {
    try {
      if (fs.existsSync(file)) {
        fs.unlinkSync(file)
        console.log(`✅ 已删除认证状态文件: ${file}`)
      }
    } catch (error) {
      console.warn(`⚠️ 删除认证状态文件失败: ${file}`, error.message)
    }
  }
}

/**
 * 清理临时文件
 */
async function cleanupTempFiles() {
  console.log('📁 清理临时文件...')
  
  const tempDirs = [
    'tests/reports/e2e_artifacts',
    'tests/temp'
  ]
  
  for (const dir of tempDirs) {
    try {
      if (fs.existsSync(dir)) {
        // 递归删除目录中的临时文件
        const files = fs.readdirSync(dir)
        for (const file of files) {
          const filePath = path.join(dir, file)
          const stat = fs.statSync(filePath)
          
          if (stat.isFile() && (
            file.endsWith('.tmp') ||
            file.endsWith('.temp') ||
            file.startsWith('temp_')
          )) {
            fs.unlinkSync(filePath)
            console.log(`✅ 已删除临时文件: ${filePath}`)
          }
        }
      }
    } catch (error) {
      console.warn(`⚠️ 清理临时文件失败: ${dir}`, error.message)
    }
  }
}

/**
 * 生成测试总结报告
 */
async function generateTestSummary() {
  console.log('📊 生成测试总结报告...')
  
  try {
    const reportDir = 'tests/reports'
    const summaryFile = path.join(reportDir, 'e2e_summary.json')
    
    const summary = {
      timestamp: new Date().toISOString(),
      status: 'completed',
      cleanup: {
        testData: 'cleaned',
        authStates: 'cleaned',
        tempFiles: 'cleaned'
      },
      notes: [
        '所有E2E测试已完成',
        '测试数据已清理',
        '认证状态文件已删除',
        '临时文件已清理'
      ]
    }
    
    if (!fs.existsSync(reportDir)) {
      fs.mkdirSync(reportDir, { recursive: true })
    }
    
    fs.writeFileSync(summaryFile, JSON.stringify(summary, null, 2))
    console.log(`✅ 测试总结报告已生成: ${summaryFile}`)
    
  } catch (error) {
    console.warn('⚠️ 生成测试总结报告失败:', error.message)
  }
}

export default globalTeardown
