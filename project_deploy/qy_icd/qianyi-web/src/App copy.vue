<template>
  <div class="app-container" v-if="!isAuthPage">
    <el-container>
      <!-- 头部导航栏 -->
      <el-header class="app-header">
        <div class="header-content">
          <!-- 左侧Logo -->
          <div class="header-logo">
            <img src="@/assets/logo_02.png" alt="医院Logo" class="logo-image" />
          </div>

          <!-- 主菜单 -->
          <el-menu
            :default-active="activeMenu"
            class="main-menu"
            mode="horizontal"
            @select="handleMenuSelect"
          >
            <el-menu-item index="dashboard">
              <template #title>
                <el-icon><Monitor /></el-icon>
                <span>工作台</span>
              </template>
            </el-menu-item>
            <!-- 在主菜单中添加病案编码菜单项 -->
            <el-sub-menu index="coding">
              <template #title>
                <el-icon><Document /></el-icon>
                <span style="font-size: 16px; font-weight: 500"
                  >智能病案编码</span
                >
              </template>
              <el-menu-item index="coding-main">
                <el-icon><Document /></el-icon>
                <span>病案编码</span>
              </el-menu-item>
              <el-menu-item index="coding-pdf">
                <el-icon><Document /></el-icon>
                <span>PDF上传识别</span>
              </el-menu-item>
              <el-menu-item index="coding-structured">
                <el-icon><DataBoard /></el-icon>
                <span>结构化数据上传</span>
              </el-menu-item>
              <el-menu-item index="coding-history">
                <el-icon><Collection /></el-icon>
                <span>编码历史</span>
              </el-menu-item>
            </el-sub-menu>
            <el-menu-item index="drg">
              <template #title>
                <el-icon><PieChart /></el-icon>
                <span>DRG预分组</span>
              </template>
            </el-menu-item>
            <el-menu-item index="knowledge">
              <template #title>
                <el-icon><Reading /></el-icon>
                <span>疾病手术知识查询</span>
              </template>
            </el-menu-item>
            <el-sub-menu index="system" v-if="userRole === 0">
              <template #title>
                <el-icon><Setting /></el-icon>
                <span style="font-size: 16px; font-weight: 500">系统设置</span>
              </template>
              <el-menu-item index="user-management">
                <el-icon><User /></el-icon>
                <span>用户管理</span>
              </el-menu-item>
              <el-menu-item index="change-password">
                <el-icon><Lock /></el-icon>
                <span>修改密码</span>
              </el-menu-item>
            </el-sub-menu>
          </el-menu>

          <!-- 右侧Logo -->
          <div class="header-right-section">
            <div class="partner-logos">
              <img
                src="@/assets/qfsLogo.png"
                alt="合作伙伴Logo"
                class="partner-logo"
                style="height: 50px"
              />
              <img
                src="@/assets/chaosuanLogo.png"
                alt="合作伙伴Logo"
                class="partner-logo"
                style="height: 40px"
              />
            </div>
            <el-button
              type="danger"
              plain
              size="small"
              @click="logout"
              class="logout-button"
            >
              <el-icon><SwitchButton /></el-icon>
              <span>退出</span>
            </el-button>
          </div>
        </div>
      </el-header>

      <el-container class="app-body">
        <!-- 侧边栏（仅LLM功能页面显示） -->
        <el-aside
          v-if="showHistorySidebar"
          :width="sidebarWidth"
          class="history-sidebar"
        >
          <!-- 侧边栏头部 -->
          <div class="sidebar-header">
            <h3 v-show="!sidebarCollapsed">对话历史</h3>
            <el-tooltip
              :content="sidebarCollapsed ? '展开侧边栏' : '折叠侧边栏'"
              placement="bottom"
            >
              <el-button
                circle
                size="small"
                @click="toggleSidebar"
                class="collapse-button"
              >
                <el-icon>
                  <component :is="sidebarCollapsed ? 'Expand' : 'Fold'" />
                </el-icon>
              </el-button>
            </el-tooltip>
          </div>

          <!-- 历史记录列表 -->
          <div class="history-list-container">
            <el-scrollbar>
              <!-- 加载状态 -->
              <div v-if="isLoading" class="loading-state">
                <el-icon class="is-loading"><Loading /></el-icon>
                <span>加载历史记录中...</span>
              </div>

              <!-- 错误状态 -->
              <div v-else-if="error" class="error-state">
                <el-icon><Warning /></el-icon>
                <span>{{ error }}</span>
              </div>
              <!-- 正常状态 -->
              <el-menu
                :default-active="activeHistory"
                class="history-menu"
                @select="handleHistorySelect"
              >
                <el-menu-item
                  v-for="(item, index) in historyList"
                  :key="item.id"
                  :index="item.id"
                >
                  <template #title>
                    <el-icon><ChatLineRound /></el-icon>
                    <span class="history-title">
                      {{ item.title || defaultHistoryTitle(index) }}
                    </span>
                    <span class="history-date">
                      {{ formatDate(item.time) }}
                    </span>
                    <!-- 编辑按钮 -->
                    <el-button
                      link
                      type="primary"
                      size="small"
                      @click.stop="showEditDialog(item)"
                      class="edit-button"
                    >
                      <el-icon><Edit /></el-icon>
                    </el-button>
                    <el-button
                      link
                      type="danger"
                      size="small"
                      @click.stop="confirmDelete(item.id)"
                      class="delete-button"
                    >
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </template>
                </el-menu-item>
              </el-menu>
            </el-scrollbar>
          </div>
          <!-- 新对话按钮 -->
          <div class="new-chat-container">
            <el-tooltip
              :content="
                canCreateNewChat
                  ? '开始新对话'
                  : '请先完成当前对话后再创建新对话'
              "
              placement="top"
              :disabled="sidebarCollapsed"
            >
              <el-button
                type="primary"
                @click="startNewChat"
                :icon="Plus"
                :circle="sidebarCollapsed"
                :disabled="!canCreateNewChat"
                class="new-chat-button"
              >
                <span v-if="!sidebarCollapsed">
                  {{ canCreateNewChat ? '开始新对话' : '当前对话为空' }}
                </span>
              </el-button>
            </el-tooltip>
          </div>
        </el-aside>
        <!-- 拖动条 -->
        <div
          v-if="showHistorySidebar"
          class="sidebar-resizer"
          @mousedown="startDragging"
        ></div>

        <!-- 固定背景容器 -->
        <div class="background-container">
          <img
            src="@/assets/index_beijing.jpg"
            alt="背景图"
            class="background-image"
          />
        </div>

        <!-- 主内容区 -->
        <el-main class="main-content">
          <router-view />
        </el-main>
      </el-container>
    </el-container>
    <!-- 在模板底部添加编辑对话框 -->
    <el-dialog v-model="editDialogVisible" title="修改标题" width="30%">
      <el-input
        v-model="editingTitle"
        placeholder="请输入新的标题"
        maxlength="50"
        show-word-limit
      />
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="editDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="saveTitle">确定</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
  <router-view v-else />
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Monitor,
  Document,
  PieChart,
  Reading,
  ChatLineRound,
  Plus,
  Expand,
  Fold,
  Delete,
  Edit,
  SwitchButton,
  Setting,
  User,
  Lock, // 新增图标
} from '@element-plus/icons-vue'
import { ElMessageBox, ElMessage } from 'element-plus' // 确保导入这两个组件
import { provide } from 'vue'
import { useAuthStore } from '@/stores/auth'
// import { format } from 'date-fns'
// import { fetchHistory, saveHistoryItem } from '@/api/history'

