import { useEffect } from 'react'

import styles from '../CurrencyRowList.module.scss'

import clsx from '$/shared/helpers/clsx'
import useCurrencyStore from '$/shared/storage/currency'

export const CryptoList = () => {
	const setCurrencyType = useCurrencyStore(state => state.setToCurrencyType)
	const currencyType = useCurrencyStore(state => state.toCurrencyType)

	const currencyItems = [{ id: 'crypto', name: 'Криптовалюты' }]
	useEffect(() => {
		setCurrencyType('crypto')
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [])

	return (
		<ul className={styles.list}>
			{currencyItems.map(currency => {
				const className = clsx(
					styles.listItem,
					{
						[styles.active]: currency.id === currencyType,
					},
					[],
				)
				return (
					<li key={currency.id} className={className}>
						{currency.name}
					</li>
				)
			})}
		</ul>
	)
}
