import { useQuery } from '@tanstack/react-query'

import { currencyAPI } from '$/shared/api/currency'
import { orderAPI } from '$/shared/api/order'
import { TitledBlock } from '$/shared/ui/global/TitledBlock'
import { CurrencyIcon } from '$/shared/ui/other/CurrencyIcon'
import styles from './ExchangeDetails.module.scss'

export const ExchangeDetails = () => {
	const { data } = useQuery({
		queryKey: ['order'],
		queryFn: orderAPI.getOrderState,
		retry: 0,
		select: data => data.data,
	})

	const { data: cryptoData } = useQuery({
		queryKey: ['crypto'],
		queryFn: currencyAPI.getCryptoTokens,
		select: data => data.data.methods,
	})

	const { data: banksData } = useQuery({
		queryKey: ['banks'],
		queryFn: currencyAPI.getBanks,
		select: data => data.data.methods,
	})
	const token = cryptoData?.find(token => token.id == data?.order.to.id)
	const bank = banksData
		?.find(bank => bank.id == data?.order.from.currency)
		?.payment_methods.find(
			bank => String(bank.id) === String(data?.order.from.id),
		)
	return (
		<div className={styles.container}>
			<TitledBlock title="Обмен валюты" hasBackground={false}>
				<div className={styles.currencyExchange}>
					<div className={styles.currency}>
						<h3 className={styles.currencyTitle}>Отправляете</h3>
						<div className={styles.currencyInfo}>
							<div className={styles.currencyIcon}>
								<CurrencyIcon
									currencyName={bank?.bank_name || ''}
									imageUrl={bank?.logo || ''}
									width={32}
								/>
							</div>
							<span className={styles.currencyName}>
								{data?.order.amount} {data?.order.from.currency}
							</span>
						</div>
					</div>
					<div className={styles.dividerCurrency} />
					<div className={styles.currency}>
						<h3 className={styles.currencyTitle}>Получаете</h3>
						<div className={styles.currencyInfo}>
							<div className={styles.currencyIcon}>
								<CurrencyIcon
									currencyName={token?.name || ''}
									imageUrl={token?.logo || ''}
									width={32}
								/>
							</div>
							<span className={styles.currencyName}>
								{data?.order.quantity} {token?.name}
							</span>
						</div>
					</div>
				</div>
			</TitledBlock>
			<TitledBlock title="Детали обмена" hasBackground={false}>
				<div className={styles.exchangeRate}>
					<h3 className={styles.exchangeRateTitle}>
						<span className={styles.exchangeRateText}>Курс обмена</span>
						<span className={styles.exchangeRateValue} data-color="green">
							{data?.order.rate.toFixed(3)} {data?.order.from.currency} = 1{' '}
							{data?.order.to.name}
						</span>
					</h3>
					<h3 className={styles.exchangeRateTitle}>
						<span className={styles.exchangeRateText}>Номер обмена</span>
						<span className={styles.exchangeRateValue}>
							{BigInt(data?.order.order_hash || '').toString()}
						</span>
					</h3>
				</div>
			</TitledBlock>
		</div>
	)
}
