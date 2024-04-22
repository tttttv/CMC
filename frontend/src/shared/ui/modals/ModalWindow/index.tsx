import clsx from '$/shared/helpers/clsx'
import styles from './index.module.scss'

interface Props {
	children: React.ReactNode
	icon: React.ReactNode
	windowClassName?: string
	closeFunction?: () => void
}

const ModalWindow = ({
	children,
	icon,
	closeFunction,
	windowClassName,
}: Props) => {
	const className = clsx(styles.modalWindow, {}, [windowClassName || ''])
	return (
		<div className={className}>
			<div className={styles.modalHeader}>
				<div className={styles.modalIcon}>{icon}</div>
			</div>
			<div className={styles.modalContent}>{children}</div>
			{closeFunction && (
				<button className={styles.closeButton} onClick={() => closeFunction()}>
					&#10006;
				</button>
			)}
		</div>
	)
}

export default ModalWindow
