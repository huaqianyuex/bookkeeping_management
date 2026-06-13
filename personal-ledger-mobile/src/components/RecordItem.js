import React from 'react'
import { View, Text, StyleSheet, TouchableOpacity, Alert } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { theme } from '../config/theme'
import ScaleButton from './ScaleButton'

export default function RecordItem({ item, onPress, onDelete }) {
  const isExpense = item.categoryType === 0
  const color = isExpense ? theme.colors.error : theme.colors.success
  const bgColor = isExpense ? `${theme.colors.error}15` : `${theme.colors.success}15`
  const iconName = isExpense ? 'arrow-down' : 'arrow-up'
  const sign = isExpense ? '-' : '+'

  const handleLongPress = () => {
    Alert.alert('确认删除', '确定要删除该账单记录吗？', [
      { text: '取消', style: 'cancel' },
      { text: '删除', style: 'destructive', onPress: () => onDelete?.(item.id) },
    ])
  }

  return (
    <ScaleButton onPress={onPress} onLongPress={handleLongPress} style={[styles.container, { borderLeftColor: color }]}>
      <View style={[styles.iconContainer, { backgroundColor: bgColor }]}>
        <Ionicons name={iconName} size={18} color={color} />
      </View>
      <View style={styles.info}>
        <Text style={styles.category}>{item.categoryName}</Text>
        {item.remark ? (
          <Text style={styles.remark} numberOfLines={1}>{item.remark}</Text>
        ) : null}
      </View>
      <View style={styles.right}>
        <Text style={[styles.amount, { color }]}>
          {sign}¥{item.amount.toFixed(2)}
        </Text>
      </View>
      <TouchableOpacity
        style={styles.deleteBtn}
        onPress={() => onDelete?.(item.id)}
        hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
      >
        <Ionicons name="trash-outline" size={16} color={theme.colors.textLight} />
      </TouchableOpacity>
    </ScaleButton>
  )
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: theme.colors.surface,
    paddingVertical: theme.spacing.md,
    paddingHorizontal: theme.spacing.md,
    marginBottom: theme.spacing.sm,
    borderRadius: theme.borderRadius.md,
    borderLeftWidth: 3,
    ...theme.shadows.small,
  },
  iconContainer: {
    width: 40,
    height: 40,
    borderRadius: theme.borderRadius.sm,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: theme.spacing.md,
  },
  info: {
    flex: 1,
  },
  category: {
    fontSize: theme.typography.body.fontSize,
    fontWeight: '600',
    color: theme.colors.text,
  },
  remark: {
    ...theme.typography.caption,
    color: theme.colors.textSecondary,
    marginTop: 2,
  },
  right: {
    alignItems: 'flex-end',
    marginRight: theme.spacing.md,
  },
  amount: {
    fontSize: 16,
    fontWeight: '700',
    letterSpacing: -0.3,
  },
  deleteBtn: {
    width: 32,
    height: 32,
    borderRadius: theme.borderRadius.full,
    backgroundColor: theme.colors.background,
    justifyContent: 'center',
    alignItems: 'center',
  },
})
