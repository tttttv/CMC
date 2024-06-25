import ModalWindow from '$/shared/ui/modals/ModalWindow'
import icon from './icon.svg'
import styles from './index.module.scss'

interface Props {
	text?: string
	closeFunction: () => void
}
const ErrorMessage = ({ closeFunction, text }: Props) => {
	return (
		<ModalWindow
			icon={<img src={icon} alt="Произошла ошибка" />}
			closeFunction={closeFunction}
		>
			<div className={styles.modalDescription}>
				{text ||
					'На данный момент обменник занят, попробуйте провести обмен через 10 минут'}
			</div>
		</ModalWindow>
	)
}

export default ErrorMessage
