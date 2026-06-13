import React, { useEffect, useRef } from 'react'
import { View, StyleSheet, Animated } from 'react-native'
import { theme } from '../config/theme'

export default function SkeletonCard({ lines = 3, variant = 'card' }) {
  const opacity = useRef(new Animated.Value(0.4)).current

  useEffect(() => {
    const animation = Animated.loop(
      Animated.sequence([
        Animated.timing(opacity, {
          toValue: 1,
          duration: 800,
          useNativeDriver: true,
        }),
        Animated.timing(opacity, {
          toValue: 0.4,
          duration: 800,
          useNativeDriver: true,
        }),
      ])
    )
    animation.start()
    return () => animation.stop()
  }, [opacity])

  if (variant === 'list') {
    return (
      <View style={styles.listContainer}>
        {Array.from({ length: lines }).map((_, i) => (
          <Animated.View key={i} style={[styles.listRow, { opacity }]}>
            <View style={styles.listIcon} />
            <View style={styles.listContent}>
              <View style={[styles.line, { width: '40%', marginBottom: 8 }]} />
              <View style={[styles.line, { width: '60%' }]} />
            </View>
            <View style={[styles.line, { width: 60 }]} />
          </Animated.View>
        ))}
      </View>
    )
  }

  return (
    <View style={styles.container}>
      {Array.from({ length: lines }).map((_, i) => (
        <Animated.View key={i} style={[styles.card, { opacity }]}>
          <View style={styles.header}>
            <View style={styles.icon} />
            <View style={[styles.line, { width: '30%' }]} />
          </View>
          <View style={[styles.line, { width: '80%', marginTop: 12 }]} />
          <View style={[styles.line, { width: '60%', marginTop: 8 }]} />
        </Animated.View>
      ))}
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    padding: theme.spacing.md,
  },
  card: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.borderRadius.lg,
    padding: theme.spacing.lg,
    marginBottom: theme.spacing.md,
    ...theme.shadows.small,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: theme.spacing.sm,
  },
  icon: {
    width: 36,
    height: 36,
    borderRadius: theme.borderRadius.sm,
    backgroundColor: theme.colors.border,
    marginRight: theme.spacing.md,
  },
  line: {
    height: 12,
    borderRadius: 6,
    backgroundColor: theme.colors.border,
  },
  listContainer: {
    padding: theme.spacing.md,
  },
  listRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: theme.colors.surface,
    borderRadius: theme.borderRadius.md,
    padding: theme.spacing.md,
    marginBottom: theme.spacing.sm,
    ...theme.shadows.small,
  },
  listIcon: {
    width: 40,
    height: 40,
    borderRadius: theme.borderRadius.sm,
    backgroundColor: theme.colors.border,
    marginRight: theme.spacing.md,
  },
  listContent: {
    flex: 1,
  },
})
