import { useState, useEffect, useCallback, useMemo } from 'react'
import {
  View, Text, StyleSheet, SectionList, TouchableOpacity,
  Alert, ActivityIndicator, RefreshControl, Modal,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { Ionicons } from '@expo/vector-icons'
import dayjs from 'dayjs'
import { getRecordPage, deleteRecord } from '../api/record'
import { getCategoryList } from '../api/category'

export default function RecordsScreen({ navigation }) {
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

  useEffect(() => {
    fetchCategories()
    fetchData(query)
  }, [])

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
    return (
      <View style={styles.sectionHeader}>
        <View style={styles.sectionHeaderTop}>
          <View style={styles.sectionHeaderLeft}>
            <Text style={styles.sectionDate}>{section.title}</Text>
            <Text style={styles.sectionDay}>周{dayOfWeek}</Text>
          </View>
          <View style={styles.sectionHeaderRight}>
            {section.totalIncome > 0 && (
              <Text style={styles.sectionIncome}>收 ¥{section.totalIncome.toFixed(2)}</Text>
            )}
            {section.totalExpense > 0 && (
              <Text style={styles.sectionExpense}>支 ¥{section.totalExpense.toFixed(2)}</Text>
            )}
          </View>
        </View>
      </View>
    )
  }

  const renderRecord = ({ item }) => (
    <TouchableOpacity
      style={styles.recordItem}
      activeOpacity={0.7}
      onPress={() => navigation.navigate('AddEditRecord', { record: item })}
    >
      <View style={styles.recordLeft}>
        <View style={[
          styles.typeBadge,
          { backgroundColor: item.categoryType === 0 ? '#fff1f0' : '#f6ffed' },
        ]}>
          <Ionicons
            name={item.categoryType === 0 ? 'arrow-down' : 'arrow-up'}
            size={14}
            color={item.categoryType === 0 ? '#cf1322' : '#3f8600'}
          />
        </View>
        <View style={styles.recordInfo}>
          <Text style={styles.recordCategory}>{item.categoryName}</Text>
          {item.remark ? (
            <Text style={styles.recordRemark} numberOfLines={1}>{item.remark}</Text>
          ) : null}
        </View>
      </View>
      <View style={styles.recordRight}>
        <Text style={[
          styles.recordAmount,
          { color: item.categoryType === 0 ? '#cf1322' : '#3f8600' },
        ]}>
          {item.categoryType === 0 ? '-' : '+'}¥{item.amount.toFixed(2)}
        </Text>
      </View>
      <TouchableOpacity
        style={styles.deleteBtn}
        onPress={() => handleDelete(item.id)}
        hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
      >
        <Ionicons name="trash-outline" size={18} color="#8c8c8c" />
      </TouchableOpacity>
    </TouchableOpacity>
  )

  const renderFooter = () => {
    if (loading && data.records.length > 0) {
      return <ActivityIndicator color="#18181b" style={{ padding: 16 }} />
    }
    if (data.current >= data.pages && data.records.length > 0) {
      return <Text style={styles.footerText}>没有更多了</Text>
    }
    return null
  }

  const activeFilterCategory = categories.find((c) => c.id === filterCategory)

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>账单管理</Text>
        <View style={styles.headerActions}>
          <TouchableOpacity
            style={[styles.filterBtn, filterCategory && styles.filterBtnActive]}
            onPress={() => setFilterOpen(true)}
          >
            <Ionicons
              name="filter-outline"
              size={20}
              color={filterCategory ? '#fff' : '#18181b'}
            />
          </TouchableOpacity>
          {filterCategory && (
            <Text style={styles.filterLabel} numberOfLines={1}>
              {activeFilterCategory?.name}
            </Text>
          )}
          <TouchableOpacity
            style={styles.addBtn}
            onPress={() => navigation.navigate('AddEditRecord', {})}
          >
            <Ionicons name="add" size={24} color="#fff" />
          </TouchableOpacity>
        </View>
      </View>

      <SectionList
        sections={sections}
        renderItem={renderRecord}
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
            <View style={styles.empty}>
              <Ionicons name="receipt-outline" size={48} color="#d9d9d9" />
              <Text style={styles.emptyText}>暂无账单记录</Text>
              <TouchableOpacity
                style={styles.emptyBtn}
                onPress={() => navigation.navigate('AddEditRecord', {})}
              >
                <Text style={styles.emptyBtnText}>记一笔</Text>
              </TouchableOpacity>
            </View>
          ) : (
            <ActivityIndicator color="#18181b" style={{ marginTop: 40 }} />
          )
        }
      />

      <Modal visible={filterOpen} transparent animationType="slide">
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>筛选条件</Text>

            <Text style={styles.filterLabelTitle}>分类</Text>
            <View style={styles.filterOptions}>
              <TouchableOpacity
                style={[styles.filterOption, !filterCategory && styles.filterOptionActive]}
                onPress={() => handleSearch(null)}
              >
                <Text style={[styles.filterOptionText, !filterCategory && styles.filterOptionTextActive]}>全部</Text>
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
              <TouchableOpacity style={styles.modalBtn} onPress={handleReset}>
                <Text style={styles.modalBtnText}>重置</Text>
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
    backgroundColor: '#fafafa',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 16,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#18181b',
  },
  headerActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  filterBtn: {
    width: 32,
    height: 32,
    borderRadius: 16,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#f5f5f5',
  },
  filterBtnActive: {
    backgroundColor: '#18181b',
  },
  filterLabel: {
    fontSize: 12,
    color: '#8c8c8c',
    maxWidth: 60,
  },
  addBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: '#18181b',
    justifyContent: 'center',
    alignItems: 'center',
  },
  list: {
    paddingHorizontal: 16,
    paddingBottom: 32,
  },
  sectionHeader: {
    paddingTop: 20,
    paddingBottom: 8,
  },
  sectionHeaderTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  sectionHeaderLeft: {
    flexDirection: 'row',
    alignItems: 'baseline',
    gap: 8,
  },
  sectionDate: {
    fontSize: 15,
    fontWeight: '600',
    color: '#18181b',
  },
  sectionDay: {
    fontSize: 12,
    color: '#8c8c8c',
  },
  sectionHeaderRight: {
    flexDirection: 'row',
    gap: 12,
  },
  sectionIncome: {
    fontSize: 12,
    color: '#3f8600',
    fontWeight: '500',
  },
  sectionExpense: {
    fontSize: 12,
    color: '#cf1322',
    fontWeight: '500',
  },
  recordItem: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    paddingVertical: 12,
    paddingHorizontal: 14,
    borderBottomWidth: 1,
    borderBottomColor: '#f5f5f5',
  },
  recordLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  typeBadge: {
    width: 32,
    height: 32,
    borderRadius: 16,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  recordInfo: {
    flex: 1,
  },
  recordCategory: {
    fontSize: 15,
    fontWeight: '500',
    color: '#18181b',
  },
  recordRemark: {
    fontSize: 12,
    color: '#8c8c8c',
    marginTop: 2,
  },
  recordRight: {
    alignItems: 'flex-end',
    marginRight: 8,
  },
  recordAmount: {
    fontSize: 15,
    fontWeight: '600',
  },
  deleteBtn: {
    padding: 4,
  },
  footerText: {
    textAlign: 'center',
    color: '#bfbfbf',
    fontSize: 13,
    paddingVertical: 20,
  },
  empty: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingTop: 80,
  },
  emptyText: {
    fontSize: 14,
    color: '#8c8c8c',
    marginTop: 12,
  },
  emptyBtn: {
    marginTop: 16,
    paddingHorizontal: 24,
    paddingVertical: 10,
    backgroundColor: '#18181b',
    borderRadius: 8,
  },
  emptyBtnText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '500',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.4)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: '#fff',
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
    padding: 24,
    maxHeight: '70%',
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#18181b',
    marginBottom: 20,
  },
  filterLabelTitle: {
    fontSize: 14,
    fontWeight: '500',
    color: '#18181b',
    marginBottom: 10,
  },
  filterOptions: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginBottom: 24,
  },
  filterOption: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 8,
    backgroundColor: '#f5f5f5',
  },
  filterOptionActive: {
    backgroundColor: '#18181b',
  },
  filterOptionText: {
    fontSize: 13,
    color: '#595959',
  },
  filterOptionTextActive: {
    color: '#fff',
    fontWeight: '500',
  },
  modalActions: {
    flexDirection: 'row',
    gap: 12,
  },
  modalBtn: {
    flex: 1,
    height: 44,
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#f5f5f5',
  },
  modalBtnText: {
    fontSize: 15,
    fontWeight: '500',
    color: '#595959',
  },
})
