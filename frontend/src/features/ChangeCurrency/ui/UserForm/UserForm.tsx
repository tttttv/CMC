import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { AxiosError } from 'axios'
import { useEffect, useState } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { z } from 'zod'

import { deleteSpaces } from '../../lib/form'
import { validateCardInput } from '../../lib/validation'
import { ErrorCodeModal } from '../modals/ErrorCodeModal'

import { currencyAPI } from '$/shared/api/currency'
import { orderAPI } from '$/shared/api/order'
import useCurrencyStore from '$/shared/storage/currency'
import usePlaceOrder from '$/shared/storage/placeOrder'
import { Order } from '$/shared/types/api/params'
import Button from '$/shared/ui/kit/Button/Button'
import Checkbox from '$/shared/ui/kit/Checkbox'
import Input from '$/shared/ui/kit/Input'
import Select from '$/shared/ui/kit/Select'
import styles from './UserForm.module.scss'

const FormSchema = z.object({
	fullName: z
		.string({ required_error: 'Это поле обязательное' })
		.min(1, { message: 'Это поле обязательное' }),
	walletAddress: z
		.string({ required_error: 'Это поле обязательное' })
		.min(1, { message: 'Это поле обязательное' }),
	chain: z.string(),
	cardNumber: z
		.string({ required_error: 'Это поле обязательное' })
		.min(19, { message: 'Номер карты состоит из 16 цифр' })
		.max(19, { message: 'Номер карты состоит из 16 цифр' }),
	email: z
		.string({ required_error: 'Это поле обязательное' })
		.min(1, { message: 'Это поле обязательное' })
		.email({
			message: 'Нужно ввести правильную почту!',
		}),
	agreement: z.boolean(),
	personalData: z.boolean(),
})

export const UserForm = () => {
	const { data } = useQuery({
		queryKey: ['crypto'],
		queryFn: currencyAPI.getCryptoTokens,
		select: data => data.data.methods,
	})
	const fromCurrency = useCurrencyStore(state => state.fromCurrency)
	const toCurrency = useCurrencyStore(state => state.toCurrency)
	const chains = data?.find(chain => chain.id === toCurrency)?.chains || []
	const [error, setErrorCode] = useState<{ code: number; message: string }>({
		code: -1,
		message: '',
	})

	const {
		control,
		handleSubmit,
		formState: { errors },
		register,
		watch,
		clearErrors,
		setError,
		setValue,
	} = useForm<z.infer<typeof FormSchema>>({
		resolver: zodResolver(FormSchema),
	})

	const { mutate: createOrder, isPending: isOrderCreating } = useMutation({
		mutationKey: ['order'],
		mutationFn: orderAPI.createOrder,
		onSuccess: data => {
			const { order_hash } = data.data
			document.cookie = `order_hash=${order_hash}`
			navigate({ to: '/order' })
		},
		onError: (error: AxiosError<{ message: string; code: number }>) => {
			if (error.response) {
				setErrorCode(error.response.data)
			}
			if (error.response?.data.code === 7) {
				setError('walletAddress', {
					type: 'custom',
					message: 'Неправильный формат кошелька',
				})
			}
		},
	})

	const agreement = watch(['agreement', 'personalData'])

	const setChain = usePlaceOrder(state => state.setChain)
	const chain = usePlaceOrder(state => state.chain)
	const amount = usePlaceOrder(state => state.amount)
	const itemId = usePlaceOrder(state => state.bestP2P)
	const bestPrice = usePlaceOrder(state => state.bestP2PPrice)

	const buttonDisabled = !(
		!!chain &&
		!!amount &&
		!!itemId &&
		!!bestPrice &&
		agreement[0] &&
		agreement[1]
	)

	const navigate = useNavigate()
	const onSubmitHandler = (data: z.infer<typeof FormSchema>) => {
		const newOrder: Order = {
			name: data.fullName,
			card_number: deleteSpaces(data.cardNumber),
			email: data.email,
			address: data.walletAddress,
			amount: amount,
			payment_method: fromCurrency,
			token: toCurrency,
			chain: data.chain,
			item_id: itemId,
			price: bestPrice,
		}

		createOrder(newOrder)
	}
	const [chainDefaultValue, setChainDefaultValue] = useState('')
	useEffect(() => {
		setChainDefaultValue(chains[0]?.name)
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [toCurrency])

	return (
		<form className={styles.form} onSubmit={handleSubmit(onSubmitHandler)}>
			<ErrorCodeModal errorCode={error.code} errorText={error.message} />
			<h3 className={styles.title}>Ваши реквизиты</h3>
			<div className={styles.inputs}>
				<Input
					register={register('fullName')}
					label="ФИО Отправителя"
					importantMessage="Важно, если вы отправляете с карты"
					errorText={errors.fullName?.message}
					clearError={() => {
						clearErrors('fullName')
					}}
				/>
				<Controller
					control={control}
					name="cardNumber"
					render={({ field: { onChange, ...field } }) => (
						<Input
							label="Номер карты отправителя"
							{...field}
							onChange={e => {
								const newValue = validateCardInput(e.target.value)
								if (
									newValue.errorStatus === 'ONE_LETTER' ||
									newValue.errorStatus === 'LETTER'
								) {
									if (newValue.errorStatus === 'ONE_LETTER') {
										setValue('cardNumber', '')
									}
									setError('cardNumber', {
										type: 'custom',
										message: 'Можно вводить только цифры!',
									})
									return
								}
								if (newValue.errorStatus === 'LENGTH') return

								onChange(newValue.value)
							}}
							errorText={errors.cardNumber?.message}
							clearError={() => clearErrors('cardNumber')}
						/>
					)}
				/>

				<Controller
					control={control}
					name="chain"
					defaultValue={chainDefaultValue}
					rules={{ required: 'Поле должно быть заполнено' }}
					render={({ field: { onChange, value } }) => (
						<Select
							defaultValue={chainDefaultValue}
							onChange={(value: string) => {
								onChange(value)
								setChain(value)
							}}
							value={value}
							options={chains.map(chain => ({
								name: chain.name,
								value: chain.name,
							}))}
							label="Chain"
							disabled={chains.length === 0}
						/>
					)}
				/>
				<Input
					register={register('walletAddress')}
					label="Адрес кошелька получателя"
					errorText={errors.walletAddress?.message}
					clearError={() => clearErrors('walletAddress')}
				/>
				<Input
					register={register('email')}
					name="email"
					label="Адрес почты"
					errorText={errors.email?.message}
					clearError={() => clearErrors('email')}
				/>
			</div>
			<div className={styles.checkboxes}>
				<Controller
					control={control}
					name="personalData"
					defaultValue={false}
					render={({ field: { onChange, value } }) => (
						<Checkbox
							setChecked={onChange}
							label="	Даю согласие на обработку персональных данных"
							checked={value}
						/>
					)}
				/>
				<Controller
					control={control}
					name="agreement"
					render={({ field: { onChange, value } }) => (
						<Checkbox
							setChecked={onChange}
							label="Соглашаюсь с офертой"
							checked={value}
						/>
					)}
				/>
			</div>
			<Button disabled={buttonDisabled || isOrderCreating}>
				{isOrderCreating ? 'Создаем обмен...' : 'Перейти к оплате'}
			</Button>
		</form>
	)
}
