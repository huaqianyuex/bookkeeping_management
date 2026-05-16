<template>
  <div class="records-page">
    <!-- Filters -->
    <el-card shadow="never" class="search-card">
      <div class="filter-bar">
        <el-date-picker v-model="queryParams.month" type="month" placeholder="月份" value-format="YYYY-MM" clearable class="filter-item" @change="fetchRecords" />
        <el-select v-model="queryParams.categoryId" placeholder="全部分类" clearable class="filter-item" @change="fetchRecords">
          <el-option v-for="item in categories" :key="item.id" :label="item.name" :value="item.id" />
        </el-select>
        <el-button type="primary" class="add-btn-mobile" @click="handleAdd"><el-icon><Plus /></el-icon><span class="desktop-label">添加记录</span></el-button>
      </div>
    </el-card>

    <!-- Stats -->
    <el-row :gutter="12" class="stats-row">
      <el-col :xs="24" :sm="8"><div class="stat-card income"><div class="stat-icon"><el-icon><Top /></el-icon></div><div class="stat-info"><span class="stat-label">收入</span><span class="stat-value">¥{{ formatMoney(incomeTotal) }}</span></div></div></el-col>
      <el-col :xs="24" :sm="8"><div class="stat-card expense"><div class="stat-icon"><el-icon><Bottom /></el-icon></div><div class="stat-info"><span class="stat-label">支出</span><span class="stat-value">¥{{ formatMoney(expenseTotal) }}</span></div></div></el-col>
      <el-col :xs="24" :sm="8"><div class="stat-card balance"><div class="stat-icon"><el-icon><Money /></el-icon></div><div class="stat-info"><span class="stat-label">结余</span><span class="stat-value" :class="balanceClass">¥{{ formatMoney(balanceTotal) }}</span></div></div></el-col>
    </el-row>

    <!-- Desktop Table -->
    <el-card shadow="never" class="table-card desktop-table">
      <el-table :data="tableData" stripe empty-text="暂无记录">
        <el-table-column prop="recordDate" label="日期" width="110" />
        <el-table-column label="分类" width="120"><template #default="{ row }"><div class="cat-cell"><div class="cat-dot" :style="{ background: row.categoryType === 1 ? 'var(--success)' : 'var(--danger)' }"></div>{{ row.categoryName }}</div></template></el-table-column>
        <el-table-column label="类型" width="80" align="center"><template #default="{ row }"><el-tag :type="row.categoryType === 1 ? 'success' : 'danger'" effect="plain" size="small" round>{{ row.categoryType === 1 ? '收入' : '支出' }}</el-tag></template></el-table-column>
        <el-table-column label="金额" width="140" align="right"><template #default="{ row }"><span class="amt" :style="{ color: row.categoryType === 1 ? 'var(--success)' : 'var(--danger)' }">{{ row.categoryType === 1 ? '+' : '-' }} ¥{{ row.amount.toFixed(2) }}</span></template></el-table-column>
        <el-table-column prop="remark" label="备注" min-width="120"><template #default="{ row }"><span class="rmk">{{ row.remark || '-' }}</span></template></el-table-column>
        <el-table-column label="操作" width="150" fixed="right" align="center">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handleEdit(row)"><el-icon><Edit /></el-icon>编辑</el-button>
            <el-divider direction="vertical" />
            <el-button type="danger" link size="small" @click="handleDelete(row.id)"><el-icon><Delete /></el-icon>删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="page-wrap"><el-pagination v-model:current-page="queryParams.page" v-model:page-size="queryParams.size" :page-sizes="[10,20,50]" :total="total" layout="total, sizes, prev, pager, next" background @size-change="fetchRecords" @current-change="fetchRecords" /></div>
    </el-card>

    <!-- Mobile Card List -->
    <div class="mobile-list mobile-only">
      <div v-for="item in tableData" :key="item.id" class="record-card" @click="handleEdit(item)">
        <div class="card-top">
          <div class="card-left">
            <div class="card-cat">
              <div class="card-dot" :style="{ background: item.categoryType === 1 ? 'var(--success)' : 'var(--danger)' }"></div>
              <span class="card-cat-name">{{ item.categoryName }}</span>
              <el-tag :type="item.categoryType === 1 ? 'success' : 'danger'" effect="plain" size="small" round>{{ item.categoryType === 1 ? '收入' : '支出' }}</el-tag>
            </div>
            <span class="card-date">{{ item.recordDate }}</span>
          </div>
          <div class="card-amount" :style="{ color: item.categoryType === 1 ? 'var(--success)' : 'var(--danger)' }">
            {{ item.categoryType === 1 ? '+' : '-' }} ¥{{ item.amount.toFixed(2) }}
          </div>
        </div>
        <div class="card-bottom">
          <span class="card-remark">{{ item.remark || '无备注' }}</span>
          <div class="card-actions" @click.stop>
            <el-button type="primary" link size="small" @click.stop="handleEdit(item)"><el-icon><Edit /></el-icon></el-button>
            <el-button type="danger" link size="small" @click.stop="handleDelete(item.id)"><el-icon><Delete /></el-icon></el-button>
          </div>
        </div>
      </div>
      <div v-if="tableData.length === 0" class="empty-state"><el-icon><FolderRemove /></el-icon><span>暂无记录</span></div>
      <div class="page-wrap mobile-page"><el-pagination v-model:current-page="queryParams.page" v-model:page-size="queryParams.size" :total="total" layout="prev, pager, next" small background @current-change="fetchRecords" /></div>
    </div>

    <!-- Dialog -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="92%" max-width="520px" top="5vh" :close-on-click-modal="false" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" size="large">
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="类型"><el-radio-group v-model="type" class="type-group"><el-radio-button :label="0">支出</el-radio-button><el-radio-button :label="1">收入</el-radio-button></el-radio-group></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="日期" prop="recordDate"><el-date-picker v-model="form.recordDate" type="date" placeholder="选择日期" value-format="YYYY-MM-DD" class="full-width" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="分类" prop="categoryId"><el-select v-model="form.categoryId" placeholder="请选择分类" class="full-width"><el-option v-for="item in filteredCategories" :key="item.id" :label="item.name" :value="item.id" /></el-select></el-form-item>
        <el-form-item label="金额" prop="amount"><el-input-number v-model="form.amount" :min="0.01" :precision="2" :step="10" class="full-width" controls-position="right" placeholder="金额" /></el-form-item>
        <el-form-item label="备注" prop="remark"><el-input v-model="form.remark" type="textarea" :rows="3" placeholder="选填" maxlength="200" show-word-limit /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleSubmit">{{ isEdit ? '保存修改' : '添加记录' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import dayjs from 'dayjs'
