import Button from '$/shared/ui/kit/Button/Button'
import ButtonCancel from '$/shared/ui/kit/ButtonCancel/CancelButton'
import ModalWindow from '$/shared/ui/modals/ModalWindow'
import icon from './icon.svg'
import styles from './index.module.scss'

interface Props {
	confirmFn: () => void
	closeFn: () => void
}
const OperationCancel = ({ closeFn, confirmFn }: Props) => {
	return (
		<ModalWindow icon={<img src={icon} alt="accept" />}>
			<h1 className={styles.modalTitle}>Эту операцию нельзя отменить</h1>
			<Button onClick={confirmFn}>Подтверждаю</Button>
			<ButtonCancel onClick={closeFn}>Отмена</ButtonCancel>
		</ModalWindow>
	)
}

export default OperationCancel
