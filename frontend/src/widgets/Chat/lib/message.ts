import { Message } from '$/shared/types/api/enitites'

export const getDateFromMessage: (
	message: Message | string,
) => number = message => {
	if (typeof message === 'string') {
		if (!message) return 0
		const [date, time] = message.split(' ')
		const [day, month, year] = date.split('.')
		const [hours, minutes, seconds] = time.split(':')
		return new Date(
			+year,
			+month - 1,
			+day,
			+hours,
			+minutes,
			+seconds,
		).getTime()
	}

	if (message.dt === null) return 0
	const [date, time] = message.dt.split(' ')
	const [day, month, year] = date.split('.')
	const [hours, minutes, seconds] = time.split(':')
	return new Date(+year, +month - 1, +day, +hours, +minutes, +seconds).getTime()
}
