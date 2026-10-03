/**
 * ListToolbar - 列表页筛选/操作工具栏的统一容器（换行对齐、统一间距）
 */
export default function ListToolbar({ children, style }) {
  return (
    <div className="list-toolbar" style={style}>
      {children}
    </div>
  )
}