// 使用 auth store
const authStore = useAuthStore()

// const userName = computed(() => authStore.user?.username || '')
const userRole = computed(() => authStore.user?.role)

onMounted(() => {
  authStore.restoreUser()
  console.log('当前用户信息:', authStore.user)
  console.log('用户角色:', userRole.value, '是否为管理员:', authStore.isAdmin())
})

// 添加以下变量
const editDialogVisible = ref(false)
const editingTitle = ref('')
const editingId = ref('')

// 添加以下方法
const showEditDialog = (item) => {
  editingId.value = item.id
  editingTitle.value =
    item.title ||
    defaultHistoryTitle(historyList.value.findIndex((i) => i.id === item.id))
  editDialogVisible.value = true
}

const saveTitle = () => {
  if (!editingId.value) return

  const type = activeMenu.value
  const history = historyData.value[type]
  const index = history.findIndex((item) => item.id === editingId.value)

  if (index !== -1) {
    history[index].title = editingTitle.value
    saveHistory()
    editDialogVisible.value = false
    ElMessage.success('标题修改成功')
  }
}

// 侧边栏宽度（默认为 '15vw' 展开时）
const defaultExpandedWidth = 360
const collapsedWidth = 50 // 一般是 3vw，你可以自定义

const sidebarWidth = computed(() => {
  return sidebarCollapsed.value
    ? `${collapsedWidth}px`
    : `${resizableWidth.value}px`
})

