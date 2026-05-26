import { View, Text, StyleSheet, TouchableOpacity, Alert } from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { Ionicons } from '@expo/vector-icons'
import { useAuth } from '../context/AuthContext'

export default function UserInfoScreen({ navigation }) {
  const { user, logout } = useAuth()

  const handleLogout = () => {
    Alert.alert('退出登录', '确定要退出登录吗？', [
      { text: '取消', style: 'cancel' },
      { text: '退出', style: 'destructive', onPress: logout },
    ])
  }

  if (!user) return null

  const infoItems = [
    { label: '用户ID', value: user.id, icon: 'key-outline' },
    { label: '用户名', value: user.username, icon: 'person-outline' },
    { label: '创建时间', value: user.createTime, icon: 'time-outline' },
    { label: '更新时间', value: user.updateTime, icon: 'refresh-outline' },
  ]

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>我的</Text>
      </View>

      <View style={styles.profileCard}>
        <View style={styles.avatar}>
          <Ionicons name="person" size={32} color="#fff" />
        </View>
        <Text style={styles.username}>{user.username}</Text>
        <Text style={styles.userId}>ID: {user.id}</Text>
      </View>

      <View style={styles.infoCard}>
        {infoItems.map((item, index) => (
          <View key={item.label} style={[
            styles.infoRow,
            index < infoItems.length - 1 && styles.infoRowBorder,
          ]}>
            <View style={styles.infoLeft}>
              <Ionicons name={item.icon} size={18} color="#8c8c8c" />
              <Text style={styles.infoLabel}>{item.label}</Text>
            </View>
            <Text style={styles.infoValue}>{item.value}</Text>
          </View>
        ))}
      </View>

      <TouchableOpacity
        style={styles.menuItem}
        onPress={() => navigation.navigate('ChangePassword')}
      >
        <View style={styles.menuLeft}>
          <Ionicons name="lock-closed-outline" size={20} color="#18181b" />
          <Text style={styles.menuText}>修改密码</Text>
        </View>
        <Ionicons name="chevron-forward" size={18} color="#d9d9d9" />
      </TouchableOpacity>

      <TouchableOpacity style={styles.logoutBtn} onPress={handleLogout}>
        <Text style={styles.logoutBtnText}>退出登录</Text>
      </TouchableOpacity>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fafafa',
  },
  header: {
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
  profileCard: {
    alignItems: 'center',
    paddingVertical: 28,
    backgroundColor: '#fff',
    marginBottom: 12,
  },
  avatar: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: '#18181b',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 12,
  },
  username: {
    fontSize: 18,
    fontWeight: '600',
    color: '#18181b',
    marginBottom: 4,
  },
  userId: {
    fontSize: 13,
    color: '#8c8c8c',
  },
  infoCard: {
    backgroundColor: '#fff',
    marginBottom: 12,
    paddingHorizontal: 20,
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 14,
  },
  infoRowBorder: {
    borderBottomWidth: 1,
    borderBottomColor: '#f5f5f5',
  },
  infoLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  infoLabel: {
    fontSize: 14,
    color: '#595959',
  },
  infoValue: {
    fontSize: 14,
    color: '#18181b',
    fontWeight: '500',
  },
  menuItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#fff',
    paddingHorizontal: 20,
    paddingVertical: 16,
    marginBottom: 12,
  },
  menuLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  menuText: {
    fontSize: 15,
    color: '#18181b',
  },
  logoutBtn: {
    marginHorizontal: 20,
    marginTop: 20,
    height: 48,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#ff4d4f',
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#fff',
  },
  logoutBtnText: {
    fontSize: 16,
    fontWeight: '500',
    color: '#ff4d4f',
  },
})
