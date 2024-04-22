import axios from 'axios'

import type { Currency, PriceExchange, Token } from '../types/api/enitites'
import { PriceParams } from '../types/api/params'

class CurrencyAPI {
	private apiUrl: string
	constructor(apiUrl: string) {
		this.apiUrl = apiUrl
	}
	getBanks = async () => {
		return await axios.get<{ methods: Currency[] }>(
			`${this.apiUrl}/exchange/from`,
		)
	}
	getCryptoTokens = async () => {
		return await axios.get<{ methods: Token[] }>(`${this.apiUrl}/exchange/to`)
	}

	getPrice = async (params: PriceParams) => {
		return await axios.get<PriceExchange>(`${this.apiUrl}/exchange/price`, {
			params,
		})
	}
}

const currencyAPI = new CurrencyAPI(import.meta.env.VITE_API_URL)
export { currencyAPI }