const resizableWidth = ref(defaultExpandedWidth)

let isDragging = false

const startDragging = (e) => {
  if (sidebarCollapsed.value) {
    sidebarCollapsed.value = false // 拖动时强制展开
  }

  isDragging = true
  document.addEventListener('mousemove', handleDragging)
  document.addEventListener('mouseup', stopDragging)
}

const handleDragging = (e) => {
  if (!isDragging) return
  const min = 120
  const max = 600
  const newWidth = Math.min(Math.max(e.clientX, min), max)
  resizableWidth.value = newWidth
}

const stopDragging = () => {
  isDragging = false
  document.removeEventListener('mousemove', handleDragging)
  document.removeEventListener('mouseup', stopDragging)
}

// 路由相关
const route = useRoute()
const router = useRouter()
const isAuthPage = computed(
  () => route.name === 'login' || route.name === 'register'
)
// 当前激活的菜单项
const activeMenu = ref('dashboard')
const isLoading = ref(false)
const error = ref(null)

// 添加退出方法

const logout = () => {
  ElMessageBox.confirm('确定要退出登录吗？', '退出确认', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  })
    .then(() => {
      // 不需要 async，因为主要操作是同步的
      try {
        // --- 1. 尝试清除 sessionid Cookie ---
        // 注意：如果 Django 的 sessionid Cookie 设置了 HttpOnly 标志（默认设置），此方法将无效
        // 你需要确切知道 Cookie 的 path，默认通常是 '/' 或你的应用前缀 (例如 '/qy/')
        // 假设你的 Django 应用部署在根路径 '/'
        document.cookie =
          'sessionid=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/; SameSite=Lax'

        // 如果你的 Django 应用部署在子路径，例如 '/qy/'，则需要这样清除：
        // document.cookie = "sessionid=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/qy/; SameSite=Lax";

        // --- 2. 尝试清除 csrftoken Cookie ---
        // 注意：如果 Django 的 csrftoken Cookie 设置了 HttpOnly 标志，此方法将无效
        // 通常 csrftoken Cookie 不是 HttpOnly，所以此方法可能有效
        document.cookie =
          'csrftoken=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/; SameSite=Lax'

        // 如果你的 Django 应用部署在子路径，例如 '/qy/'，则需要这样清除：
        // document.cookie = "csrftoken=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/qy/; SameSite=Lax";

        // --- 3. 清除本地存储的数据 (可选，根据需要) ---
        // 即使清除了 Cookie，清除本地数据也能让前端 UI 立即反应退出状态
        // localStorage.removeItem('llmHistoryData');
        // 如果有其他需要清除的本地数据，也在这里清除
        // localStorage.removeItem('userInfo'); // 如果存储了用户信息

        // --- 4. 清除 Pinia Store 中的认证状态 (如果你的 Store 里有) ---
        // 假设你的 auth store 有 logout 方法来清除状态
        // const auth = useAuthStore(); // 需要导入
        // auth.logout(); // 调用 store 的 logout 方法来清除内部状态

        // --- 5. 提示并跳转 ---
        ElMessage.success('已退出登录')
        // 重定向到登录页
        router.push('/login')
      } catch (error) {
        // 处理清除过程中的错误（虽然可能性较小）
        console.error('Logout state clearing error:', error)
        ElMessage.error('退出时发生错误')
      }
    })
    .catch(() => {
      // 用户取消退出
      console.log('用户取消退出')
    })
}

