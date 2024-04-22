import { ErrorModal } from '../../../../shared/ui/modals/ErrorModal'

const ERROR_CODES: Record<number, string> = {
	0: 'Обменник недоступен, попробуйте позже',
	1: 'Обменник недоступен, попробуйте позже',
	2: 'Цена изменилась, попробуйте обновить страницу и снова создать обмен',
}

interface Props {
	errorCode: number
	errorText: string
	closeFn?: () => void
	omitErrorCodeCheck?: boolean
}
export const ErrorCodeModal = ({ errorCode, errorText, closeFn }: Props) => {
	if (!errorCode) return
	if (errorCode < 0 || errorCode > 6) return null
	return (
		<ErrorModal
			text={ERROR_CODES[errorCode] || errorText || ''}
			closeFunction={closeFn}
			useMyFunction={closeFn ? true : false}
		/>
	)
}
