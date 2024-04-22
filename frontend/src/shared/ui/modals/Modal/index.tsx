import { createPortal } from 'react-dom'

import clsx from '$/shared/helpers/clsx'
import styles from './index.module.scss'

interface Props {
	children: React.ReactNode
	modalClassName?: string
	opened: boolean
	closeByClick?: () => void
}

const Modal = ({
	children,
	modalClassName,
	opened,
	closeByClick = () => {},
}: Props) => {
	const className = clsx(styles.modal, {}, [modalClassName || ''])

	return (
		<>
			{opened &&
				createPortal(
					<div
						className={className}
						onClick={
							closeByClick
								? e => {
										if (e.target === e.currentTarget) {
											closeByClick()
										}
									}
								: undefined
						}
					>
						{children}
					</div>,
					document.body,
				)}
		</>
	)
}

export default Modal