import { recordApi, categoryApi } from '@/api'
import type { RecordVO, CategoryVO, RecordDTO, CategoryType } from '@/types'
import { Plus, Edit, Delete, Top, Bottom, Money, FolderRemove } from '@element-plus/icons-vue'

const tableData = ref<RecordVO[]>([])
const categories = ref<CategoryVO[]>([])
const total = ref(0)
const dialogVisible = ref(false)
const submitLoading = ref(false)
const formRef = ref<FormInstance>()
const isEdit = ref(false)
const editId = ref<number | null>(null)
const type = ref<CategoryType>(0)

const queryParams = reactive({ page: 1, size: 10, categoryId: undefined as number | undefined, month: dayjs().format('YYYY-MM') })
const form = reactive<RecordDTO>({ categoryId: 0, amount: 0, remark: '', recordDate: dayjs().format('YYYY-MM-DD') })
const rules: FormRules = { categoryId: [{ required: true, message: '请选择分类', trigger: 'change' }], amount: [{ required: true, message: '请输入金额', trigger: 'blur' }], recordDate: [{ required: true, message: '请选择日期', trigger: 'change' }] }

const dialogTitle = computed(() => isEdit.value ? '编辑记录' : '添加记录')
const filteredCategories = computed(() => categories.value.filter(i => i.type === type.value))
const incomeTotal = computed(() => tableData.value.filter(r => r.categoryType === 1).reduce((s, r) => s + r.amount, 0))
const expenseTotal = computed(() => tableData.value.filter(r => r.categoryType === 0).reduce((s, r) => s + r.amount, 0))
const balanceTotal = computed(() => incomeTotal.value - expenseTotal.value)
const balanceClass = computed(() => balanceTotal.value >= 0 ? 'bp' : 'bn')
const formatMoney = (v: number) => v.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

const fetchCategories = async () => { try { const r = await categoryApi.getList(); categories.value = r.data } catch {} }
const fetchRecords = async () => {
  try {
    const p = { ...queryParams }
    if (!p.month) delete (p as any).month
    if (!p.categoryId) delete (p as any).categoryId
    const r = await recordApi.getPage(p); tableData.value = r.data.records; total.value = r.data.total
  } catch {}
}

