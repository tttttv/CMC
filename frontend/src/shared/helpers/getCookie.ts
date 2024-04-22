const getCookieValue = (name: string) => {
	const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'))
	if (match) {
		return decodeURIComponent(match[2])
	} else {
		return null
	}
}

export default getCookieValue
