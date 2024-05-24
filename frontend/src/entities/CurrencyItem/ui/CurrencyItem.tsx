import clsx from '$/shared/helpers/clsx'
import { CurrencyIcon } from '$/shared/ui/other/CurrencyIcon'
import styles from './CurrencyItem.module.scss'

interface Props {
	name: string
	image: string
	crypto?: boolean
}
export const CurrencyItem = ({ name, image, crypto = false }: Props) => {
	const cryptoContainer = clsx(
		styles.cryptoContainer,
		{
			[styles.exist]: crypto,
		},
		[],
	)
	return (
		<div className={styles.item}>
			<div className={cryptoContainer}>
				<div className={styles.icon}>
					<CurrencyIcon currencyName={name} imageUrl={image} width={32} />
				</div>
				<span className={styles.name}>{name}</span>
			</div>
		</div>
	)
}
