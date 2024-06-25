import styles from './index.module.scss'

interface Props {
	currencyName: string
	imageUrl: string
	width: number
	dev?: boolean
}
export const CurrencyIcon = ({
	currencyName,
	imageUrl,
	width,
	dev = false,
}: Props) => {
	const widthStyle = width ? { width, height: width } : {}
	return (
		<img
			style={widthStyle}
			className={styles.currencyIcon}
			src={dev ? imageUrl : `https://api.fleshlight.fun/${imageUrl}`}
			alt={currencyName}
		/>
	)
}
