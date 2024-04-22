import { getDateFromMessage } from '$/widgets/Chat/lib/message'

export const generateImageName = (url: string) => {
	return `${(Math.random() + 1).toString(36).substring(7)}.${url.match(/data:image\/(\w+);base64,.*$/)?.[1] || '.png'}`
}

export const generateDateForOpenedImage = (datetime: string) => {
	return new Date(getDateFromMessage(datetime))
		.toLocaleDateString('ru-RU', {
			day: 'numeric',
			month: 'long',
			hour: 'numeric',
			minute: 'numeric',
		})
		.replace(' в ', ', ')
}
