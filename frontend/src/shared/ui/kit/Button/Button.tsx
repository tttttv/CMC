import { ReactNode } from '@tanstack/react-router'
import { ButtonHTMLAttributes } from 'react'

import clsx from '$/shared/helpers/clsx'
import styles from './Button.module.scss'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
	children: ReactNode
	linkBehavior?: {
		enabled: boolean
		to?: string
		target?: '_blank' | '_self' | '_parent' | '_top'
	}
}

const Button = ({
	children,
	linkBehavior = { enabled: false },
	className = '',
	...props
}: ButtonProps) => {
	const buttonClassName = clsx(styles.button, {}, [className])
	if (linkBehavior.enabled) {
		return (
			<a
				className={buttonClassName}
				href={linkBehavior.to}
				target={linkBehavior.target}
			>
				{children}
			</a>
		)
	}
	return (
		<button className={buttonClassName} {...props}>
			{children}
		</button>
	)
}

export default Button
