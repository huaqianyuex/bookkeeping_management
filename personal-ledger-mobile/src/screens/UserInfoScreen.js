import { useState, useCallback } from 'react'
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Alert,
  TextInput,
  Image,
  Modal,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { Ionicons } from '@expo/vector-icons'
import * as ImagePicker from 'expo-image-picker'
import { useAuth } from '../context/AuthContext'
import { theme } from '../config/theme'
import { API_BASE_URL } from '../config'
import { updateUserInfo, uploadAvatar } from '../api/user'
import PageHeader from '../components/PageHeader'
import FadeInView from '../components/FadeInView'
import ScaleButton from '../components/ScaleButton'

// ─── 常量 ─────────────────────────────────
const USERNAME_REGEX = /^[A-Za-z0-9\u4e00-\u9fa5]{2,20}$/
const PASSWORD_REGEX = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[A-Za-z\d]{8,16}$/
const MAX_AVATAR_SIZE = 2 * 1024 * 1024  // 2MB

// ─── 辅助函数 ─────────────────────────────
/** 拼接完整的头像 URL */
function getAvatarUrl(avatarUrl) {
  if (!avatarUrl) return null
  if (avatarUrl.startsWith('http://') || avatarUrl.startsWith('https://')) {
    return avatarUrl
  }
  // avatarUrl 格式: /uploads/avatars/xxx.jpg
  // 去掉 API 基地址中的 /api 部分
  const base = API_BASE_URL.replace(/\/api\/?$/, '')
  return base + avatarUrl
}

/** 格式化日期 */
function formatDate(dateStr) {
  if (!dateStr) return '-'
  return dateStr.replace('T', ' ')
}

