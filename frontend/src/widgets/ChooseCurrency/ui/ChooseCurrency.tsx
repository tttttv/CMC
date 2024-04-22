import clsx from '$/shared/helpers/clsx'
import { TitledBlock } from '$/shared/ui/global/TitledBlock'
import styles from './ChooseCurrency.module.scss'
import { CurrencyColumnList } from './CurrencyColumnList/CurrencyColumnList'
import { CurrencyRowList } from './CurrencyRowList/CurrencyRowList'

interface Props {
	title: string
	changingProperty: string
}
export const ChooseCurrency = ({ title, changingProperty }: Props) => {
	const isGetting = changingProperty === 'getting'
	const bankClassName = clsx(
		styles.chooseCurrencyBank,
		{ [styles.active]: !isGetting },
		[],
	)
	const cryptoClassName = clsx(
		styles.chooseCurrencyCrypto,
		{ [styles.active]: isGetting },
		[],
	)
	return (
		<TitledBlock title={title}>
			<div className={styles.chooseCurrency}>
				<div className={bankClassName}>Валюта</div>
				<div className={cryptoClassName}>Криптовалюта</div>
			</div>
			<CurrencyRowList property={changingProperty} />
			<CurrencyColumnList property={changingProperty} />
		</TitledBlock>
	)
}
