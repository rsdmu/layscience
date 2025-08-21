import cx from 'classnames'

export default function Button({ children, onClick, type='button', variant='primary', disabled=false, className }:{
  children: React.ReactNode, onClick?: ()=>void, type?: 'button'|'submit'|'reset', variant?: 'primary'|'secondary'|'ghost', disabled?: boolean, className?: string
}) {
  const base = 'inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2 font-semibold transition'
  const styles = {
    primary: 'bg-accent text-black hover:opacity-90',
    secondary: 'bg-surface text-white border border-border hover:border-accent',
    ghost: 'bg-transparent text-white hover:bg-surface'
  }[variant]
  const disabledCls = disabled ? 'opacity-60 cursor-not-allowed' : ''
  return <button type={type} onClick={onClick} disabled={disabled} className={cx(base, styles, disabledCls, className)}>{children}</button>
}
