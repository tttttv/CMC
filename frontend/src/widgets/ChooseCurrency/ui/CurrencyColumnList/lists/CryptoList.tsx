import { useQuery } from '@tanstack/react-query'

import styles from '../CurrencyColumnList.module.scss'

import CurrencyItem from '$/entities/CurrencyItem'
import { currencyAPI } from '$/shared/api/currency'
import clsx from '$/shared/helpers/clsx'
import useCurrencyStore from '$/shared/storage/currency'
import LoadingScreen from '$/shared/ui/global/LoadingScreen'
import ScrollableList from '$/shared/ui/other/ScrollList'

export const CryptoList = () => {
	const { data, isLoading } = useQuery({
		queryKey: ['crypto'],
		queryFn: currencyAPI.getCryptoTokens,
		select: data => data.data.methods,
	})

	const toCurrency = useCurrencyStore(state => state.toCurrency)
	const setToCurrency = useCurrencyStore(state => state.setToCurrency)

	return (
		<ScrollableList>
			{isLoading ? (
				<LoadingScreen inContainer>Грузим криптовалюты</LoadingScreen>
			) : (
				<div className={styles.list}>
					{data?.map(token => {
						const className = clsx(
							styles.listItem,
							{ [styles.active]: `${toCurrency}` === `${token.id}` },
							[],
						)
						return (
							<div key={token.id} className={className}>
								<button
									className={styles.itemButton}
									onClick={() => setToCurrency(String(token.id))}
								></button>
								<CurrencyItem name={token.name} image={token.logo} />
							</div>
						)
					})}
				</div>
			)}
		</ScrollableList>
	)
}