// 设置激活菜单的逻辑
const setActiveMenu = () => {
  const path = route.path
  const menuMap = {
    '/bigModel': 'coding',
    '/coding-pdf': 'coding',
    '/coding-structured': 'coding',
    '/coding-history': 'coding',
    '/drgGrouping': 'drg',
    '/query': 'knowledge',
    '/homeIndex': 'dashboard',
    // 系统设置
    '/user-management': 'system',
    '/change-password': 'system',
  }

  // 使用路由元信息或映射表
  const newMenu = route.meta.menuType || menuMap[path]

  if (newMenu && newMenu !== activeMenu.value) {
    activeMenu.value = newMenu
    console.log('当前路径:', path, '对应菜单:', activeMenu.value)

    if (showHistorySidebar.value) {
      console.log('当前菜单需要加载历史记录:', activeMenu.value)
      loadHistory()
      checkAndCreateInitialChat()
    }
  }
}

// 检查并创建初始对话（仅在没有任何历史记录时）
const checkAndCreateInitialChat = () => {
  const type = activeMenu.value
  const history = historyData.value[type]

  // 只有在完全没有历史记录时才创建新对话
  if (!history || history.length === 0) {
    createNewChat(type)
  } else {
    // 如果有历史记录，选择第一个
    activeHistory.value = history[0].id
  }
}

// 菜单选择处理
const handleMenuSelect = (index) => {
  const routeMap = {
    'coding-main': '/bigModel',
    'coding-pdf': '/coding-pdf',
    'coding-structured': '/coding-structured',
    'coding-history': '/coding-history',
    drg: '/drgGrouping',
    knowledge: '/query',
    dashboard: '/homeIndex',
    // 系统设置
    'user-management': '/user-management',
    'change-password': '/change-password',
  }

  // 如果当前已经在目标路由，不进行跳转
  if (route.path !== routeMap[index]) {
    router.push(routeMap[index])
  }
}

// 初始化时设置激活菜单
onMounted(() => {
  // 确保路由已经解析完成
  router.isReady().then(() => {
    setActiveMenu()
    console.log('初始化激活菜单:', activeMenu.value)
  })
})

// 监听路由变化
watch(
  () => route.path,
  () => {
    setActiveMenu()
  }
)

// 历史记录数据结构
const historyData = ref({
  coding: [],
  knowledge: [],
})
// 当前显示的历史记录
const activeHistory = ref('')

// 当前显示的历史记录
const historyList = computed(() => {
  return historyData.value[activeMenu.value] || []
})

// 侧边栏状态
const sidebarCollapsed = ref(false)

// 是否显示历史记录侧边栏
const showHistorySidebar = computed(() => {
  // 编码历史页面不显示侧边栏
  if (route.path === '/coding-history') return false
  return ['coding', 'knowledge'].includes(activeMenu.value)
})

// 是否可以创建新对话
const canCreateNewChat = computed(() => {
  if (!activeHistory.value) return true // 如果没有当前对话，可以创建

  const currentHistory = getCurrentHistoryData()
  if (!currentHistory || !currentHistory.data) return true // 如果没有数据，可以创建

  try {
    const dataObj = JSON.parse(currentHistory.data)
    // 有实际对话内容时才能创建新对话
    return dataObj.questList && dataObj.questList.length > 0
  } catch (e) {
    return true // 解析失败时允许创建
  }
})

