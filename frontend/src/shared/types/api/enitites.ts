interface IdTemplate {
	id: string
	name: string
}

export interface PaymentMethod {
	id: string
	bank_name: string
	logo: string
}
export interface Currency extends IdTemplate {
	payment_methods: PaymentMethod[]
}

export interface Chain extends IdTemplate {
	withdraw_commission: number
}

export interface Token extends IdTemplate {
	chains: Chain[]
	withdraw_commission: number
	payment_methods: PaymentMethod[]
	crypto: boolean
	logo: string
}

export interface PriceExchange {
	price: number
	amount: number
	quantity: number
	better_amount: number
	best_p2p: string
	best_p2p_price: number
}

// Order
export interface OrderHash {
	order_hash: string
}
export interface OrderState {
	order: {
		amount: number
		quantity: number
		time_left: number // last screen
		from: {
			bank_name: string
			currency: string
			id: number
			logo: string
		}
		to: {
			id: string
			name: string
			chains: Chain[]
			payment_methods: number[]
		}
		rate: number
		order_hash: string
	}
	state:
		| 'INITIALIZATION'
		| 'PENDING'
		| 'RECEIVING'
		| 'BUYING'
		| 'TRADING'
		| 'WITHDRAWING'
		| 'SUCCESS'
		| 'ERROR'
		| 'TIMEOUT'
		| 'WRONG' // COURSE HAS CHANGED
		| 'CREATED'
		| 'INITIATED'
	state_data: {
		terms?: {
			real_name: string
			account_no: string
			payment_id: string
			payment_type: number
		}
		time_left?: number
		commentary?: string
		address?: string
		withdraw_quantity: number
	}
}

export interface Message {
	uuid: string
	text: string
	dt: string
	nick_name: string
	image: string
	side: 'USER' | 'TRADER' | 'SUPPORT'
}
export interface Messages {
	title: string
	avatar: string
	messages: Message[]
}
