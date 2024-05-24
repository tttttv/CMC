import { useEffect, useState } from 'react'

import { useStagesStore } from '../../model/stagesStore'

import styles from './Timer.module.scss'

const UPDATE_TIMER_TIME = 1000
export const Timer = () => {
	const timeFromStorage = useStagesStore(state => state.time)
	const [time, setTime] = useState<number>(0)
	useEffect(() => {
		setTime(timeFromStorage)

		const interval = setInterval(() => {
			setTime(prev => {
				if (prev === 0) return 0
				return prev - 1
			})
		}, UPDATE_TIMER_TIME)

		return () => clearInterval(interval)
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [timeFromStorage])

	const formattedTime = `${`${Math.floor(time / 60)}`.padStart(2, '0')}:${`${time % 60}`.padStart(2, '0')}`

	return (
		<span className={styles.waitTime}>
			Ожидайте проведения платежа. Максимальное время ожидания:{' '}
			<div className={styles.time}>{formattedTime}</div>
		</span>
	)
}
