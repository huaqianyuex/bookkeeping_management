import { useState, useEffect } from 'react'
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity,
  Alert, ActivityIndicator, RefreshControl, TextInput, Modal,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { Ionicons } from '@expo/vector-icons'
import { getCategoryList, addCategory, updateCategory, deleteCategory } from '../api/category'
import { theme } from '../config/theme'
import SkeletonCard from '../components/SkeletonCard'
import EmptyState from '../components/EmptyState'
import FadeInView from '../components/FadeInView'
import ScaleButton from '../components/ScaleButton'

export default function CategoriesScreen() {
  const [list, setList] = useState([])
  const [loading, setLoading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [name, setName] = useState('')
  const [type, setType] = useState(0)
  const [submitting, setSubmitting] = useState(false)

  const fetchList = async () => {
    setLoading(true)
    try {
      const res = await getCategoryList()
      if (res.code === 200) setList(res.data)
    } catch (e) {}
    setLoading(false)
  }

  useEffect(() => { fetchList() }, [])

  const onRefresh = () => {
    setRefreshing(true)
    fetchList().then(() => setRefreshing(false))
  }

  const handleAdd = () => {
    setEditing(null)
    setName('')
    setType(0)
    setModalOpen(true)
  }

  const handleEdit = (item) => {
    setEditing(item)
    setName(item.name)
    setType(item.type)
    setModalOpen(true)
  }

  const handleDelete = (id) => {
    Alert.alert('确认删除', '删除后关联账单的分类名称将保留，确定删除？', [
      { text: '取消', style: 'cancel' },
      {
        text: '删除', style: 'destructive',
        onPress: async () => {
          try {
            const res = await deleteCategory(id)
            if (res.code === 200) {
              fetchList()
            } else {
              Alert.alert('删除失败', res.message)
            }
          } catch (e) {
            Alert.alert('错误', '删除失败')
          }
        },
      },
    ])
  }

  const handleSave = async () => {
    if (!name.trim()) {
      Alert.alert('提示', '分类名称不能为空')
      return
    }
    setSubmitting(true)
    try {
      let res
      if (editing) {
        res = await updateCategory(editing.id, { name: name.trim(), type })
      } else {
        res = await addCategory({ name: name.trim(), type })
      }
      if (res.code === 200) {
        setModalOpen(false)
        fetchList()
      } else {
        Alert.alert('失败', res.message)
      }
    } catch (e) {
      Alert.alert('错误', '保存失败')
    } finally {
      setSubmitting(false)
    }
  }

  const expenseCategories = list.filter(c => c.type === 0)
  const incomeCategories = list.filter(c => c.type === 1)

  const renderCategoryItem = (item) => (
    <ScaleButton
      key={item.id}
      style={styles.categoryItem}
      onPress={() => handleEdit(item)}
    >
      <View style={[
        styles.categoryIcon,
        { backgroundColor: item.type === 0 ? `${theme.colors.error}15` : `${theme.colors.success}15` }
      ]}>
        <Ionicons
          name={item.type === 0 ? 'arrow-down' : 'arrow-up'}
          size={20}
          color={item.type === 0 ? theme.colors.error : theme.colors.success}
        />
      </View>
      <View style={styles.categoryInfo}>
        <Text style={styles.categoryName}>{item.name}</Text>
      </View>
      <TouchableOpacity
        style={styles.deleteBtn}
        onPress={() => handleDelete(item.id)}
        hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
      >
        <Ionicons name="trash-outline" size={18} color={theme.colors.textLight} />
      </TouchableOpacity>
    </ScaleButton>
  )

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <View>
          <Text style={styles.headerTitle}>分类管理</Text>
          <Text style={styles.headerSubtitle}>共 {list.length} 个分类</Text>
        </View>
        <ScaleButton style={styles.addBtn} onPress={handleAdd}>
          <Ionicons name="add" size={24} color={theme.colors.surface} />
        </ScaleButton>
      </View>

      {loading && !refreshing ? (
        <SkeletonCard lines={4} />
      ) : (
        <FadeInView style={{ flex: 1 }}>
          <ScrollView
            style={styles.scroll}
            contentContainerStyle={styles.scrollContent}
            refreshControl={
              <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
            }
          >
            {list.length === 0 ? (
              <EmptyState
                icon="grid-outline"
                title="暂无分类"
                description="点击右上角按钮添加分类"
              />
            ) : (
              <>
                {expenseCategories.length > 0 && (
                  <View style={styles.section}>
                    <View style={styles.sectionHeader}>
                      <View style={[styles.sectionDot, { backgroundColor: theme.colors.error }]} />
                      <Text style={styles.sectionTitle}>支出分类</Text>
                      <Text style={styles.sectionCount}>{expenseCategories.length}个</Text>
                    </View>
                    {expenseCategories.map(renderCategoryItem)}
                  </View>
                )}
                {incomeCategories.length > 0 && (
                  <View style={styles.section}>
                    <View style={styles.sectionHeader}>
                      <View style={[styles.sectionDot, { backgroundColor: theme.colors.success }]} />
                      <Text style={styles.sectionTitle}>收入分类</Text>
                      <Text style={styles.sectionCount}>{incomeCategories.length}个</Text>
                    </View>
                    {incomeCategories.map(renderCategoryItem)}
                  </View>
                )}
              </>
            )}
          </ScrollView>
        </FadeInView>
      )}

      <Modal visible={modalOpen} transparent animationType="slide">
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>
                {editing ? '编辑分类' : '新增分类'}
              </Text>
              <TouchableOpacity onPress={() => setModalOpen(false)}>
                <Ionicons name="close" size={24} color={theme.colors.textSecondary} />
              </TouchableOpacity>
            </View>

            <Text style={styles.fieldLabel}>分类名称</Text>
            <View style={styles.inputContainer}>
              <TextInput
                style={styles.input}
                placeholder="请输入分类名称"
                placeholderTextColor={theme.colors.textLight}
                value={name}
                onChangeText={setName}
              />
            </View>

            <Text style={styles.fieldLabel}>分类类型</Text>
            <View style={styles.typeOptions}>
              <ScaleButton
                style={[styles.typeOption, type === 0 && styles.typeOptionExpense]}
                onPress={() => setType(0)}
              >
                <View style={[styles.typeIconContainer, { backgroundColor: type === 0 ? `${theme.colors.error}15` : theme.colors.surfaceHover }]}>
                  <Ionicons name="arrow-down" size={16} color={type === 0 ? theme.colors.error : theme.colors.textSecondary} />
                </View>
                <Text style={[styles.typeOptionText, type === 0 && styles.typeOptionTextActive]}>
                  支出
                </Text>
              </ScaleButton>
              <ScaleButton
                style={[styles.typeOption, type === 1 && styles.typeOptionIncome]}
                onPress={() => setType(1)}
              >
                <View style={[styles.typeIconContainer, { backgroundColor: type === 1 ? `${theme.colors.success}15` : theme.colors.surfaceHover }]}>
                  <Ionicons name="arrow-up" size={16} color={type === 1 ? theme.colors.success : theme.colors.textSecondary} />
                </View>
                <Text style={[styles.typeOptionText, type === 1 && styles.typeOptionTextActive]}>
                  收入
                </Text>
              </ScaleButton>
            </View>

            <View style={styles.modalActions}>
              <TouchableOpacity
                style={styles.cancelBtn}
                onPress={() => setModalOpen(false)}
              >
                <Text style={styles.cancelBtnText}>取消</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.saveBtn, submitting && { opacity: 0.6 }]}
                onPress={handleSave}
                disabled={submitting}
              >
                {submitting ? (
                  <ActivityIndicator color={theme.colors.surface} size="small" />
                ) : (
                  <Text style={styles.saveBtnText}>确定</Text>
                )}
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: theme.spacing.lg,
    paddingVertical: theme.spacing.md,
    backgroundColor: theme.colors.surface,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.borderLight,
  },
  headerTitle: {
    ...theme.typography.h1,
    color: theme.colors.primary,
  },
  headerSubtitle: {
    ...theme.typography.caption,
    color: theme.colors.textSecondary,
    marginTop: 4,
  },
  addBtn: {
    width: 40,
    height: 40,
    borderRadius: theme.borderRadius.full,
    backgroundColor: theme.colors.primary,
    justifyContent: 'center',
    alignItems: 'center',
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    padding: theme.spacing.md,
    paddingBottom: theme.spacing.xl,
  },
  section: {
    marginBottom: theme.spacing.lg,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: theme.spacing.md,
  },
  sectionDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: 8,
  },
  sectionTitle: {
    fontSize: 15,
    fontWeight: '700',
    color: theme.colors.primary,
    flex: 1,
  },
  sectionCount: {
    fontSize: 13,
    color: theme.colors.textSecondary,
    fontWeight: '500',
  },
  categoryItem: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: theme.colors.surface,
    borderRadius: theme.borderRadius.md,
    padding: theme.spacing.md,
    marginBottom: theme.spacing.sm,
    ...theme.shadows.small,
  },
  categoryIcon: {
    width: 40,
    height: 40,
    borderRadius: theme.borderRadius.sm,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: theme.spacing.md,
  },
  categoryInfo: {
    flex: 1,
  },
  categoryName: {
    fontSize: 15,
    fontWeight: '600',
    color: theme.colors.primary,
  },
  deleteBtn: {
    width: 32,
    height: 32,
    borderRadius: theme.borderRadius.full,
    backgroundColor: theme.colors.background,
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: theme.colors.shadowDark,
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: theme.colors.surface,
    borderTopLeftRadius: theme.borderRadius.xl,
    borderTopRightRadius: theme.borderRadius.xl,
    padding: theme.spacing.lg,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
  },
  modalTitle: {
    ...theme.typography.h2,
    color: theme.colors.primary,
  },
  fieldLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: theme.colors.primary,
    marginBottom: 10,
  },
  inputContainer: {
    marginBottom: theme.spacing.md,
  },
  input: {
    height: 50,
    borderWidth: 1,
    borderColor: theme.colors.border,
    borderRadius: theme.borderRadius.md,
    paddingHorizontal: theme.spacing.md,
    fontSize: 16,
    color: theme.colors.text,
    backgroundColor: theme.colors.background,
  },
  typeOptions: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: theme.spacing.lg,
  },
  typeOption: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    height: 50,
    borderRadius: theme.borderRadius.md,
    backgroundColor: theme.colors.surfaceHover,
    gap: 8,
  },
  typeOptionExpense: {
    backgroundColor: `${theme.colors.error}15`,
    borderWidth: 1,
    borderColor: theme.colors.error,
  },
  typeOptionIncome: {
    backgroundColor: `${theme.colors.success}15`,
    borderWidth: 1,
    borderColor: theme.colors.success,
  },
  typeIconContainer: {
    width: 28,
    height: 28,
    borderRadius: theme.borderRadius.sm,
    justifyContent: 'center',
    alignItems: 'center',
  },
  typeOptionText: {
    fontSize: 15,
    fontWeight: '600',
    color: theme.colors.textSecondary,
  },
  typeOptionTextActive: {
    color: theme.colors.primary,
  },
  modalActions: {
    flexDirection: 'row',
    gap: 12,
  },
  cancelBtn: {
    flex: 1,
    height: 50,
    borderRadius: theme.borderRadius.md,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: theme.colors.surfaceHover,
  },
  cancelBtnText: {
    fontSize: 16,
    fontWeight: '600',
    color: theme.colors.textSecondary,
  },
  saveBtn: {
    flex: 2,
    height: 50,
    borderRadius: theme.borderRadius.md,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: theme.colors.primary,
  },
  saveBtnText: {
    fontSize: 16,
    fontWeight: '600',
    color: theme.colors.surface,
  },
})
