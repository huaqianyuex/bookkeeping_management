import { useState, useEffect } from 'react'
import {
  View, Text, StyleSheet, FlatList, TouchableOpacity,
  Alert, ActivityIndicator, RefreshControl, TextInput, Modal,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { Ionicons } from '@expo/vector-icons'
import { getCategoryList, addCategory, updateCategory, deleteCategory } from '../api/category'

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

  const renderCategory = ({ item }) => (
    <TouchableOpacity
      style={styles.categoryItem}
      activeOpacity={0.7}
      onPress={() => handleEdit(item)}
    >
      <View style={styles.categoryLeft}>
        <View style={[
          styles.typeDot,
          { backgroundColor: item.type === 0 ? '#cf1322' : '#3f8600' },
        ]} />
        <View>
          <Text style={styles.categoryName}>{item.name}</Text>
          <Text style={styles.categoryType}>
            {item.type === 0 ? '支出' : '收入'}
          </Text>
        </View>
      </View>
      <TouchableOpacity
        onPress={() => handleDelete(item.id)}
        hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
      >
        <Ionicons name="trash-outline" size={18} color="#8c8c8c" />
      </TouchableOpacity>
    </TouchableOpacity>
  )

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>分类管理</Text>
        <TouchableOpacity style={styles.addBtn} onPress={handleAdd}>
          <Ionicons name="add" size={24} color="#fff" />
        </TouchableOpacity>
      </View>

      <FlatList
        data={list}
        renderItem={renderCategory}
        keyExtractor={(item) => String(item.id)}
        contentContainerStyle={styles.list}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
        ListEmptyComponent={
          !loading ? (
            <View style={styles.empty}>
              <Ionicons name="grid-outline" size={48} color="#d9d9d9" />
              <Text style={styles.emptyText}>暂无分类</Text>
            </View>
          ) : (
            <ActivityIndicator color="#18181b" style={{ marginTop: 40 }} />
          )
        }
      />

      <Modal visible={modalOpen} transparent animationType="slide">
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>
              {editing ? '编辑分类' : '新增分类'}
            </Text>

            <Text style={styles.fieldLabel}>分类名称</Text>
            <TextInput
              style={styles.input}
              placeholder="请输入分类名称"
              placeholderTextColor="#bfbfbf"
              value={name}
              onChangeText={setName}
            />

            <Text style={styles.fieldLabel}>分类类型</Text>
            <View style={styles.typeOptions}>
              <TouchableOpacity
                style={[styles.typeOption, type === 0 && styles.typeOptionActive]}
                onPress={() => setType(0)}
              >
                <Text style={[styles.typeOptionText, type === 0 && styles.typeOptionTextActive]}>
                  支出
                </Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.typeOption, type === 1 && styles.typeOptionActive]}
                onPress={() => setType(1)}
              >
                <Text style={[styles.typeOptionText, type === 1 && styles.typeOptionTextActive]}>
                  收入
                </Text>
              </TouchableOpacity>
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
                  <ActivityIndicator color="#fff" size="small" />
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
  addBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: '#18181b',
    justifyContent: 'center',
    alignItems: 'center',
  },
  list: {
    padding: 16,
    paddingBottom: 32,
  },
  categoryItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#fff',
    borderRadius: 10,
    padding: 16,
    marginBottom: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 4,
    elevation: 1,
  },
  categoryLeft: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  typeDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    marginRight: 12,
  },
  categoryName: {
    fontSize: 15,
    fontWeight: '500',
    color: '#18181b',
  },
  categoryType: {
    fontSize: 12,
    color: '#8c8c8c',
    marginTop: 2,
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
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#18181b',
    marginBottom: 20,
  },
  fieldLabel: {
    fontSize: 14,
    fontWeight: '500',
    color: '#18181b',
    marginBottom: 8,
    marginTop: 12,
  },
  input: {
    height: 48,
    borderWidth: 1,
    borderColor: '#e8e8e8',
    borderRadius: 8,
    paddingHorizontal: 16,
    fontSize: 16,
    color: '#18181b',
    backgroundColor: '#fafafa',
  },
  typeOptions: {
    flexDirection: 'row',
    gap: 12,
  },
  typeOption: {
    flex: 1,
    height: 44,
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#f5f5f5',
    borderWidth: 1,
    borderColor: '#f5f5f5',
  },
  typeOptionActive: {
    backgroundColor: '#18181b',
    borderColor: '#18181b',
  },
  typeOptionText: {
    fontSize: 15,
    fontWeight: '500',
    color: '#595959',
  },
  typeOptionTextActive: {
    color: '#fff',
  },
  modalActions: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 24,
  },
  cancelBtn: {
    flex: 1,
    height: 44,
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#f5f5f5',
  },
  cancelBtnText: {
    fontSize: 15,
    fontWeight: '500',
    color: '#595959',
  },
  saveBtn: {
    flex: 1,
    height: 44,
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#18181b',
  },
  saveBtnText: {
    fontSize: 15,
    fontWeight: '600',
    color: '#fff',
  },
})
