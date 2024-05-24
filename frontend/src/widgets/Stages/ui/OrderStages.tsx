import { TitledBlock } from '$/shared/ui/global/TitledBlock'
import styles from './OrderStages.module.scss'
import { Stages } from './Stages/Stages'
import { TechSupport } from './TechSupport/TechSupport'

export const OrderStages = () => {
	return (
		<div className={styles.container}>
			<TitledBlock title="Этапы оформления" hasBackground={false}>
				<Stages />
			</TitledBlock>
			<TitledBlock title="Бот тех поддержки" hasBackground={false}>
				<TechSupport />
			</TitledBlock>
		</div>
	)
}
