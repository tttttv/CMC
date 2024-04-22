import { useQuery } from '@tanstack/react-query'

import styles from '../CurrencyColumnList.module.scss'

import CurrencyItem from '$/entities/CurrencyItem'
import { currencyAPI } from '$/shared/api/currency'
import clsx from '$/shared/helpers/clsx'
import useCurrencyStore from '$/shared/storage/currency'
import LoadingScreen from '$/shared/ui/global/LoadingScreen'
import ScrollableList from '$/shared/ui/other/ScrollList'

export const BankList = () => {
	const { data, isLoading } = useQuery({
		queryKey: ['banks'],
		queryFn: currencyAPI.getBanks,
	})
	const fromCurrencyType = useCurrencyStore(state => state.fromCurrencyType)
	const fromCurrency = useCurrencyStore(state => state.fromCurrency)
	const setFromCurrency = useCurrencyStore(state => state.setFromCurrency)

	const banks =
		fromCurrencyType === 'all'
			? data?.data.methods.map(bank => bank.payment_methods).flat()
			: data?.data.methods.find(bank => bank.id === fromCurrencyType)
					?.payment_methods

	return (
		<ScrollableList>
			{isLoading ? (
				<LoadingScreen inContainer>Грузим банки</LoadingScreen>
			) : (
				<div className={styles.list}>
					{banks?.map(bank => {
						const className = clsx(
							styles.listItem,
							{ [styles.active]: `${fromCurrency}` === `${bank.id}` },
							[],
						)
						return (
							<div key={bank.id} className={className}>
								<CurrencyItem name={bank.bank_name} image={bank.logo} />
								<button
									className={styles.itemButton}
									onClick={() => setFromCurrency(String(bank.id))}
								></button>
							</div>
						)
					})}
				</div>
			)}
		</ScrollableList>
	)
}
