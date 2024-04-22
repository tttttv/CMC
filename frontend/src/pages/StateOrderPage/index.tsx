import { useState } from 'react'

import clsx from '$/shared/helpers/clsx'
import useMediaQuery from '$/shared/hooks/useMediaQuery'
import Page from '$/shared/ui/global/Page'
import Button from '$/shared/ui/kit/Button/Button'
import Chat from '$/widgets/Chat'
import ExchangeDetails from '$/widgets/ExchangeDetails'
import OrderStages from '$/widgets/Stages'
import styles from './index.module.scss'

export const StateOrderPage = () => {
	const { matching: isChatHide } = useMediaQuery('(max-width: 1024px)')
	const [isChatOpened, setIsChatOpened] = useState(false)
	const containerName = clsx(
		styles.stagesContainer,
		{
			[styles.chatOpened]: isChatOpened,
		},
		[],
	)
	return (
		<Page>
			<div className={containerName}>
				{!isChatOpened ? (
					<>
						<div className={styles.left}>
							<ExchangeDetails />
							<OrderStages />
						</div>
						{!isChatHide ? (
							<Chat />
						) : (
							<>
								<div className={styles.chatButtonContainer}>
									<Button
										onClick={() => setIsChatOpened(true)}
										className={styles.chatButton}
										data-amount="1"
									>
										Открыть чат
									</Button>
								</div>
							</>
						)}
					</>
				) : (
					<div className={styles.chatContainer}>
						<Chat />
						<div className={styles.chatButtonContainer}>
							<Button onClick={() => setIsChatOpened(false)}>
								Вернуться к обмену
							</Button>
						</div>
					</div>
				)}
			</div>
		</Page>
	)
}
