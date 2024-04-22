import { useQuery } from '@tanstack/react-query'

import SendChatMessage from '$/features/SendChatMessage'
import { orderAPI } from '$/shared/api/order'
import { CurrencyIcon } from '$/shared/ui/other/CurrencyIcon'
import styles from './Chat.module.scss'
import { Messages } from './Messages/Messages'

export const Chat = () => {
	const { data } = useQuery({
		queryKey: ['messages'],
		queryFn: orderAPI.getOrderMessages,
		retry: 0,
		select: data => data.data,
	})

	return (
		<section className={styles.container}>
			<div className={styles.header}>
				<div className={styles.avatar}>
					<CurrencyIcon
						currencyName={data?.title || ''}
						imageUrl={data?.avatar || ''}
						width={40}
					/>
				</div>
				<h2 className={styles.headerTitle}>{data?.title}</h2>
			</div>
			<div className={styles.body}>
				<Messages />
				<SendChatMessage />
			</div>
		</section>
	)
}
