<template>
  <view class="history-page">
    <!-- 状态栏占位 -->
    <view class="status-bar" :style="{ height: statusBarHeight + 'px' }"></view>

    <!-- 顶部栏 -->
    <view class="header">
      <view class="header-left" @click="uni.navigateBack()">
        <AppIcon name="back" :size="36" />
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
      <!-- 排序切换：与全局选中态语言统一（灰底胶囊 + 墨黑选中） -->
      <view class="sort-tabs">
        <view class="sort-tab" :class="{ 'sort-tab--active': sort === 'updated' }" @click="sort = 'updated'">
          <text class="sort-tab-text" :class="{ active: sort === 'updated' }">最近更新</text>
        </view>
        <view class="sort-tab" :class="{ 'sort-tab--active': sort === 'created' }" @click="sort = 'created'">
          <text class="sort-tab-text" :class="{ active: sort === 'created' }">创建时间</text>
        </view>
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
      <!-- 首次加载先出骨架，避免白屏一闪 -->
      <view v-if="items.length === 0 && listLoading" class="skeleton-list">
        <skeleton-card :lines="2" style="margin-bottom: 16rpx;"></skeleton-card>
        <skeleton-card :lines="2" style="margin-bottom: 16rpx;"></skeleton-card>
        <skeleton-card :lines="2"></skeleton-card>
      </view>

      <!-- 加载失败 ≠ 没有对话 -->
      <empty-state
        v-else-if="loadError && items.length === 0"
        mode="error"
        title="对话加载失败"
        description="网络似乎不太顺畅，稍后再试试"
      >
        <template #action>
          <view class="empty-btn" @click="fetchList(1)">
            <text class="empty-btn-text">重新加载</text>
          </view>
        </template>
      </empty-state>

      <view v-else-if="items.length === 0" class="empty">
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
import SkeletonCard from '@/components/SkeletonCard.vue'
import EmptyState from '@/components/EmptyState.vue'
import AppIcon from '@/components/AppIcon.vue'

const statusBarHeight = ref(20)
const keyword = ref('')
const sort = ref('updated')
const items = ref([])
const page = ref(1)
const hasMore = ref(false)
const listLoading = ref(false)
const loadError = ref(false)
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
    loadError.value = false
  } catch (e) {
    console.error('加载会话列表失败:', e)
    // 首屏失败标记错误态（追加加载失败保持原列表，仅 toast）
    if (p === 1) loadError.value = true
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
    // 原生弹窗只接受字面量色值，取 --color-danger 令牌的实际值
    confirmColor: '#E5484D',
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
  height: var(--page-bottom-space);
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

.title {
	color: var(--color-text-heading);
	font-size: var(--font-2xl);
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

/* 排序切换：灰底胶囊 + 墨黑选中，与全局选中态语言一致 */
.sort-tabs {
	display: inline-flex;
	align-items: center;
	background-color: var(--color-surface-raised);
	border-radius: var(--radius-full);
	padding: var(--space-2xs);
	gap: var(--space-2xs);
}

.sort-tab {
	padding: var(--space-xs) var(--space-lg);
	border-radius: var(--radius-full);
	transition: background-color var(--transition-fast);
}

.sort-tab--active {
	background: var(--color-primary);
}

.sort-tab-text {
	font-size: var(--font-sm);
	color: var(--color-text-secondary);
	font-weight: var(--weight-medium);
}

.sort-tab-text.active {
	color: var(--color-text-inverse);
	font-weight: var(--weight-semibold);
}

.list {
  flex: 1;
  padding: var(--space-md) var(--space-lg);
}

.skeleton-list {
  padding-top: var(--space-md);
}

.empty-btn {
  display: inline-flex;
  align-items: center;
  background: var(--color-accent);
  padding: var(--space-lg) var(--space-3xl);
  border-radius: var(--radius-full);
  box-shadow: var(--shadow-accent);
  transition: opacity var(--transition-fast);
}

.empty-btn:active {
  opacity: 0.88;
}

.empty-btn-text {
  color: var(--color-text-heading);
  font-size: var(--font-base);
  font-weight: var(--weight-semibold);
}

.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 200rpx;
}

.empty-icon {
  font-size: var(--font-5xl);
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
