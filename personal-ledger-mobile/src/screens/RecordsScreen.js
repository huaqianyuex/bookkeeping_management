import { useState, useCallback, useMemo, useRef, useEffect } from 'react'
import {
  View, Text, StyleSheet, SectionList, TouchableOpacity,
  Alert, ActivityIndicator, RefreshControl, Modal,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { useFocusEffect } from '@react-navigation/native'
import { Ionicons } from '@expo/vector-icons'
import dayjs from 'dayjs'
import { getRecordPage, deleteRecord } from '../api/record'
import { getCategoryList } from '../api/category'
import { theme } from '../config/theme'
import RecordItem from '../components/RecordItem'
import SkeletonCard from '../components/SkeletonCard'
import EmptyState from '../components/EmptyState'
import FadeInView from '../components/FadeInView'
import ScaleButton from '../components/ScaleButton'

export default function RecordsScreen({ navigation, route }) {
  const [data, setData] = useState({ records: [], total: 0, pages: 0, current: 1, size: 20 })
  const [loading, setLoading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [categories, setCategories] = useState([])
  const [query, setQuery] = useState({ page: 1, size: 20 })
  const [filterOpen, setFilterOpen] = useState(false)
  const [filterCategory, setFilterCategory] = useState(null)

  const fetchCategories = async () => {
    try {
      const res = await getCategoryList()
      if (res.code === 200) setCategories(res.data)
    } catch (e) {}
  }

  const fetchData = useCallback(async (params, append = false) => {
    setLoading(true)
    try {
      const res = await getRecordPage(params)
      if (res.code === 200) {
        if (append && params.page > 1) {
          setData((prev) => ({
            ...res.data,
            records: [...prev.records, ...res.data.records],
          }))
        } else {
          setData(res.data)
        }
      }
    } catch (e) {
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  // 使用 ref 保存当前筛选值，避免 useFocusEffect 闭包陈旧
  const filterCategoryRef = useRef(filterCategory)
  filterCategoryRef.current = filterCategory

  // 每次屏幕获得焦点时，强制从第1页重新加载数据
  // 解决从新增/编辑页面返回后列表不刷新的问题
  useFocusEffect(
    useCallback(() => {
      fetchCategories()
      const params = { page: 1, size: 20 }
      if (filterCategoryRef.current) params.categoryId = filterCategoryRef.current
      setQuery(params)
      fetchData(params)
    }, [])
  )

  // 监听 route.params.refresh 信号作为辅助刷新机制
  // 当 AddEditRecord 保存成功后 navigate 回来时会携带此参数
  useEffect(() => {
    if (route.params?.refresh) {
      const params = { page: 1, size: 20 }
      if (filterCategory) params.categoryId = filterCategory
      setQuery(params)
      fetchData(params)
    }
  }, [route.params?.refresh])

  const sections = useMemo(() => {
    const groups = {}
    for (const r of data.records) {
      if (!groups[r.recordDate]) groups[r.recordDate] = []
      groups[r.recordDate].push(r)
    }
    return Object.entries(groups)
      .sort(([a], [b]) => b.localeCompare(a))
      .map(([date, items]) => {
        const totalIncome = items
          .filter((i) => i.categoryType === 1)
          .reduce((s, i) => s + i.amount, 0)
        const totalExpense = items
          .filter((i) => i.categoryType === 0)
          .reduce((s, i) => s + i.amount, 0)
        return { title: date, totalIncome, totalExpense, data: items }
      })
  }, [data.records])

  const onRefresh = () => {
    setRefreshing(true)
    const params = { ...query, page: 1 }
    setQuery(params)
    fetchData(params)
  }

  const loadMore = () => {
    if (loading || data.current >= data.pages) return
    const params = { ...query, page: data.current + 1, size: data.size }
    setQuery(params)
    fetchData(params, true)
  }

  const handleSearch = (categoryId) => {
    setFilterOpen(false)
    setFilterCategory(categoryId)
    const params = { page: 1, size: 20 }
    if (categoryId) params.categoryId = categoryId
    setQuery(params)
    fetchData(params)
  }

  const handleReset = () => {
    setFilterCategory(null)
    setFilterOpen(false)
    const params = { page: 1, size: 20 }
    setQuery(params)
    fetchData(params)
  }

  const handleDelete = (id) => {
    Alert.alert('确认删除', '确定要删除该账单记录吗？', [
      { text: '取消', style: 'cancel' },
      {
        text: '删除', style: 'destructive',
        onPress: async () => {
          try {
            const res = await deleteRecord(id)
            if (res.code === 200) {
              fetchData({ ...query, page: 1 })
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

  const renderSectionHeader = ({ section }) => {
    const d = dayjs(section.title)
    const dayOfWeek = ['日', '一', '二', '三', '四', '五', '六'][d.day()]
    const isToday = dayjs().format('YYYY-MM-DD') === section.title

    return (
      <View style={styles.sectionHeader}>
        <View style={styles.sectionHeaderLeft}>
          <View style={[styles.dateBadge, isToday && styles.dateBadgeToday]}>
            <Text style={[styles.dateBadgeDay, isToday && styles.dateBadgeDayToday]}>{d.format('DD')}</Text>
          </View>
          <View>
            <Text style={styles.sectionDate}>{section.title}</Text>
            <Text style={styles.sectionDay}>周{dayOfWeek}{isToday ? ' · 今天' : ''}</Text>
          </View>
        </View>
        <View style={styles.sectionSummary}>
          {section.totalIncome > 0 && (
            <View style={styles.summaryItem}>
              <Ionicons name="arrow-down" size={12} color={theme.colors.success} />
              <Text style={styles.sectionIncome}>¥{section.totalIncome.toFixed(2)}</Text>
            </View>
          )}
          {section.totalExpense > 0 && (
            <View style={styles.summaryItem}>
              <Ionicons name="arrow-up" size={12} color={theme.colors.error} />
              <Text style={styles.sectionExpense}>¥{section.totalExpense.toFixed(2)}</Text>
            </View>
          )}
        </View>
      </View>
    )
  }

  const renderFooter = () => {
    if (loading && data.records.length > 0) {
      return <ActivityIndicator color={theme.colors.primary} style={{ padding: theme.spacing.md }} />
    }
    if (data.current >= data.pages && data.records.length > 0) {
      return (
        <View style={styles.footer}>
          <View style={styles.footerLine} />
          <Text style={styles.footerText}>没有更多了</Text>
          <View style={styles.footerLine} />
        </View>
      )
    }
    return null
  }

  const activeFilterCategory = categories.find((c) => c.id === filterCategory)

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <View>
          <Text style={styles.headerTitle}>账单管理</Text>
          <Text style={styles.headerSubtitle}>共 {data.total} 条记录</Text>
        </View>
        <View style={styles.headerActions}>
          <ScaleButton
            style={[styles.filterBtn, filterCategory && styles.filterBtnActive]}
            onPress={() => setFilterOpen(true)}
          >
            <Ionicons
              name="filter"
              size={18}
              color={filterCategory ? theme.colors.surface : theme.colors.textSecondary}
            />
          </ScaleButton>
          <ScaleButton
            style={styles.addBtn}
            onPress={() => navigation.navigate('AddEditRecord', {})}
          >
            <Ionicons name="add" size={24} color={theme.colors.surface} />
          </ScaleButton>
        </View>
      </View>

      {filterCategory && (
        <View style={styles.activeFilter}>
          <Text style={styles.activeFilterText}>
            筛选: {activeFilterCategory?.name}
          </Text>
          <TouchableOpacity onPress={handleReset}>
            <Ionicons name="close-circle" size={18} color={theme.colors.textSecondary} />
          </TouchableOpacity>
        </View>
      )}

      <FadeInView style={{ flex: 1 }}>
        <SectionList
          sections={sections}
          renderItem={({ item }) => (
            <RecordItem
              item={item}
              onPress={() => navigation.navigate('AddEditRecord', { record: item })}
              onDelete={handleDelete}
            />
          )}
          renderSectionHeader={renderSectionHeader}
          keyExtractor={(item) => String(item.id)}
          contentContainerStyle={styles.list}
          stickySectionHeadersEnabled={false}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
          }
          onEndReached={loadMore}
          onEndReachedThreshold={0.3}
          ListFooterComponent={renderFooter}
          ListEmptyComponent={
            !loading ? (
              <EmptyState
                icon="receipt-outline"
                title="暂无账单记录"
                description="点击下方按钮开始记账"
                actionLabel="记一笔"
                onAction={() => navigation.navigate('AddEditRecord', {})}
              />
            ) : (
              <SkeletonCard lines={5} variant="list" />
            )
          }
        />
      </FadeInView>

      <Modal visible={filterOpen} transparent animationType="slide">
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>筛选条件</Text>
              <TouchableOpacity onPress={() => setFilterOpen(false)}>
                <Ionicons name="close" size={24} color={theme.colors.textSecondary} />
              </TouchableOpacity>
            </View>

            <Text style={styles.filterLabelTitle}>分类</Text>
            <View style={styles.filterOptions}>
              <TouchableOpacity
                style={[styles.filterOption, !filterCategory && styles.filterOptionActive]}
                onPress={() => handleSearch(null)}
              >
                <Text style={[styles.filterOptionText, !filterCategory && styles.filterOptionTextActive]}>
                  全部
                </Text>
              </TouchableOpacity>
              {categories.map((c) => (
                <TouchableOpacity
                  key={c.id}
                  style={[styles.filterOption, filterCategory === c.id && styles.filterOptionActive]}
                  onPress={() => handleSearch(c.id)}
                >
                  <Text style={[styles.filterOptionText, filterCategory === c.id && styles.filterOptionTextActive]}>
                    {c.name}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            <View style={styles.modalActions}>
              <TouchableOpacity style={styles.resetBtn} onPress={handleReset}>
                <Text style={styles.resetBtnText}>重置</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.applyBtn}
                onPress={() => setFilterOpen(false)}
              >
                <Text style={styles.applyBtnText}>确定</Text>
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
  headerActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  filterBtn: {
    width: 40,
    height: 40,
    borderRadius: theme.borderRadius.full,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: theme.colors.surfaceHover,
  },
  filterBtnActive: {
    backgroundColor: theme.colors.primary,
  },
  addBtn: {
    width: 40,
    height: 40,
    borderRadius: theme.borderRadius.full,
    backgroundColor: theme.colors.primary,
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: theme.colors.primary,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 4,
  },
  activeFilter: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: theme.spacing.lg,
    paddingVertical: theme.spacing.sm,
    backgroundColor: `${theme.colors.accent}15`,
  },
  activeFilterText: {
    fontSize: 13,
    color: theme.colors.accent,
    fontWeight: '500',
  },
  list: {
    paddingHorizontal: theme.spacing.md,
    paddingBottom: theme.spacing.xl,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: theme.spacing.lg,
    paddingBottom: theme.spacing.md,
  },
  sectionHeaderLeft: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  dateBadge: {
    width: 44,
    height: 44,
    borderRadius: theme.borderRadius.md,
    backgroundColor: theme.colors.surfaceHover,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: theme.spacing.md,
  },
  dateBadgeToday: {
    backgroundColor: theme.colors.primary,
  },
  dateBadgeDay: {
    fontSize: 18,
    fontWeight: '700',
    color: theme.colors.text,
  },
  dateBadgeDayToday: {
    color: theme.colors.surface,
  },
  sectionDate: {
    fontSize: 15,
    fontWeight: '700',
    color: theme.colors.primary,
  },
  sectionDay: {
    fontSize: 12,
    color: theme.colors.textSecondary,
    marginTop: 2,
  },
  sectionSummary: {
    flexDirection: 'row',
    gap: 12,
  },
  summaryItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  sectionIncome: {
    fontSize: 13,
    color: theme.colors.success,
    fontWeight: '600',
  },
  sectionExpense: {
    fontSize: 13,
    color: theme.colors.error,
    fontWeight: '600',
  },
  footer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 20,
    gap: 12,
  },
  footerLine: {
    flex: 1,
    height: 1,
    backgroundColor: theme.colors.border,
  },
  footerText: {
    textAlign: 'center',
    color: theme.colors.textLight,
    fontSize: 13,
    fontWeight: '500',
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
    maxHeight: '70%',
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
  filterLabelTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: theme.colors.primary,
    marginBottom: 12,
  },
  filterOptions: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
    marginBottom: theme.spacing.lg,
  },
  filterOption: {
    paddingHorizontal: theme.spacing.md,
    paddingVertical: 10,
    borderRadius: theme.borderRadius.sm,
    backgroundColor: theme.colors.surfaceHover,
  },
  filterOptionActive: {
    backgroundColor: theme.colors.primary,
  },
  filterOptionText: {
    fontSize: 14,
    color: theme.colors.textSecondary,
    fontWeight: '500',
  },
  filterOptionTextActive: {
    color: theme.colors.surface,
    fontWeight: '600',
  },
  modalActions: {
    flexDirection: 'row',
    gap: 12,
  },
  resetBtn: {
    flex: 1,
    height: 50,
    borderRadius: theme.borderRadius.md,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: theme.colors.surfaceHover,
  },
  resetBtnText: {
    fontSize: 16,
    fontWeight: '600',
    color: theme.colors.textSecondary,
  },
  applyBtn: {
    flex: 2,
    height: 50,
    borderRadius: theme.borderRadius.md,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: theme.colors.primary,
  },
  applyBtnText: {
    fontSize: 16,
    fontWeight: '600',
    color: theme.colors.surface,
  },
})