// 从本地存储加载历史记录
const loadHistory = () => {
  if (!showHistorySidebar.value) return

  const savedData = localStorage.getItem('llmHistoryData')
  if (savedData) {
    try {
      const parsedData = JSON.parse(savedData)

      // 清理空数据
      Object.keys(parsedData).forEach((type) => {
        parsedData[type] = parsedData[type].filter((item) => {
          // 检查data是否存在且不为空
          if (!item.data) return false

          try {
            const dataObj = JSON.parse(item.data)
            // 保留有实际内容的记录（questList不为空数组）
            return dataObj.questList && dataObj.questList.length > 0
          } catch (e) {
            console.error('解析data失败:', e)
            return false // 解析失败视为无效数据
          }
        })
      })

      historyData.value = parsedData

      // 保存清理后的数据
      saveHistory()

      if (historyList.value.length > 0) {
        activeHistory.value = historyList.value[0].id
      }
    } catch (e) {
      console.error('解析历史记录失败:', e)
    }
  }
}

// 保存历史记录到本地存储
const saveHistory = () => {
  // 先清理空数据再保存
  const dataToSave = { ...historyData.value }
  Object.keys(dataToSave).forEach((type) => {
    dataToSave[type] = dataToSave[type].filter((item) => {
      // 保留有数据或有标题的记录
      return item.data || item.title
    })
  })

  localStorage.setItem('llmHistoryData', JSON.stringify(dataToSave))
}

// 添加一个清理空记录的公共方法
const cleanupEmptyHistory = () => {
  Object.keys(historyData.value).forEach((type) => {
    historyData.value[type] = historyData.value[type].filter((item) => {
      return item.data || item.title
    })
  })
  saveHistory()
}

// 切换菜单时更新历史记录
watch(
  () => activeMenu.value,
  (newVal) => {
    const currentHistoryList = historyData.value[newVal] || []
    if (currentHistoryList.length > 0) {
      activeHistory.value = currentHistoryList[0].id
      console.log('切换到菜单:', newVal, '历史记录:', currentHistoryList)
    } else {
      // 如果没有历史记录，清空当前选中的历史记录
      activeHistory.value = ''
      console.log('切换到菜单:', newVal, '没有历史记录')
    }
  },
  { immediate: true }
)

// 切换侧边栏状态
const toggleSidebar = () => {
  sidebarCollapsed.value = !sidebarCollapsed.value
}

// 开始新对话
const startNewChat = () => {
  // 如果不能创建新对话，直接返回
  if (!canCreateNewChat.value) {
    console.log('当前对话没有内容，不创建新对话')
    return
  }

  const type = activeMenu.value
  createNewChat(type)
}

// 创建新对话的具体实现
const createNewChat = (type) => {
  const newId = (type === 'coding' ? 'c' : 'k') + Date.now().toString()
  const newItem = {
    id: newId,
    title: '',
    time: new Date(),
    data: '',
  }

  // 添加到本地列表
  historyData.value[type].unshift(newItem)
  activeHistory.value = newId
  saveHistory()

  // 如果是编码页面，导航到新对话
  if (type === 'coding') {
    router.push({ path: '/bigModel', query: { historyId: newId } })
  }

  console.log('创建新对话:', newItem)
}

