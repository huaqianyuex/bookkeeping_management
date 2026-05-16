<template>
  <div class="statistics-page">
    <el-card shadow="never" class="header-card">
      <div class="header-content">
        <div class="header-info">
          <h2 class="page-title">数据统计</h2>
          <p class="page-desc">查看每月的收支概况与分类分析</p>
        </div>
        <el-date-picker v-model="currentMonth" type="month" placeholder="选择月份" value-format="YYYY-MM" @change="fetchData" class="month-picker" />
      </div>
    </el-card>

    <el-row :gutter="[16, 16]">
      <el-col :xs="24" :sm="8">
        <div class="summary-card income-card">
          <div class="summary-icon-wrap"><el-icon><ArrowDown /></el-icon></div>
          <div class="summary-body"><span class="summary-label">月度收入</span><div class="summary-value"><span class="currency">¥</span><span class="number">{{ formatMoney(monthlyData.totalIncome) }}</span></div><div class="summary-trend"><span>来自 {{ incomeStats.length }} 个分类</span></div></div>
        </div>
      </el-col>
      <el-col :xs="24" :sm="8">
        <div class="summary-card expense-card">
          <div class="summary-icon-wrap"><el-icon><ArrowUp /></el-icon></div>
          <div class="summary-body"><span class="summary-label">月度支出</span><div class="summary-value"><span class="currency">¥</span><span class="number">{{ formatMoney(monthlyData.totalExpense) }}</span></div><div class="summary-trend"><span>来自 {{ expenseStats.length }} 个分类</span></div></div>
        </div>
      </el-col>
      <el-col :xs="24" :sm="8">
        <div class="summary-card balance-card">
          <div class="summary-icon-wrap"><el-icon><Wallet /></el-icon></div>
          <div class="summary-body"><span class="summary-label">月度结余</span><div class="summary-value" :class="balanceTrend"><span class="currency">¥</span><span class="number">{{ formatMoney(monthlyData.balance) }}</span></div><div class="summary-trend"><span :class="balanceTrend">{{ balanceText }}</span></div></div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="[16, 16]">
      <el-col :xs="24" :lg="12">
        <el-card shadow="never" class="detail-card">
          <template #header><div class="detail-header"><div class="detail-header-left"><div class="detail-icon expense-dot"></div><span>支出分类统计</span></div><el-tag type="danger" effect="plain" size="small">¥{{ formatMoney(monthlyData.totalExpense) }}</el-tag></div></template>
          <div v-if="expenseStats.length === 0" class="empty-chart"><el-icon><PieChart /></el-icon><span>暂无支出数据</span></div>
          <div v-else class="stats-list">
            <div v-for="item in sortedExpenseStats" :key="item.categoryId" class="stats-item">
              <div class="stats-item-header"><span class="stats-cat-name">{{ item.categoryName }}</span><span class="stats-amount">¥{{ formatMoney(item.amount) }} <span class="stats-percentage">{{ item.percentage.toFixed(1) }}%</span></span></div>
              <el-progress :percentage="Math.min(item.percentage, 100)" :stroke-width="8" color="#FF4D4F" :show-text="false" class="stats-progress" />
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :lg="12">
        <el-card shadow="never" class="detail-card">
          <template #header><div class="detail-header"><div class="detail-header-left"><div class="detail-icon income-dot"></div><span>收入分类统计</span></div><el-tag type="success" effect="plain" size="small">¥{{ formatMoney(monthlyData.totalIncome) }}</el-tag></div></template>
          <div v-if="incomeStats.length === 0" class="empty-chart"><el-icon><PieChart /></el-icon><span>暂无收入数据</span></div>
          <div v-else class="stats-list">
            <div v-for="item in sortedIncomeStats" :key="item.categoryId" class="stats-item">
              <div class="stats-item-header"><span class="stats-cat-name">{{ item.categoryName }}</span><span class="stats-amount">¥{{ formatMoney(item.amount) }} <span class="stats-percentage">{{ item.percentage.toFixed(1) }}%</span></span></div>
              <el-progress :percentage="Math.min(item.percentage, 100)" :stroke-width="8" color="#52C41A" :show-text="false" class="stats-progress" />
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import dayjs from 'dayjs'
import { statisticsApi } from '@/api'
import type { MonthlyStatsVO, CategoryStatVO } from '@/types'
import { ArrowDown, ArrowUp, Wallet, PieChart } from '@element-plus/icons-vue'

const currentMonth = ref(dayjs().format('YYYY-MM'))
const monthlyData = reactive<MonthlyStatsVO>({ year: dayjs().year(), month: dayjs().month() + 1, totalIncome: 0, totalExpense: 0, balance: 0 })
const expenseStats = ref<CategoryStatVO[]>([])
const incomeStats = ref<CategoryStatVO[]>([])

