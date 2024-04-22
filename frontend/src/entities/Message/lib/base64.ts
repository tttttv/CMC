export const formatBase64Url = (base64: string) => {
	return base64.replace("base64,b'", 'base64,').slice(0, -1)
	// delete b' at the start and ' at the end of base64
}
