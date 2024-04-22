import { ReactNode } from '@tanstack/react-router'

import styles from './CancelButton.module.scss'

interface ButtonProps {
	children: ReactNode
	onClick?: () => void
}

export default function ButtonCancel({ children, onClick }: ButtonProps) {
	return (
		<>
			<button className={styles.buttonCancel} onClick={onClick}>
				{children}
			</button>
		</>
	)
}
