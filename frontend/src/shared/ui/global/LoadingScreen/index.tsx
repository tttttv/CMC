import clsx from '$/shared/helpers/clsx'
import styles from './index.module.scss'

interface Props {
	children?: React.ReactNode
	inContainer?: boolean
}
const LoadingScreen = ({ children, inContainer = false }: Props) => {
	const className = clsx(
		styles.loaderContainer,
		{ [styles.inContainer]: inContainer },
		[],
	)
	return (
		<div className={className}>
			<div className={styles.loader}></div>
			<span>{children}</span>
		</div>
	)
}

export default LoadingScreen
