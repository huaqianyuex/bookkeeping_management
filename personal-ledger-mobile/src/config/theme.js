// 统一主题配置
export const theme = {
  // 颜色系统
  colors: {
    primary: '#1a1a2e',
    primaryLight: '#16213e',
    accent: '#e94560',
    accentLight: '#ff6b6b',
    
    success: '#00b894',
    successLight: '#55efc4',
    error: '#e94560',
    errorLight: '#ff7675',
    
    background: '#f8f9fa',
    surface: '#ffffff',
    surfaceHover: '#f1f3f5',
    
    text: '#2d3436',
    textSecondary: '#636e72',
    textLight: '#b2bec3',
    
    border: '#e9ecef',
    borderLight: '#f1f3f5',
    
    shadow: 'rgba(0, 0, 0, 0.08)',
    shadowDark: 'rgba(0, 0, 0, 0.15)',
  },
  
  // 间距系统
  spacing: {
    xs: 4,
    sm: 8,
    md: 16,
    lg: 24,
    xl: 32,
  },
  
  // 圆角系统
  borderRadius: {
    sm: 8,
    md: 12,
    lg: 16,
    xl: 20,
    full: 9999,
  },
  
  // 字体系统
  typography: {
    h1: {
      fontSize: 28,
      fontWeight: '800',
      letterSpacing: -0.5,
    },
    h2: {
      fontSize: 22,
      fontWeight: '700',
      letterSpacing: -0.3,
    },
    h3: {
      fontSize: 18,
      fontWeight: '600',
    },
    body: {
      fontSize: 15,
      fontWeight: '400',
      lineHeight: 1.5,
    },
    caption: {
      fontSize: 12,
      fontWeight: '500',
    },
    amount: {
      fontSize: 24,
      fontWeight: '700',
      letterSpacing: -0.5,
    },
  },
  
  // 阴影系统
  shadows: {
    small: {
      shadowColor: '#000',
      shadowOffset: { width: 0, height: 2 },
      shadowOpacity: 0.06,
      shadowRadius: 8,
      elevation: 2,
    },
    medium: {
      shadowColor: '#000',
      shadowOffset: { width: 0, height: 4 },
      shadowOpacity: 0.1,
      shadowRadius: 12,
      elevation: 4,
    },
    large: {
      shadowColor: '#000',
      shadowOffset: { width: 0, height: 8 },
      shadowOpacity: 0.15,
      shadowRadius: 24,
      elevation: 8,
    },
  },
}

export default theme
