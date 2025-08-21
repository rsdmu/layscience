import clsx from 'classnames'
import React from 'react'

export default function Button({children, className, ...props}: React.ButtonHTMLAttributes<HTMLButtonElement> & {variant?: 'solid'|'ghost'}) {
  const classes = clsx(
    'inline-flex items-center justify-center whitespace-nowrap rounded-md border border-black/10 px-4 py-2 text-sm font-medium shadow-sm transition',
    'bg-black text-white hover:bg-black/90 focus:outline-none focus:ring-2 focus:ring-black',
    className
  )
  return <button className={classes} {...props}>{children}</button>
}
