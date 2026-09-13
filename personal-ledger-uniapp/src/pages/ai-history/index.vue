<template>
  <view class="history-page">
    <!-- 状态栏占位 -->
    <view class="status-bar" :style="{ height: statusBarHeight + 'px' }"></view>

    <!-- 顶部栏 -->
    <view class="header">
      <view class="header-left" @click="uni.navigateBack()">
        <text class="header-icon">←</text>
      </view>
      <text class="title">历史对话</text>
      <view class="header-right" />
    </view>

    <!-- 搜索 + 排序 -->
    <view class="toolbar">
      <input
        class="search-input"
        v-model="keyword"
        placeholder="搜索标题或内容"
        confirm-type="search"
        @confirm="fetchList(1)"
      />
      <view class="sort-tabs">
        <text
          class="sort-tab"
          :class="{ 'sort-tab--active': sort === 'updated' }"
          @click="sort = 'updated'"
        >最近更新</text>
        <text
          class="sort-tab"
          :class="{ 'sort-tab--active': sort === 'created' }"
          @click="sort = 'created'"
        >创建时间</text>
      </view>
    </view>

    <!-- 列表 -->
    <scroll-view
      class="list"
      scroll-y
      @scrolltolower="onReachBottom"
      refresher-enabled
      :refresher-triggered="refreshing"
      @refresherrefresh="onRefresh"
    >
      <view v-if="items.length === 0 && !listLoading" class="empty">
        <text class="empty-icon">📋</text>
        <text class="empty-text">暂无历史对话</text>
      </view>

      <view
        v-for="item in items"
        :key="item.id"
        class="session-item"
        @click="openSession(item)"
        @longpress="onLongPress(item)"
      >
        <view class="session-top">
          <text class="session-title">{{ item.title || '新对话' }}</text>
          <text class="session-time">{{ formatRelative(item.updatedAt) }}</text>
        </view>
        <text class="session-preview">{{ item.preview || '（暂无消息）' }}</text>
        <text class="session-count">{{ item.messageCount }}条消息</text>
      </view>

      <view v-if="hasMore && items.length > 0" class="load-more" @click="fetchList(page + 1, true)">
        <text class="load-more-text">{{ listLoading ? '加载中...' : '加载更多' }}</text>
      </view>

      <!-- 底部给自定义 TabBar 留出空间，避免最后一条被遮挡 -->
      <view class="list-bottom-space" />
    </scroll-view>
  </view>
</template>

<script setup>
import { ref, watch } from 'vue'
import { onLoad, onShow } from '@dcloudio/uni-app'
import { listSessions, renameSession, deleteSession, getMessages } from '@/api/ai.js'

const statusBarHeight = ref(20)
const keyword = ref('')
const sort = ref('updated')
const items = ref([])
const page = ref(1)
const hasMore = ref(false)
const listLoading = ref(false)
const refreshing = ref(false)
const PAGE_SIZE = 20

