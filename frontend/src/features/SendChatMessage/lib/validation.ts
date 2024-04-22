export const validateInputFile = (file: File | undefined) => {
	return file && file.name && file.name.match(/\.(jpg|jpeg|png|gif)$/i)
}
