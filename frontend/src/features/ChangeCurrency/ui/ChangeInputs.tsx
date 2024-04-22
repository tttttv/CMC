import { useQuery } from '@tanstack/react-query'
import { AxiosError } from 'axios'
import { useEffect, useRef, useState } from 'react'

import { validateCurrencyInput } from '../lib/validation'

import { currencyAPI } from '$/shared/api/currency'
import useCurrencyStore from '$/shared/storage/currency'
import usePlaceOrder from '$/shared/storage/placeOrder'
import Input from '$/shared/ui/kit/Input'
import { ErrorModal } from '$/shared/ui/modals/ErrorModal'
import styles from './ChangeInputs.module.scss'
import arrows from './images/arrows.jpg'

const DELAY = 1000
export const ChangeInputs = () => {
	const fromCurrency = useCurrencyStore(state => state.fromCurrency)
	const fromCurrencyType = useCurrencyStore(state => state.fromCurrencyType)
	const toCurrency = useCurrencyStore(state => state.toCurrency)

	const chain = usePlaceOrder(state => state.chain)
	const setAmount = usePlaceOrder(state => state.setAmount)
	const setBestP2P = usePlaceOrder(state => state.setBestP2P)
	const setBestP2PPrice = usePlaceOrder(state => state.setBestP2PPrice)

	const savedCryptoAmount = useRef('')
	const savedBankAmount = useRef('')
	const timeout = useRef<NodeJS.Timeout>()

	const [bankChanging, setBankChanging] = useState(false)
	const [tokenChanging, setTokenChanging] = useState(false)
	const [showErrorModal, setShowErrorModal] = useState(false)

	const [bankAmount, setBankAmount] = useState<string>('')
	const [cryptoAmount, setCryptoAmount] = useState<string>('')
	const [price, setPriceField] = useState<string>('')
	const [profit, setProfit] = useState(0)
	const [errorCode, setErrorCode] = useState(-1)

	const cryptoData = useQuery({
		queryKey: ['crypto'],
		queryFn: currencyAPI.getCryptoTokens,
		select: data => data.data.methods,
	})
	const banksData = useQuery({
		queryKey: ['banks'],
		queryFn: currencyAPI.getBanks,
		select: data => data.data.methods,
	})

	const priceProps = {
		chain,
		payment_method: fromCurrency,
		token: toCurrency,
	}
	const {
		refetch: tokenRefetch,
		data: tokenData,
		error: tokenError,
	} = useQuery({
		queryKey: [],
		queryFn: () =>
			currencyAPI.getPrice({
				anchor: 'token',
				quantity: +cryptoAmount,
				...priceProps,
			}),
		enabled: false,
	})

	const {
		refetch: bankRefetch,
		data: bankData,
		error: bankError,
	} = useQuery({
		queryKey: [],
		queryFn: () =>
			currencyAPI.getPrice({
				anchor: 'currency',
				amount: +bankAmount,
				...priceProps,
			}),
		enabled: false,
	})

	useEffect(() => {
		if (bankAmount !== '' && cryptoAmount !== '' && toCurrency) {
			setBankChanging(true)
			if (timeout.current) clearTimeout(timeout.current)
			timeout.current = setTimeout(() => {
				tokenRefetch()
			}, DELAY)
		}
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [fromCurrency])
	useEffect(() => {
		if (bankAmount !== '' && cryptoAmount !== '' && fromCurrency) {
			setTokenChanging(true)
			if (timeout.current) clearTimeout(timeout.current)
			timeout.current = setTimeout(() => {
				bankRefetch()
			}, DELAY)
		}
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [toCurrency])

	useEffect(() => {
		setCryptoAmount(`${bankData?.data.quantity || ''}`)
		savedCryptoAmount.current = `${bankData?.data.quantity || ''}`
		setPriceField(`${bankData?.data.price || ''}`)
		setProfit(bankData?.data.better_amount || 0)
		setBestP2P(bankData?.data.best_p2p || '')
		setBestP2PPrice(bankData?.data.best_p2p_price || 0)

		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [bankData?.data])

	useEffect(() => {
		setBankAmount(`${tokenData?.data.amount || ''}`)
		savedBankAmount.current = `${bankData?.data.amount || ''}`
		setPriceField(`${tokenData?.data.price || ''}`)
		setProfit(tokenData?.data.better_amount || 0)
		setBestP2P(tokenData?.data.best_p2p || '')
		setBestP2PPrice(bankData?.data.best_p2p_price || 0)

		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [tokenData?.data])
	useEffect(() => {
		setAmount(+bankAmount)
		setBankChanging(false)

		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [bankAmount])
	useEffect(() => {
		setTokenChanging(false)
	}, [cryptoAmount])

	const resetData = (errorCode: number | undefined) => {
		if (errorCode === 2 || errorCode === 3) {
			setErrorCode(errorCode)
			setShowErrorModal(true)
		}

		setBestP2P('')
		setBankAmount('')
		setCryptoAmount('')
		savedBankAmount.current = ''
		savedCryptoAmount.current = ''
		setPriceField('')
		setProfit(0)
		setBankChanging(false)
		setTokenChanging(false)
	}
	useEffect(() => {
		const errorCode =
			(bankError as AxiosError<{ code: number }>)?.response?.data.code ||
			(tokenError as AxiosError<{ code: number }>)?.response?.data.code

		// 2 - can't price
		// 3 - zero input
		if (errorCode === 2) resetData(2)

		if (errorCode === 3) resetData(3)
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [bankError, tokenError])

	const token = cryptoData.data?.find(token => token.id == toCurrency)
	const bank = banksData.data
		?.find(currency => {
			return currency.id === fromCurrencyType || fromCurrencyType === 'all'
		})
		?.payment_methods.find(bank => `${bank.id}` === fromCurrency)

	const isInputDisabled = !token || !bank || !chain
	const currency = fromCurrencyType === 'all' ? 'RUB' : fromCurrencyType
	const isUpdateButtonVisible = !isInputDisabled && bankAmount && !tokenChanging
	const isValueChanging = bankChanging || tokenChanging
	const isExchangeRateVisible = token?.name && price && currency
	const isBestRateVisible = currency && profit

	return (
		<>
			{showErrorModal && (
				<ErrorModal
					text={
						errorCode === 3
							? 'Ошибка получения цены. Попробуйте другую цену или другой способ пополнения'
							: ''
					}
					closeFunction={() => {
						setErrorCode(-1)
						setShowErrorModal(false)
					}}
					useMyFunction
				/>
			)}
			<div className={styles.changeInputs}>
				<Input
					disabled={isInputDisabled || bankChanging}
					value={bankChanging ? 'Рассчитываем...' : bankAmount}
					disabledStyle={true}
					label="Отдаете"
					onChange={e => {
						const formattedValue = validateCurrencyInput(e.target.value)
						if (!formattedValue) return

						setTokenChanging(true)
						setBankAmount(formattedValue)

						if (timeout.current) clearTimeout(timeout.current)

						timeout.current = setTimeout(() => {
							if (`${+formattedValue}` === savedBankAmount.current) {
								setTokenChanging(false)

								return
							}
							bankRefetch()
							if ([2, 3].includes(errorCode)) {
								setErrorCode(-1)
								setCryptoAmount(`${bankData?.data.quantity || ''}`)
							}
						}, DELAY)
					}}
					iconUrl={bank?.logo || ''}
					iconAlt={bank?.bank_name || ''}
				/>
				<Input
					value={tokenChanging ? 'Рассчитываем...' : cryptoAmount}
					disabled={isInputDisabled || tokenChanging}
					disabledStyle={true}
					label="Получаете"
					onChange={e => {
						const formattedValue = validateCurrencyInput(e.target.value)
						if (!formattedValue) return

						setCryptoAmount(formattedValue)
						setBankChanging(true)

						if (timeout.current) clearTimeout(timeout.current)

						timeout.current = setTimeout(() => {
							if (`${+formattedValue}` === savedCryptoAmount.current) {
								setBankChanging(false)
								return
							}

							tokenRefetch()
							if ([2, 3].includes(errorCode)) {
								setErrorCode(-1)
								setBankAmount(`${tokenData?.data.amount || ''}`)
							}
						}, DELAY)
					}}
					iconUrl={token?.logo || ''}
					iconAlt={token?.name || ''}
				/>

				<div className={styles.exchangeRate}>
					<h3 className={styles.exchangeRateTitle}>
						<span className={styles.exchangeRateText}>Курс обмена</span>
						<span className={styles.exchangeRateValue}>
							{isExchangeRateVisible ? (
								<>
									{isValueChanging ? '...' : price} {currency} = 1 {token?.name}
								</>
							) : (
								'---'
							)}
						</span>
					</h3>
					<h3 className={styles.exchangeRateTitle}>
						<span className={styles.exchangeRateText}>Курс выгоднее с</span>
						<span className={styles.exchangeRateValue}>
							{isBestRateVisible ? (
								<>
									{isValueChanging ? '...' : profit} {currency}
								</>
							) : (
								'---'
							)}
						</span>
					</h3>
				</div>

				{isUpdateButtonVisible && (
					<button
						className={styles.refetchButton}
						onClick={() => {
							setTokenChanging(true)
							if (timeout.current) clearTimeout(timeout.current)
							timeout.current = setTimeout(() => {
								bankRefetch()
								setCryptoAmount(`${bankData?.data.quantity || ''}`)
								setTokenChanging(false)
							}, DELAY)
						}}
					>
						<img src={arrows} alt="запрос курса" />
					</button>
				)}
			</div>
		</>
	)
}
