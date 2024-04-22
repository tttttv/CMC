import { create } from 'zustand'

interface CurrencyState {
	fromCurrencyType: string
	fromCurrency: string
	toCurrencyType: string
	toCurrency: string

	setFromCurrency: (currency: string) => void
	setToCurrency: (currency: string) => void
	setToCurrencyType: (type: string) => void
	setFromCurrencyType: (type: string) => void
}
const useCurrencyStore = create<CurrencyState>(set => ({
	fromCurrencyType: 'all',
	fromCurrency: '',
	toCurrencyType: '',
	toCurrency: '',
	setFromCurrency: (currency: string) => set({ fromCurrency: currency }),
	setToCurrency: (currency: string) => set({ toCurrency: currency }),
	setFromCurrencyType: (type: string) => set({ fromCurrencyType: type }),
	setToCurrencyType: (type: string) => set({ toCurrencyType: type }),
}))

export default useCurrencyStore
