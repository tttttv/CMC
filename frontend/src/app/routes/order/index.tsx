import { createFileRoute, redirect } from '@tanstack/react-router'

import { OrderPage } from '$/pages/OrderPage'
import getCookieValue from '$/shared/helpers/getCookie'

export const Route = createFileRoute('/order/')({
	component: OrderPage,
	loader: async () => {
		const hash = getCookieValue('order_hash')
		if (!hash) {
			throw redirect({
				to: '/',
			})
		}
	},
})