// 格式化相对时间
function formatRelative(ts) {
  const diff = Date.now() - ts
  const min = Math.floor(diff / 60000)
  if (min < 1) return '刚刚'
  if (min < 60) return `${min}分钟前`
  const hour = Math.floor(min / 60)
  if (hour < 24) return `${hour}小时前`
  const day = Math.floor(hour / 24)
  if (day < 7) return `${day}天前`
  const d = new Date(ts)
  return `${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

// 拉取列表
async function fetchList(p = 1, append = false) {
  listLoading.value = true
  try {
    const res = await listSessions({
      keyword: keyword.value || undefined,
      sort: sort.value,
      order: 'desc',
      page: p,
      size: PAGE_SIZE
    })
    const newItems = res.items || []
    if (append) {
      items.value = [...items.value, ...newItems]
    } else {
      items.value = newItems
    }
    page.value = p
    hasMore.value = p * PAGE_SIZE < (res.total || 0)
  } catch (e) {
    console.error('加载会话列表失败:', e)
    uni.showToast({ title: '加载失败', icon: 'none' })
  } finally {
    listLoading.value = false
  }
}

// 搜索防抖
let searchTimer = null
watch(keyword, () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => fetchList(1), 300)
})

// 排序变化时刷新
watch(sort, () => fetchList(1))

// 下拉刷新
async function onRefresh() {
  refreshing.value = true
  await fetchList(1)
  refreshing.value = false
}

// 触底加载
function onReachBottom() {
  if (hasMore.value && !listLoading.value) {
    fetchList(page.value + 1, true)
  }
}

// 打开会话
async function openSession(item) {
  // 携带 sessionId 跳回 ai-chat 页
  uni.navigateTo({
    url: '/pages/ai-chat/index?sessionId=' + item.id
  })
}

// 长按操作
function onLongPress(item) {
  uni.showActionSheet({
    itemList: ['重命名', '删除'],
    success: (res) => {
      if (res.tapIndex === 0) {
        handleRename(item)
      } else if (res.tapIndex === 1) {
        handleDelete(item)
      }
    }
  })
}

// 重命名
function handleRename(item) {
  uni.showModal({
    title: '重命名',
    editable: true,
    placeholderText: '输入新标题',
    content: item.title || '',
    success: async (res) => {
      if (res.confirm && res.content && res.content.trim()) {
        try {
          await renameSession(item.id, res.content.trim().slice(0, 50))
          uni.showToast({ title: '已重命名', icon: 'success' })
          fetchList(1)
        } catch {
          uni.showToast({ title: '重命名失败', icon: 'none' })
        }
      }
    }
  })
}

// 删除
function handleDelete(item) {
  uni.showModal({
    title: '删除该对话？',
    content: `「${item.title || '新对话'}」及其全部消息将被永久移除，无法恢复。`,
    confirmColor: '#C43D3D',
    success: async (res) => {
      if (res.confirm) {
        try {
          await deleteSession(item.id)
          uni.showToast({ title: '已删除', icon: 'success' })
          fetchList(1)
        } catch {
          uni.showToast({ title: '删除失败', icon: 'none' })
        }
      }
    }
  })
}

onLoad(() => {
  const systemInfo = uni.getSystemInfoSync()
  statusBarHeight.value = systemInfo.statusBarHeight || 20
})

onShow(() => {
  fetchList(1)
})
</script>

<style scoped>
.history-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--color-bg);
}

.list-bottom-space {
  height: calc(240rpx + env(safe-area-inset-bottom));
  flex-shrink: 0;
}

.status-bar {
  width: 100%;
  background-color: var(--color-bg);
}

/* 设计稿04 同风格顶栏：透明底 + 大标题 */
.header {
  height: 96rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--space-2xl);
  background: transparent;
  border-bottom: none;
}

.header-left,
.header-right {
  width: 72rpx;
  height: 72rpx;
  border-radius: var(--radius-full);
  background: var(--color-surface);
  box-shadow: var(--shadow-xs);
  display: flex;
  align-items: center;
  justify-content: center;
}

.header-icon {
  font-size: var(--font-lg);
  color: var(--color-text-secondary);
}

.title {
  color: var(--color-text-heading);
  font-size: 44rpx;
  font-weight: var(--weight-extrabold);
}

/* 设计稿08：灰底胶囊搜索框 */
.toolbar {
  padding: var(--space-sm) var(--space-2xl) var(--space-md);
  background: transparent;
  border-bottom: none;
}

.search-input {
  height: 88rpx;
  background: var(--color-surface-raised);
  border-radius: var(--radius-full);
  padding: 0 var(--space-xl);
  font-size: var(--font-base);
  margin-bottom: var(--space-md);
}

.sort-tabs {
  display: flex;
  gap: var(--space-lg);
}

.sort-tab {
  font-size: var(--font-sm);
  color: var(--color-text-tertiary);
  padding-bottom: var(--space-xs);
}

.sort-tab--active {
  color: var(--color-text-heading);
  font-weight: var(--weight-semibold);
  border-bottom: 4rpx solid var(--color-accent);
}

.list {
  flex: 1;
  padding: var(--space-md) var(--space-lg);
}

.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 200rpx;
}

.empty-icon {
  font-size: 80rpx;
  margin-bottom: var(--space-xl);
}

.empty-text {
  font-size: var(--font-base);
  color: var(--color-text-tertiary);
}

.session-item {
  background: var(--color-surface);
  border: none;
  border-radius: var(--radius-2xl);
  box-shadow: var(--shadow-card);
  padding: var(--space-xl);
  margin-bottom: var(--space-md);
}

.session-item:active {
  background: var(--color-surface-raised);
}

.session-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-sm);
}

.session-title {
  font-size: var(--font-base);
  font-weight: var(--weight-semibold);
  color: var(--color-text);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-right: var(--space-md);
}

.session-time {
  font-size: var(--font-xs);
  color: var(--color-text-tertiary);
  flex-shrink: 0;
}

.session-preview {
  font-size: var(--font-sm);
  color: var(--color-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: var(--space-xs);
}

.session-count {
  font-size: var(--font-xs);
  color: var(--color-text-tertiary);
}

.load-more {
  padding: var(--space-lg);
  text-align: center;
}

.load-more-text {
  font-size: var(--font-sm);
  color: var(--color-text-tertiary);
}
</style>
