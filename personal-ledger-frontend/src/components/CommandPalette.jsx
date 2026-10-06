import { useState, useEffect, useMemo, useRef } from 'react'

/**
 * CommandPalette - ⌘K / Ctrl+K 命令面板
 *
 * @param {Object} props
 * @param {boolean} props.open
 * @param {() => void} props.onClose
 * @param {Array<{ key: string, label: string, icon?: ReactNode, hint?: string, run: () => void }>} props.commands
 */
export default function CommandPalette({ open, onClose, commands }) {
  const [query, setQuery] = useState('')
  const [active, setActive] = useState(0)
  const inputRef = useRef(null)

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return q ? commands.filter(c => c.label.toLowerCase().includes(q)) : commands
  }, [query, commands])

  useEffect(() => {
    if (open) {
      setQuery('')
      setActive(0)
      inputRef.current?.focus()
    }
  }, [open])

  useEffect(() => { setActive(0) }, [query])

  const run = (cmd) => {
    if (!cmd) return
    cmd.run()
    onClose()
  }

  const onKeyDown = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActive(a => Math.min(a + 1, filtered.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActive(a => Math.max(a - 1, 0))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      run(filtered[active])
    } else if (e.key === 'Escape') {
      onClose()
    }
  }

  if (!open) return null

  return (
    <>
      <div className="cmdk-backdrop" onClick={onClose} />
      <div className="cmdk-panel" role="dialog" aria-label="命令面板">
        <input
          ref={inputRef}
          className="cmdk-input"
          value={query}
          placeholder="搜索页面或执行操作…"
          onChange={e => setQuery(e.target.value)}
          onKeyDown={onKeyDown}
        />
        <div className="cmdk-list">
          {filtered.map((c, i) => (
            <div
              key={c.key}
              className={`cmdk-item${i === active ? ' cmdk-item--active' : ''}`}
              onMouseEnter={() => setActive(i)}
              onClick={() => run(c)}
            >
              {c.icon && <span className="cmdk-item__icon">{c.icon}</span>}
              <span className="cmdk-item__label">{c.label}</span>
              {c.hint && <span className="cmdk-item__hint">{c.hint}</span>}
            </div>
          ))}
          {!filtered.length && <div className="cmdk-empty">无匹配结果</div>}
        </div>
      </div>
    </>
  )
}
