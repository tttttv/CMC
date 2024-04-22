export const validateCurrencyInput = (value: string) => {
	let isZero = false
	if (+value === 0 || value === '') {
		isZero = true
	}
	let preparedValue = value.trim().replace(',', '.').replace(/^0+/, '')
	if (preparedValue.startsWith('.')) {
		preparedValue = `0${preparedValue}`
	}

	const strArray = Array.from(preparedValue)
	if (strArray.filter(c => c === '.').length > 1) return undefined
	if (!/^\d*\.?\d*$/.test(preparedValue)) return undefined

	if (isZero) preparedValue = '0'

	return preparedValue
}

export const validateCardInput: (value: string) => {
	value: string
	errorStatus: 'LENGTH' | 'LETTER' | 'ONE_LETTER' | undefined
} = value => {
	if (value.length > 19) {
		return { value: '', errorStatus: 'LENGTH' }
	}
	if (!Array.from(value.trim()).every(char => /^[0-9\s]*$/.test(char))) {
		if (value.length === 1) {
			// фикс бага, когда вводится одна буква

			return { value: '', errorStatus: 'ONE_LETTER' }
		}

		return { value: '', errorStatus: 'LETTER' }
	}

	const newValue = value
		.replace(' ', '')
		.split(/(\d{4})/)
		.filter((w: string) => w.length > 0)
		.map((w: string) => {
			return w.trim()
		})
		.join(' ')
		.split(' ')
		.filter((w: string) => w !== '')
		.join(' ')
	return {
		value: newValue,
		errorStatus: undefined,
	}
}
