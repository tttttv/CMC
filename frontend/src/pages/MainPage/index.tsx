import ChangeCurrency from '$/features/ChangeCurrency'
import Page from '$/shared/ui/global/Page'
import ChooseCurrency from '$/widgets/ChooseCurrency'
import styles from './index.module.scss'

export const MainPage = () => (
	<Page>
		<div className={styles.container}>
			<ChooseCurrency title="Вы отправляете" changingProperty="sending" />
			<ChooseCurrency title="Вы получаете" changingProperty="getting" />
			<ChangeCurrency />
		</div>
	</Page>
)
