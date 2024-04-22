import { InputHTMLAttributes } from 'react'
import { UseFormRegisterReturn } from 'react-hook-form'

import { CurrencyIcon } from '../../other/CurrencyIcon'

import importantIcon from './important.svg'
import styles from './index.module.scss'

interface Props extends InputHTMLAttributes<HTMLInputElement> {
	label: string
	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	register?: UseFormRegisterReturn<any>

	importantMessage?: string
	iconUrl?: string
	iconAlt?: string
	disabledStyle?: boolean
	errorText?: string
	clearError?: () => void
	// eslint-disable-next-line @typescript-eslint/no-explicit-any
}

const Input = ({
	clearError,
	onChange,
	label,
	register,
	importantMessage = '',
	iconAlt = '',
	iconUrl = '',
	errorText = '',
	disabledStyle = false,
	...props
}: Props) => {
	return (
		<div className={styles.inputWrapper}>
			{label && (
				<label className={styles.label} htmlFor={label}>
					{label}
				</label>
			)}
			<div className={styles.inputContainer}>
				{iconUrl && iconAlt && (
					<div className={styles.icon}>
						<CurrencyIcon
							currencyName={iconAlt}
							imageUrl={iconUrl}
							width={32}
						/>
					</div>
				)}
				<input
					className={styles.input}
					id={label}
					data-disabled={disabledStyle}
					{...register}
					{...props}
					onChange={e => {
						clearError?.()
						onChange?.(e)
					}}
				/>
				{errorText && clearError && (
					<span className={styles.error}>{errorText}</span>
				)}
			</div>
			{importantMessage && (
				<label htmlFor={label} className={styles.importantMessage}>
					<img src={importantIcon} alt="!" />
					<span>{importantMessage}</span>
				</label>
			)}
		</div>
	)
}

export default Input