// ─── 组件 ─────────────────────────────────
export default function UserInfoScreen({ navigation }) {
  const { user, setUser, logout } = useAuth()

  // 头像状态
  const [avatarLoading, setAvatarLoading] = useState(false)

  // 用户名编辑弹窗状态
  const [usernameModalVisible, setUsernameModalVisible] = useState(false)
  const [usernameValue, setUsernameValue] = useState('')
  const [usernameError, setUsernameError] = useState('')
  const [usernameSubmitting, setUsernameSubmitting] = useState(false)

  // ─── 头像选择 ─────────────────────────
  const handlePickAvatar = useCallback(async () => {
    // 请求权限
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync()
    if (status !== 'granted') {
      Alert.alert('权限不足', '请在设置中授予相册访问权限以选择头像')
      return
    }

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      allowsEditing: true,
      aspect: [1, 1],
      quality: 0.8,
      base64: false,
    })

    if (result.canceled || !result.assets || result.assets.length === 0) return

    const asset = result.assets[0]

    // 前端校验文件大小
    if (asset.fileSize && asset.fileSize > MAX_AVATAR_SIZE) {
      Alert.alert('文件过大', '头像大小不能超过 2MB')
      return
    }

    // 前端校验文件类型
    const mimeType = (asset.mimeType || asset.type || '').toLowerCase()
    if (mimeType && !['image/jpeg', 'image/png', 'image/jpg'].includes(mimeType)) {
      Alert.alert('格式不支持', '头像仅支持 JPG/PNG 格式')
      return
    }

    setAvatarLoading(true)
    try {
      const res = await uploadAvatar(asset)
      if (res.code === 200) {
        setUser(res.data)
        Alert.alert('成功', '头像上传成功')
      } else {
        Alert.alert('上传失败', res.message || '头像上传失败，请稍后重试')
      }
    } catch (error) {
      const msg = error?.response?.data?.message || error?.message || '请求失败，请稍后重试'
      Alert.alert('上传失败', msg)
    } finally {
      setAvatarLoading(false)
    }
  }, [setUser])

  // 长按头像用拍照方式
  const handleTakePhoto = useCallback(async () => {
    const { status } = await ImagePicker.requestCameraPermissionsAsync()
    if (status !== 'granted') {
      Alert.alert('权限不足', '请在设置中授予相机权限以拍摄头像')
      return
    }

    const result = await ImagePicker.launchCameraAsync({
      allowsEditing: true,
      aspect: [1, 1],
      quality: 0.8,
    })

    if (result.canceled || !result.assets || result.assets.length === 0) return

    const asset = result.assets[0]

    if (asset.fileSize && asset.fileSize > MAX_AVATAR_SIZE) {
      Alert.alert('文件过大', '头像大小不能超过 2MB')
      return
    }

    setAvatarLoading(true)
    try {
      const res = await uploadAvatar(asset)
      if (res.code === 200) {
        setUser(res.data)
        Alert.alert('成功', '头像上传成功')
      } else {
        Alert.alert('上传失败', res.message || '头像上传失败，请稍后重试')
      }
    } catch (error) {
      const msg = error?.response?.data?.message || error?.message || '请求失败，请稍后重试'
      Alert.alert('上传失败', msg)
    } finally {
      setAvatarLoading(false)
    }
  }, [setUser])

  // ─── 用户名编辑 ─────────────────────────
  const openUsernameModal = useCallback(() => {
    setUsernameValue(user?.username || '')
    setUsernameError('')
    setUsernameModalVisible(true)
  }, [user])

  const handleUsernameChange = useCallback((text) => {
    setUsernameValue(text)
    // 实时校验
    if (text.length === 0) {
      setUsernameError('用户名不能为空')
    } else if (text.length < 2) {
      setUsernameError('用户名至少需要 2 个字符')
    } else if (text.length > 20) {
      setUsernameError('用户名最多 20 个字符')
    } else if (!USERNAME_REGEX.test(text)) {
      setUsernameError('用户名仅支持中英文和数字组合')
    } else {
      setUsernameError('')
    }
  }, [])

  const handleUsernameSubmit = useCallback(async () => {
    const trimmed = usernameValue.trim()
    if (!trimmed) {
      setUsernameError('用户名不能为空')
      return
    }
    if (!USERNAME_REGEX.test(trimmed)) {
      setUsernameError('用户名需为 2-20 位中英文或数字组合')
      return
    }

    setUsernameSubmitting(true)
    try {
      const res = await updateUserInfo({ username: trimmed })
      if (res.code === 200) {
        setUser(res.data)
        setUsernameModalVisible(false)
        Alert.alert('成功', '用户名更新成功')
      } else {
        setUsernameError(res.message || '用户名更新失败')
      }
    } catch (error) {
      const msg = error?.response?.data?.message || error?.message || '请求失败，请稍后重试'
      setUsernameError(msg)
    } finally {
      setUsernameSubmitting(false)
    }
  }, [usernameValue, setUser])

  // ─── 退出 ───────────────────────────────
  const handleLogout = useCallback(() => {
    Alert.alert('退出登录', '确定要退出登录吗？', [
      { text: '取消', style: 'cancel' },
      { text: '退出', style: 'destructive', onPress: logout },
    ])
  }, [logout])

  // ─── 渲染 ───────────────────────────────
  if (!user) return null

  const avatarSrc = getAvatarUrl(user.avatarUrl)
  const infoItems = [
    { label: '用户ID', value: String(user.id), icon: 'key-outline', color: theme.colors.textSecondary },
    { label: '用户名', value: user.username, icon: 'person-outline', color: theme.colors.primary },
    { label: '创建时间', value: formatDate(user.createTime), icon: 'time-outline', color: theme.colors.success },
    { label: '更新时间', value: formatDate(user.updateTime), icon: 'refresh-outline', color: theme.colors.success },
  ]

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <PageHeader title="我的" />

      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <ScrollView
          style={{ flex: 1 }}
          contentContainerStyle={styles.scrollContent}
          showsVerticalScrollIndicator={false}
        >
          <FadeInView>
            {/* 头像卡片 */}
            <View style={styles.profileCard}>
              <TouchableOpacity
                style={styles.avatarContainer}
                onPress={handlePickAvatar}
                onLongPress={handleTakePhoto}
                activeOpacity={0.8}
              >
                {avatarSrc ? (
                  <Image source={{ uri: avatarSrc }} style={styles.avatarImage} />
                ) : (
                  <View style={styles.avatarPlaceholder}>
                    <Ionicons name="person" size={40} color={theme.colors.surface} />
                  </View>
                )}
                {avatarLoading ? (
                  <View style={styles.avatarOverlay}>
                    <ActivityIndicator color="#fff" size="small" />
                  </View>
                ) : (
                  <View style={styles.avatarBadge}>
                    <Ionicons name="camera" size={14} color="#fff" />
                  </View>
                )}
                <View style={styles.onlineIndicator} />
              </TouchableOpacity>

              <Text style={styles.avatarHint}>点击更换头像，长按拍照</Text>

              {/* 用户名 + 编辑按钮 */}
              <View style={styles.usernameRow}>
                <Text style={styles.username}>{user.username}</Text>
                <TouchableOpacity onPress={openUsernameModal} style={styles.editBtn}>
                  <Ionicons name="create-outline" size={18} color={theme.colors.primary} />
                </TouchableOpacity>
              </View>

              <View style={styles.userIdBadge}>
                <Ionicons name="finger-print" size={14} color={theme.colors.textSecondary} />
                <Text style={styles.userId}>ID: {user.id}</Text>
              </View>
            </View>

            {/* 个人信息卡片 */}
            <View style={styles.infoCard}>
              <Text style={styles.cardTitle}>个人信息</Text>
              {infoItems.map((item, index) => (
                <View
                  key={item.label}
                  style={[
                    styles.infoRow,
                    index < infoItems.length - 1 && styles.infoRowBorder,
                  ]}
                >
                  <View style={styles.infoLeft}>
                    <View style={[styles.infoIcon, { backgroundColor: `${item.color}15` }]}>
                      <Ionicons name={item.icon} size={16} color={item.color} />
                    </View>
                    <Text style={styles.infoLabel}>{item.label}</Text>
                  </View>
                  <Text style={styles.infoValue} numberOfLines={1}>
                    {item.value}
                  </Text>
                </View>
              ))}
            </View>

            {/* 功能菜单 */}
            <View style={styles.menuCard}>
              <ScaleButton
                style={styles.menuItem}
                onPress={() => navigation.navigate('AiChat')}
              >
                <View style={styles.menuLeft}>
                  <View style={[styles.menuIcon, { backgroundColor: `${theme.colors.primary}15` }]}>
                    <Ionicons name="robot" size={18} color={theme.colors.primary} />
                  </View>
                  <Text style={styles.menuText}>AI记账助手</Text>
                </View>
                <View style={styles.menuRight}>
                  <Ionicons name="chevron-forward" size={18} color={theme.colors.textLight} />
                </View>
              </ScaleButton>
              <ScaleButton
                style={[styles.menuItem, styles.menuItemBorder]}
                onPress={() => navigation.navigate('ChangePassword')}
              >
                <View style={styles.menuLeft}>
                  <View style={[styles.menuIcon, { backgroundColor: `${theme.colors.success}15` }]}>
                    <Ionicons name="lock-closed" size={18} color={theme.colors.success} />
                  </View>
                  <Text style={styles.menuText}>修改密码</Text>
                </View>
                <View style={styles.menuRight}>
                  <Ionicons name="chevron-forward" size={18} color={theme.colors.textLight} />
                </View>
              </ScaleButton>
            </View>

            {/* 退出按钮 */}
            <ScaleButton style={styles.logoutBtn} onPress={handleLogout}>
              <Ionicons name="log-out-outline" size={20} color={theme.colors.error} />
              <Text style={styles.logoutBtnText}>退出登录</Text>
            </ScaleButton>
          </FadeInView>
        </ScrollView>
      </KeyboardAvoidingView>

      {/* ─── 用户名编辑弹窗 ─── */}
      <Modal
        visible={usernameModalVisible}
        transparent
        animationType="fade"
        onRequestClose={() => setUsernameModalVisible(false)}
      >
        <TouchableOpacity
          style={styles.modalBackdrop}
          activeOpacity={1}
          onPress={() => setUsernameModalVisible(false)}
        >
          <TouchableOpacity
            style={styles.modalCard}
            activeOpacity={1}
            onPress={() => {}}
          >
            <Text style={styles.modalTitle}>修改用户名</Text>
            <Text style={styles.modalDesc}>
              支持 2-20 个字符的中文、英文和数字组合
            </Text>

            <TextInput
              style={[styles.modalInput, usernameError ? styles.modalInputError : null]}
              value={usernameValue}
              onChangeText={handleUsernameChange}
              placeholder="请输入新用户名"
              placeholderTextColor={theme.colors.textLight}
              maxLength={20}
              autoFocus
              selectionColor={theme.colors.primary}
            />
            {usernameError ? (
              <Text style={styles.modalError}>{usernameError}</Text>
            ) : null}

            <View style={styles.modalActions}>
              <TouchableOpacity
                style={styles.modalCancelBtn}
                onPress={() => setUsernameModalVisible(false)}
              >
                <Text style={styles.modalCancelText}>取消</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[
                  styles.modalConfirmBtn,
                  (!!usernameError || usernameSubmitting) && styles.modalConfirmBtnDisabled,
                ]}
                onPress={handleUsernameSubmit}
                disabled={!!usernameError || usernameSubmitting}
              >
                {usernameSubmitting ? (
                  <ActivityIndicator color="#fff" size="small" />
                ) : (
                  <Text style={styles.modalConfirmText}>确认修改</Text>
                )}
              </TouchableOpacity>
            </View>
          </TouchableOpacity>
        </TouchableOpacity>
      </Modal>
    </SafeAreaView>
  )
}

