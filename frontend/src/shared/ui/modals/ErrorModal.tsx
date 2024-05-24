import { useEffect, useState } from 'react'

import Modal from '$/shared/ui/modals/Modal'
import ErrorMessage from '$/widgets/ModalWindows/ErrorMessage'

interface Props {
	text?: string
	closeFunction?: () => void
	useMyFunction?: boolean
}

export const ErrorModal = ({
	closeFunction,
	text,
	useMyFunction = false,
}: Props) => {
	const [open, setOpen] = useState(true)
	const handleKeyDown = (e: KeyboardEvent) => {
		if (e.key === 'Escape') {
			closeFunction?.()
		}
	}
	useEffect(() => {
		document.addEventListener('keydown', handleKeyDown)
		return () => {
			document.removeEventListener('keydown', handleKeyDown)
		}
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [])

	return (
		<Modal opened={text ? open : true} closeByClick={() => closeFunction?.()}>
			<ErrorMessage
				closeFunction={
					useMyFunction || !text ? closeFunction! : () => setOpen(false)
				}
				text={text}
			/>
		</Modal>
	)
}
