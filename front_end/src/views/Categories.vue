<template>
  <div class="categories-page">
    <el-row :gutter="[16, 16]">
      <el-col :xs="24" :md="12">
        <el-card shadow="never" class="category-card">
          <template #header>
            <div class="card-header">
              <div class="header-left"><div class="header-icon expense-icon"><el-icon><Bottom /></el-icon></div><span class="header-title">支出分类</span></div>
              <el-button type="primary" size="small" @click="handleAdd(0)"><el-icon><Plus /></el-icon><span class="desktop-label">添加支出</span></el-button>
            </div>
          </template>
          <div v-if="expenseCategories.length === 0" class="empty-state"><el-icon class="empty-icon"><FolderRemove /></el-icon><span>暂无支出分类</span></div>
          <div v-else class="category-list">
            <div v-for="item in expenseCategories" :key="item.id" class="category-item">
              <div class="item-left"><div class="item-dot expense-dot"></div><span class="item-name">{{ item.name }}</span></div>
              <div class="item-actions">
                <el-button link type="primary" size="small" @click="handleEdit(item)"><el-icon><Edit /></el-icon></el-button>
                <el-button link type="danger" size="small" @click="handleDelete(item.id)"><el-icon><Delete /></el-icon></el-button>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :md="12">
        <el-card shadow="never" class="category-card">
          <template #header>
            <div class="card-header">
              <div class="header-left"><div class="header-icon income-icon"><el-icon><Top /></el-icon></div><span class="header-title">收入分类</span></div>
              <el-button type="primary" size="small" @click="handleAdd(1)"><el-icon><Plus /></el-icon><span class="desktop-label">添加收入</span></el-button>
            </div>
          </template>
          <div v-if="incomeCategories.length === 0" class="empty-state"><el-icon class="empty-icon"><FolderRemove /></el-icon><span>暂无收入分类</span></div>
          <div v-else class="category-list">
            <div v-for="item in incomeCategories" :key="item.id" class="category-item">
              <div class="item-left"><div class="item-dot income-dot"></div><span class="item-name">{{ item.name }}</span></div>
              <div class="item-actions">
                <el-button link type="primary" size="small" @click="handleEdit(item)"><el-icon><Edit /></el-icon></el-button>
                <el-button link type="danger" size="small" @click="handleDelete(item.id)"><el-icon><Delete /></el-icon></el-button>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="88%" max-width="420px" top="20vh" :close-on-click-modal="false" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" size="large">
        <el-form-item label="类型"><el-radio-group v-model="form.type" class="type-group"><el-radio-button :label="0">支出</el-radio-button><el-radio-button :label="1">收入</el-radio-button></el-radio-group></el-form-item>
        <el-form-item label="分类名称" prop="name"><el-input v-model="form.name" placeholder="请输入分类名称" maxlength="20" show-word-limit clearable /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleSubmit">{{ isEdit ? '保存修改' : '添加分类' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { categoryApi } from '@/api'
import type { CategoryVO, CategoryDTO, CategoryType } from '@/types'
import { Plus, Edit, Delete, Bottom, Top, FolderRemove } from '@element-plus/icons-vue'

const categories = ref<CategoryVO[]>([])
const dialogVisible = ref(false)
const submitLoading = ref(false)
const formRef = ref<FormInstance>()
const isEdit = ref(false)
const editId = ref<number | null>(null)
const form = reactive<CategoryDTO>({ name: '', type: 0 as CategoryType })
const rules: FormRules = { name: [{ required: true, message: '请输入分类名称', trigger: 'blur' }, { max: 20, message: '名称不能超过20个字符', trigger: 'blur' }] }

const dialogTitle = computed(() => isEdit.value ? '编辑分类' : '添加分类')
const expenseCategories = computed(() => categories.value.filter(i => i.type === 0))
const incomeCategories = computed(() => categories.value.filter(i => i.type === 1))

const fetchCategories = async () => { try { const r = await categoryApi.getList(); categories.value = r.data } catch {} }
const handleAdd = (t: CategoryType) => { isEdit.value = false; editId.value = null; form.name = ''; form.type = t; dialogVisible.value = true }
const handleEdit = (row: CategoryVO) => { isEdit.value = true; editId.value = row.id; form.name = row.name; form.type = row.type; dialogVisible.value = true }
const handleDelete = (id: number) => {
  ElMessageBox.confirm('确定要删除这个分类吗？', '提示', { confirmButtonText: '确定删除', cancelButtonText: '取消', type: 'warning', roundButton: true })
    .then(async () => { try { await categoryApi.delete(id); ElMessage.success('删除成功'); fetchCategories() } catch {} }).catch(() => {})
}
const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    submitLoading.value = true
    try {
      if (isEdit.value && editId.value) { await categoryApi.update(editId.value, form); ElMessage.success('编辑成功') }
      else { await categoryApi.add(form); ElMessage.success('添加成功') }
      dialogVisible.value = false; fetchCategories()
    } catch {} finally { submitLoading.value = false }
  })
}
onMounted(() => { fetchCategories() })
defineExpose({ refreshData: fetchCategories })
</script>

<style scoped>
.categories-page { display: flex; flex-direction: column; gap: 16px; }
.category-card { height: 100%; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.header-left { display: flex; align-items: center; gap: 10px; }
.header-icon { width: 32px; height: 32px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 16px; }
.expense-icon { background: rgba(255,77,79,.1); color: var(--danger); }
.income-icon { background: rgba(82,196,26,.1); color: var(--success); }
.header-title { font-size: 16px; font-weight: 600; color: var(--text-primary); }
.category-list { display: flex; flex-direction: column; gap: 8px; }
.category-item { display: flex; align-items: center; justify-content: space-between; padding: 14px 16px; border-radius: 12px; background: var(--bg-body); transition: all .15s; }
.category-item:active { transform: scale(.98); background: #e8ecf1; }
.item-left { display: flex; align-items: center; gap: 12px; }
.item-dot { width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0; }
.expense-dot { background: var(--danger); box-shadow: 0 0 6px rgba(255,77,79,.3); }
.income-dot { background: var(--success); box-shadow: 0 0 6px rgba(82,196,26,.3); }
.item-name { font-size: 15px; font-weight: 500; color: var(--text-primary); }
.item-actions { display: flex; gap: 6px; }
.item-actions .el-button { min-width: 36px; height: 36px; font-size: 16px; }
.empty-state { display: flex; flex-direction: column; align-items: center; gap: 12px; padding: 40px 0; color: var(--text-tertiary); }
.empty-icon { font-size: 40px; color: var(--border); }
.type-group .el-radio-button__inner { min-width: 90px; }
@media (max-width: 767px) {
  .desktop-label { display: none; }
  .categories-page { gap: 20px; }
  .category-item { padding: 16px; border-radius: 14px; }
  .item-name { font-size: 16px; }
  .item-actions .el-button { min-width: 44px; height: 44px; font-size: 18px; }
}
</style>
