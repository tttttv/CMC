import { TitledBlock } from '$/shared/ui/global/TitledBlock'
import styles from './ChangeCurrency.module.scss'
import { ChangeInputs } from './ChangeInputs'
import { UserForm } from './UserForm/UserForm'

export const ChangeCurrency = () => (
	<TitledBlock title="Обмен">
		<ChangeInputs />
		<div className={styles.divider} />
		<UserForm />
	</TitledBlock>
)