// ─── 样式 ─────────────────────────────────
const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  scrollContent: {
    padding: theme.spacing.md,
    paddingBottom: theme.spacing.xl,
  },

  // ── 头像卡片 ──
  profileCard: {
    alignItems: 'center',
    paddingVertical: theme.spacing.xl,
    backgroundColor: theme.colors.surface,
    borderRadius: theme.borderRadius.xl,
    marginBottom: theme.spacing.md,
    ...theme.shadows.small,
  },
  avatarContainer: {
    position: 'relative',
    marginBottom: theme.spacing.sm,
  },
  avatarImage: {
    width: 88,
    height: 88,
    borderRadius: theme.borderRadius.full,
    borderWidth: 3,
    borderColor: theme.colors.border,
  },
  avatarPlaceholder: {
    width: 88,
    height: 88,
    borderRadius: theme.borderRadius.full,
    backgroundColor: theme.colors.primary,
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: theme.colors.primary,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 12,
    elevation: 6,
  },
  avatarOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    borderRadius: theme.borderRadius.full,
    backgroundColor: 'rgba(0,0,0,0.4)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  avatarBadge: {
    position: 'absolute',
    bottom: 0,
    right: 0,
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: theme.colors.accent,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: theme.colors.surface,
  },
  onlineIndicator: {
    position: 'absolute',
    top: 2,
    right: 2,
    width: 14,
    height: 14,
    borderRadius: 7,
    backgroundColor: theme.colors.success,
    borderWidth: 2.5,
    borderColor: theme.colors.surface,
  },
  avatarHint: {
    fontSize: 12,
    color: theme.colors.textLight,
    marginBottom: theme.spacing.md,
  },
  usernameRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: theme.spacing.sm,
  },
  username: {
    ...theme.typography.h2,
    color: theme.colors.primary,
  },
  editBtn: {
    padding: 4,
    borderRadius: theme.borderRadius.sm,
    backgroundColor: `${theme.colors.primary}10`,
  },
  userIdBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: theme.spacing.md,
    paddingVertical: 6,
    backgroundColor: theme.colors.surfaceHover,
    borderRadius: 12,
  },
  userId: {
    fontSize: 13,
    color: theme.colors.textSecondary,
    fontWeight: '500',
  },

  // ── 信息卡片 ──
  infoCard: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.borderRadius.lg,
    padding: theme.spacing.md,
    marginBottom: theme.spacing.md,
    ...theme.shadows.small,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: theme.colors.primary,
    marginBottom: theme.spacing.md,
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: theme.spacing.md,
  },
  infoRowBorder: {
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.borderLight,
  },
  infoLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  infoIcon: {
    width: 32,
    height: 32,
    borderRadius: theme.borderRadius.sm,
    justifyContent: 'center',
    alignItems: 'center',
  },
  infoLabel: {
    fontSize: 14,
    color: theme.colors.textSecondary,
    fontWeight: '500',
  },
  infoValue: {
    fontSize: 14,
    color: theme.colors.text,
    fontWeight: '600',
    flexShrink: 1,
    maxWidth: '55%',
    textAlign: 'right',
  },

  // ── 功能菜单 ──
  menuCard: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.borderRadius.lg,
    marginBottom: theme.spacing.md,
    overflow: 'hidden',
    ...theme.shadows.small,
  },
  menuItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: theme.spacing.md,
    paddingVertical: theme.spacing.md,
  },
  menuItemBorder: {
    borderTopWidth: 1,
    borderTopColor: theme.colors.borderLight,
  },
  menuLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  menuIcon: {
    width: 36,
    height: 36,
    borderRadius: theme.borderRadius.sm,
    justifyContent: 'center',
    alignItems: 'center',
  },
  menuText: {
    fontSize: 15,
    fontWeight: '600',
    color: theme.colors.primary,
  },
  menuRight: {
    padding: 4,
  },

  // ── 退出按钮 ──
  logoutBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    height: 52,
    borderRadius: theme.borderRadius.md,
    borderWidth: 1,
    borderColor: `${theme.colors.error}20`,
    backgroundColor: theme.colors.surface,
    marginTop: theme.spacing.sm,
  },
  logoutBtnText: {
    fontSize: 16,
    fontWeight: '600',
    color: theme.colors.error,
  },

  // ── 编辑弹窗 ──
  modalBackdrop: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.45)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: theme.spacing.lg,
  },
  modalCard: {
    width: '100%',
    maxWidth: 340,
    backgroundColor: theme.colors.surface,
    borderRadius: theme.borderRadius.xl,
    padding: theme.spacing.lg,
    ...theme.shadows.large,
  },
  modalTitle: {
    ...theme.typography.h3,
    color: theme.colors.primary,
    marginBottom: theme.spacing.xs,
  },
  modalDesc: {
    fontSize: 13,
    color: theme.colors.textSecondary,
    marginBottom: theme.spacing.lg,
    lineHeight: 18,
  },
  modalInput: {
    height: 48,
    borderWidth: 1,
    borderColor: theme.colors.border,
    borderRadius: theme.borderRadius.md,
    paddingHorizontal: theme.spacing.md,
    fontSize: 16,
    color: theme.colors.text,
    backgroundColor: theme.colors.background,
  },
  modalInputError: {
    borderColor: theme.colors.error,
  },
  modalError: {
    fontSize: 12,
    color: theme.colors.error,
    marginTop: 6,
    paddingLeft: 4,
  },
  modalActions: {
    flexDirection: 'row',
    gap: 12,
    marginTop: theme.spacing.lg,
  },
  modalCancelBtn: {
    flex: 1,
    height: 44,
    borderRadius: theme.borderRadius.md,
    borderWidth: 1,
    borderColor: theme.colors.border,
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalCancelText: {
    fontSize: 15,
    color: theme.colors.textSecondary,
    fontWeight: '600',
  },
  modalConfirmBtn: {
    flex: 1,
    height: 44,
    borderRadius: theme.borderRadius.md,
    backgroundColor: theme.colors.primary,
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalConfirmBtnDisabled: {
    opacity: 0.5,
  },
  modalConfirmText: {
    fontSize: 15,
    color: '#fff',
    fontWeight: '600',
  },
})