const sortedExpenseStats = computed(() => [...expenseStats.value].sort((a, b) => b.amount - a.amount))
const sortedIncomeStats = computed(() => [...incomeStats.value].sort((a, b) => b.amount - a.amount))
const balanceTrend = computed(() => monthlyData.balance > 0 ? 'tp' : monthlyData.balance < 0 ? 'tn' : '')
const balanceText = computed(() => monthlyData.balance > 0 ? '收大于支，有结余' : monthlyData.balance < 0 ? '支出超过收入' : '收支平衡')
const formatMoney = (v: number) => v.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

const fetchData = async () => {
  const d = dayjs(currentMonth.value); const y = d.year(); const m = d.month() + 1
  try {
    const [mr, er, ir] = await Promise.all([
      statisticsApi.getMonthly(y, m),
      statisticsApi.getCategory({ year: y, month: m, type: 0 }),
      statisticsApi.getCategory({ year: y, month: m, type: 1 })
    ])
    Object.assign(monthlyData, mr.data); expenseStats.value = er.data; incomeStats.value = ir.data
  } catch {}
}
onMounted(() => { fetchData() })
defineExpose({ refreshData: fetchData })
</script>

<style scoped>
.statistics-page { display: flex; flex-direction: column; gap: 22px; }
@media (max-width: 767px) { .statistics-page { gap: 18px; } }
.header-card { flex-shrink: 0; }
@media (max-width: 767px) { .header-card { margin-bottom: 2px; } }
.header-content { display: flex; justify-content: space-between; align-items: center; gap: 16px; }
.page-title { font-size: 20px; font-weight: 700; color: var(--text-primary); }
@media (max-width: 767px) { .page-title { font-size: 17px; } .page-desc { font-size: 12px; } }
.page-desc { font-size: 13px; color: var(--text-tertiary); margin-top: 4px; }
.month-picker { width: 200px; }
@media (max-width: 767px) { .month-picker { width: 100%; } .header-content { flex-wrap: wrap; } }

.summary-card { display: flex; align-items: center; gap: 16px; padding: 20px; background: #fff; border-radius: 14px; box-shadow: 0 2px 8px rgba(0,0,0,.06); border: 1px solid rgba(0,0,0,.03); transition: all .2s; }
.summary-card:active { transform: scale(.98); }
.summary-icon-wrap { width: 48px; height: 48px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 22px; flex-shrink: 0; }
.income-card .summary-icon-wrap { background: rgba(82,196,26,.12); color: var(--success); }
.expense-card .summary-icon-wrap { background: rgba(255,77,79,.12); color: var(--danger); }
.balance-card .summary-icon-wrap { background: rgba(91,127,255,.12); color: var(--primary); }
.summary-body { flex: 1; }
.summary-label { font-size: 12px; color: var(--text-tertiary); font-weight: 500; letter-spacing: .5px; }
.summary-value { margin: 4px 0; display: flex; align-items: baseline; gap: 2px; }
.summary-value .currency { font-size: 14px; font-weight: 600; color: var(--text-secondary); }
.summary-value .number { font-size: 24px; font-weight: 800; color: var(--text-primary); letter-spacing: -1px; font-variant-numeric: tabular-nums; }
@media (max-width: 767px) { .summary-value .number { font-size: 20px; } }
.tp .number, .tp .currency { color: var(--success) !important; }
.tn .number, .tn .currency { color: var(--danger) !important; }
.summary-trend { font-size: 12px; color: var(--text-tertiary); }
.summary-trend .tp { color: var(--success); font-weight: 500; }
.summary-trend .tn { color: var(--danger); font-weight: 500; }

.detail-card { height: 100%; }
.detail-header { display: flex; justify-content: space-between; align-items: center; }
.detail-header-left { display: flex; align-items: center; gap: 8px; font-size: 15px; font-weight: 600; color: var(--text-primary); }
.detail-icon { width: 10px; height: 10px; border-radius: 50%; }
.expense-dot { background: var(--danger); box-shadow: 0 0 6px rgba(255,77,79,.3); }
.income-dot { background: var(--success); box-shadow: 0 0 6px rgba(82,196,26,.3); }

.stats-list { display: flex; flex-direction: column; gap: 16px; }
.stats-item { display: flex; flex-direction: column; gap: 6px; }
.stats-item-header { display: flex; justify-content: space-between; align-items: center; }
.stats-cat-name { font-size: 14px; font-weight: 500; color: var(--text-primary); }
.stats-amount { font-size: 14px; font-weight: 700; color: var(--text-primary); font-variant-numeric: tabular-nums; white-space: nowrap; }
.stats-percentage { font-size: 12px; font-weight: 500; color: var(--text-tertiary); margin-left: 4px; }
.stats-progress { flex: 1; }

.empty-chart { display: flex; flex-direction: column; align-items: center; gap: 12px; padding: 40px 0; color: var(--text-tertiary); }
.empty-chart .el-icon { font-size: 40px; color: var(--border); }
</style>