const handleAdd = () => { isEdit.value = false; editId.value = null; type.value = 0; Object.assign(form, { categoryId: 0, amount: 0, remark: '', recordDate: dayjs().format('YYYY-MM-DD') }); dialogVisible.value = true }
const handleEdit = (row: RecordVO) => { isEdit.value = true; editId.value = row.id; type.value = row.categoryType; Object.assign(form, { categoryId: row.categoryId, amount: row.amount, remark: row.remark || '', recordDate: row.recordDate }); dialogVisible.value = true }
const handleDelete = (id: number) => {
  ElMessageBox.confirm('确定要删除这条记录吗？', '提示', { confirmButtonText: '确定删除', cancelButtonText: '取消', type: 'warning', roundButton: true })
    .then(async () => { try { await recordApi.delete(id); ElMessage.success('删除成功'); fetchRecords() } catch {} }).catch(() => {})
}
const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    submitLoading.value = true
    try {
      if (isEdit.value && editId.value) { await recordApi.update(editId.value, form); ElMessage.success('编辑成功') }
      else { await recordApi.add(form); ElMessage.success('添加成功') }
      dialogVisible.value = false; fetchRecords()
    } catch {} finally { submitLoading.value = false }
  })
}

watch(type, () => { form.categoryId = 0 })
onMounted(() => { fetchCategories(); fetchRecords() })
defineExpose({ refreshData: fetchRecords })
</script>

<style scoped>
.records-page { display: flex; flex-direction: column; gap: 20px; }
@media (max-width: 767px) { .records-page { gap: 18px; } }

/* Filters */
.filter-bar { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.filter-item { width: 150px; }
.add-btn-mobile { margin-left: auto; }
@media (max-width: 767px) {
  .filter-bar { gap: 8px; }
  .filter-item { width: calc(50% - 4px); flex: 1; }
  .add-btn-mobile { width: 100%; margin-left: 0; height: 40px; font-size: 14px; }
  .desktop-label { display: none; }
}

/* Stats */
.stats-row { margin-bottom: 0; }
@media (max-width: 767px) { .stats-row .el-col { margin-bottom: 12px; } }
.stat-card { display: flex; align-items: center; gap: 14px; padding: 16px 18px; background: #fff; border-radius: 14px; box-shadow: 0 2px 8px rgba(0,0,0,.06); border: 1px solid rgba(0,0,0,.03); }
.stat-icon { width: 44px; height: 44px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 20px; flex-shrink: 0; }
.stat-card.income .stat-icon { background: rgba(82,196,26,.12); color: var(--success); }
.stat-card.expense .stat-icon { background: rgba(255,77,79,.12); color: var(--danger); }
.stat-card.balance .stat-icon { background: rgba(91,127,255,.12); color: var(--primary); }
.stat-info { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.stat-label { font-size: 12px; color: var(--text-tertiary); font-weight: 500; letter-spacing: .3px; }
.stat-value { font-size: 20px; font-weight: 700; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
@media (max-width: 767px) { .stat-value { font-size: 18px; } }
.bp { color: var(--success) !important; }
.bn { color: var(--danger) !important; }

/* Desktop Table */
.desktop-table { display: none; }
@media (min-width: 768px) { .desktop-table { display: block; } }

.cat-cell { display: flex; align-items: center; gap: 6px; }
.cat-dot { width: 8px; height: 8px; border-radius: 50%; }
.amt { font-weight: 700; font-variant-numeric: tabular-nums; }
.rmk { color: var(--text-secondary); font-size: 13px; }
.page-wrap { display: flex; justify-content: flex-end; padding-top: 16px; }

/* Mobile Card List */
.mobile-list { display: none; flex-direction: column; gap: 12px; padding-bottom: 8px; }
@media (max-width: 767px) { .mobile-list { display: flex; } }

.record-card { background: #fff; border-radius: 14px; padding: 16px 18px; box-shadow: 0 2px 8px rgba(0,0,0,.06); cursor: pointer; transition: all .2s; border: 1px solid rgba(0,0,0,.03); }
.record-card:active { transform: scale(.97); background: #f8f9fb; }
.card-top { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px; }
.card-left { display: flex; flex-direction: column; gap: 6px; }
.card-cat { display: flex; align-items: center; gap: 8px; }
.card-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.card-cat-name { font-size: 16px; font-weight: 600; color: var(--text-primary); }
.card-date { font-size: 12px; color: var(--text-tertiary); }
.card-amount { font-size: 20px; font-weight: 800; white-space: nowrap; letter-spacing: -.5px; }
.card-bottom { display: flex; justify-content: space-between; align-items: center; padding-top: 10px; border-top: 1px solid var(--border-light); }
.card-remark { font-size: 13px; color: var(--text-tertiary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 60%; }
.card-actions { display: flex; gap: 8px; }
.card-actions .el-button { font-size: 18px; min-width: 36px; height: 36px; }

/* Mobile Pagination */
@media (max-width: 767px) { .mobile-page { justify-content: center; } }

/* Empty */
.empty-state { display: flex; flex-direction: column; align-items: center; gap: 12px; padding: 40px 0; color: var(--text-tertiary); }
.empty-state .el-icon { font-size: 40px; color: var(--border); }

.full-width { width: 100%; }
.type-group .el-radio-button__inner { min-width: 80px; }
</style>
