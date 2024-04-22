import { useQuery } from '@tanstack/react-query'

import styles from '../CurrencyRowList.module.scss'

import { currencyAPI } from '$/shared/api/currency'
import clsx from '$/shared/helpers/clsx'
import useCurrencyStore from '$/shared/storage/currency'

export const BankList = () => {
	const { data } = useQuery({
		queryKey: ['banks'],
		queryFn: currencyAPI.getBanks,
	})

	const currencyItems = data?.data.methods

	const setCurrencyType = useCurrencyStore(state => state.setFromCurrencyType)
	const currencyType = useCurrencyStore(state => state.fromCurrencyType)

	// if (isError) {
	// 	return 'Error :('
	// }

	// if (isLoading) {
	// 	return 'Loading...'
	// }

	return (
		<ul className={styles.list}>
			<li
				className={clsx(
					styles.listItem,
					{ [styles.active]: currencyType === 'all' },
					[],
				)}
			>
				<button onClick={() => setCurrencyType('all')}>Все</button>
			</li>
			{currencyItems?.map(currency => {
				const className = clsx(
					styles.listItem,
					{
						[styles.active]: currency.id === currencyType,
					},
					[],
				)

				const setCurrency = () => {
					setCurrencyType(currency.id)
				}

				return (
					<li key={currency.id} className={className}>
						<button onClick={setCurrency}>{currency.name}</button>
					</li>
				)
			})}
		</ul>
	)
}
