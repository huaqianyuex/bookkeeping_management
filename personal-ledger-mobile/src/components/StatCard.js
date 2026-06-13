import React from 'react'
import { View, Text, StyleSheet } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { theme } from '../config/theme'
import ScaleButton from './ScaleButton'

export default function StatCard({ label, value, type, icon, compact, onPress }) {
  const color = type === 'income'
    ? theme.colors.success
    : type === 'expense'
      ? theme.colors.error
      : theme.colors.primary

  const bgColor = type === 'income'
    ? `${theme.colors.success}15`
    : type === 'expense'
      ? `${theme.colors.error}15`
      : `${theme.colors.primary}15`

  if (compact) {
    return (
      <ScaleButton onPress={onPress} style={[styles.compactCard, { borderLeftColor: color }]}>
        <View style={[styles.compactIconContainer, { backgroundColor: bgColor }]}>
          <Ionicons name={icon} size={16} color={color} />
        </View>
        <View style={styles.compactContent}>
          <Text style={styles.compactLabel}>{label}</Text>
          <Text style={[styles.compactValue, { color }]}>{value}</Text>
        </View>
      </ScaleButton>
    )
  }

  return (
    <ScaleButton onPress={onPress} style={styles.card}>
      <View style={[styles.iconContainer, { backgroundColor: bgColor }]}>
        <Ionicons name={icon} size={20} color={color} />
      </View>
      <Text style={styles.label}>{label}</Text>
      <Text style={[styles.value, { color }]}>{value}</Text>
    </ScaleButton>
  )
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.borderRadius.lg,
    padding: theme.spacing.lg,
    marginBottom: theme.spacing.md,
    ...theme.shadows.small,
  },
  iconContainer: {
    width: 40,
    height: 40,
    borderRadius: theme.borderRadius.md,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: theme.spacing.md,
  },
  label: {
    ...theme.typography.caption,
    color: theme.colors.textSecondary,
    marginBottom: theme.spacing.sm,
  },
  value: {
    ...theme.typography.h2,
  },
  compactCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: theme.colors.surface,
    borderRadius: theme.borderRadius.lg,
    padding: theme.spacing.md,
    marginBottom: theme.spacing.md,
    borderLeftWidth: 4,
    ...theme.shadows.small,
  },
  compactIconContainer: {
    width: 36,
    height: 36,
    borderRadius: theme.borderRadius.sm,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: theme.spacing.md,
  },
  compactContent: {
    flex: 1,
  },
  compactLabel: {
    ...theme.typography.caption,
    color: theme.colors.textSecondary,
    marginBottom: 2,
  },
  compactValue: {
    ...theme.typography.amount,
    fontSize: 20,
  },
})