// 格式化日期
const formatDate = (date) => {
  const d = new Date(date)
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${d
    .getMinutes()
    .toString()
    .padStart(2, '0')}`
}

// 默认历史记录标题
const defaultHistoryTitle = (index) => {
  return activeMenu.value === 'coding'
    ? `新对话 ${index + 1}`
    : `新对话 ${index + 1}`
}

const saveChatContent = (id, content) => {
  const type = activeMenu.value
  const history = historyData.value[type]
  const index = history.findIndex((item) => item.id === id)

  if (index !== -1) {
    history[index].data = content

    // 如果没有标题，自动生成"编码案例X"格式的标题
    if (!history[index].title) {
      // 计算当前类型下的案例数量
      const caseCount =
        history.filter(
          (item) =>
            item.id !== id && // 排除当前记录
            item.title &&
            item.title.startsWith(type === 'coding' ? '编码案例' : '知识查询')
        ).length + 1

      // 根据菜单类型生成不同前缀的标题
      history[index].title =
        type === 'coding' ? `编码案例${caseCount}` : `知识查询${caseCount}`
    }

    history[index].time = new Date() // 更新最后修改时间
    saveHistory()
    // console.log('保存成功:', history[index]);
  }
}

// 处理历史记录选择
const handleHistorySelect = (id) => {
  const type = activeMenu.value
  const history = historyData.value[type]
  const selectedItem = history.find((item) => item.id === id)

  if (selectedItem) {
    activeHistory.value = id
    console.log('选中的历史记录:', selectedItem)
    // 触发路由变化（如果是coding页面）
    if (type === 'coding') {
      router.push({ path: '/bigModel', query: { historyId: id } })
    }
  }
}

// 获取当前选中的历史记录数据
const getCurrentHistoryData = () => {
  const type = activeMenu.value
  const history = historyData.value[type]
  return history.find((item) => item.id === activeHistory.value)
}

// 确认删除历史记录
const confirmDelete = (id) => {
  console.log('确认删除历史记录:', id)
  ElMessageBox.confirm('确定要删除这条历史记录吗?', '删除确认', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  })
    .then(() => {
      deleteHistory(id)
      ElMessage.success('删除成功')
    })
    .catch(() => {
      // 用户取消删除
    })
}

// 删除历史记录
const deleteHistory = (id) => {
  const type = activeMenu.value
  const history = historyData.value[type]

  // 删除指定记录
  historyData.value[type] = history.filter((item) => item.id !== id)

  // 如果删除的是当前选中的记录，自动选择最近的记录
  if (activeHistory.value === id) {
    activeHistory.value = historyData.value[type][0]?.id || ''
  }

  // 保存到本地存储
  saveHistory()
}

provide('historyMethods', {
  saveChatContent,
  getCurrentHistoryData: () => {
    const type = activeMenu.value
    return historyData.value[type].find(
      (item) => item.id === activeHistory.value
    )
  },
  activeHistory: computed(() => activeHistory.value),
})

defineExpose({
  saveChatContent,
  getCurrentHistoryData: () => {
    const type = activeMenu.value
    const history = historyData.value[type]
    const current = history.find((item) => item.id === activeHistory.value)
    console.log('暴露的当前历史数据:', current) // 调试日志
    return current
  },
  activeHistory,
})
</script>

<style lang="scss" scoped>
.sidebar-resizer {
  width: 4px;
  cursor: col-resize;
  background-color: #dcdfe6;
  transition: background-color 0.3s;
  position: relative;
  z-index: 2;
}

.sidebar-resizer:hover {
  background-color: #409eff;
}

.app-container {
  height: 100vh;
  display: flex;
  flex-direction: column;

  .app-header {
    height: 90px;
    border-bottom: 1px solid #e6e6e6;
    background-color: #fff;
    padding: 0;

    .header-content {
      display: flex;
      align-items: center;
      height: 100%;
      padding: 0 20px;
      justify-content: space-between; // 关键：让内容分布在两端
      align-items: center; // 垂直居中

      .header-logo {
        margin-right: 30px;

        .logo-image {
          height: 70px;
          object-fit: contain;
        }
      }

      .main-menu {
        flex: 1;
        border-bottom: none;

        .el-menu-item {
          font-size: 16px;
          padding: 0 20px;
          height: 60px;
          display: flex;
          align-items: center;

          .el-icon {
            margin-right: 8px;
          }
        }
      }
      // 新增：右侧部分样式
      .header-right-section {
        display: flex;
        align-items: center;
        gap: 10px; // 按钮和 logo 之间的间距

        .partner-logos {
          display: flex;
          align-items: center;
          gap: 15px;
          margin-right: 10px; // Logo 和按钮之间的间距

          .partner-logo {
            height: 30px;
            object-fit: contain;
          }
        }
        .logout-button {
          // // 让按钮变成圆形或正方形，只显示图标
          // width: 64px; // 设置一个固定的宽度和高度
          // height: 32px;
          // padding: 2px; // 减小内部填充，让图标更居中
          // border-radius: 10%; // 设置为圆形 (可选，也可以是 4px 或其他值变成圆角矩形)
          min-height: 32px; // Element Plus 按钮可能有最小高度，覆盖它

          // 可选：调整图标的大小
          .el-icon {
            // 如果图标本身太大或太小，可以调整
            font-size: 16px; // 或者使用 height/width: 1em;
          }

          // 可选：添加一个 tooltip 提示
          // 如果你想在鼠标悬停时显示“退出”文字提示，可以使用 el-tooltip
          // 这种情况下，按钮结构保持不变，但样式可能需要微调
          // .el-button__inner { // 不推荐直接修改内部类
          //   display: flex;
          //   align-items: center;
          //   justify-content: center;
          // }
        }
      }

      // .partner-logos {
      //   display: flex;
      //   align-items: center;
      //   gap: 15px;
      //   margin-left: 30px;

      //   .partner-logo {
      //     height: 30px;
      //     object-fit: contain;
      //   }
      // }
    }
  }

  .app-body {
    height: calc(100vh - 90px);
    position: relative; // 为背景图容器定位
    .history-sidebar {
      border-right: 1px solid #e6e6e6;
      background-color: #fff;
      display: flex;
      flex-direction: column;
      transition: width 0.3s ease;
      z-index: 1;
      .sidebar-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 16px;
        border-bottom: 1px solid #f0f0f0;

        h3 {
          margin: 0;
          font-size: 16px;
          color: #333;
        }

        .collapse-button {
          background-color: #f5f7fa;
          border: none;
        }
      }

      .history-list-container {
        flex: 1;
        overflow: hidden;

        .history-menu {
          border-right: none;

          .el-menu-item {
            height: 60px;
            margin: 4px 0px;
            border-radius: 4px;

            .history-title {
              flex: 1;
              white-space: nowrap;
              overflow: hidden;
              text-overflow: ellipsis;
            }

            .history-date {
              font-size: 12px;
              color: #999;
              margin-left: 8px;
            }
          }
        }
      }

      .new-chat-container {
        padding: 16px;
        border-top: 1px solid #faf4f4;

        .new-chat-button {
          width: 100%;
        }
      }
    }

    .sidebar-resizer {
      width: 1px;
      cursor: col-resize;
      background-color: #fff;
      transition: background-color 0.3s;
      position: relative;
      z-index: 1;
      // 确保它只在侧边栏显示时存在（虽然 v-if 会处理，但明确写出来更好）
      display: v-bind('showHistorySidebar ? "block" : "none"');
    }

    // 固定背景容器
    .background-container {
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      z-index: 0;
      overflow: hidden;
      pointer-events: none;
      .background-image {
        width: 100%;
        height: 100%;
        object-fit: cover;
        opacity: 0.3;
        transition: opacity 0.3s ease;
      }
    }

    .main-content {
      // padding: 20px;
      background-color: transparent;
      flex: 1;
      // 关键：移除固定的左右 padding，或者只保留上下 padding
      padding: 20px 0; // 上下 padding 保持，左右 padding 设为 0
      // 如果你想让 router-view 内容居中，可以在 router-view 外包一层容器并居中
      display: flex;
      flex-direction: column;
      align-items: center; // 这会让 router-view 内容在主内容区内水平居中
      overflow-x: auto; // 如果内容宽度过大，允许横向滚动
      position: relative; // 确保内容在背景之上
      z-index: 1;
      pointer-events: auto;
      // 如果你不想让 router-view 内容居中，而是让 router-view 本身占满，就移除 align-items: center;
    }
  }
}
.loading-state,
.error-state {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  color: var(--el-text-color-secondary);

  .el-icon {
    margin-right: 8px;
    font-size: 18px;
  }
}

.error-state {
  color: var(--el-color-error);
}

.history-menu {
  .el-menu-item {
    position: relative;
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-right: 70px; // 为两个按钮留出更多空间

    .edit-button,
    .delete-button {
      position: absolute;
      opacity: 0;
      transition: opacity 0.3s;
    }

    .edit-button {
      right: 40px; // 编辑按钮在删除按钮左侧
    }

    .delete-button {
      right: 8px;
    }

    &:hover .edit-button,
    &:hover .delete-button {
      opacity: 1;
    }
  }
}
.el-menu-item span {
  font-weight: 500 !important;
}
</style>
