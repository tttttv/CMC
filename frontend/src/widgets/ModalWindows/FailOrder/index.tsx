import Button from '$/shared/ui/kit/Button/Button'
import icon from './icon.svg'
import styles from './index.module.scss'

const FailOrder = () => {
	return (
		<div className={styles.container}>
			<div className={styles.content}>
				<div className={styles.titleContainer}>
					<img src={icon} alt="" />
					<h2 className={styles.title}>Ошибка!</h2>
				</div>
				<div className={styles.info}>
					<div className={styles.infoTitle}>Что-то пошло не так</div>
					<div className={styles.infoDescription}>
						При совершении вашей транзакции возникла ошибка.Мы просим вас
						связаться с нами в телеграм-боте поддержки{' '}
						<a href="" target="_blank">
							@bot
						</a>
						, или мы самостоятельно напишем вам на почту{' '}
						<a href="mailto:">почта.</a>
					</div>
					<Button
						linkBehavior={{
							enabled: true,
							to: '',
							target: '_blank',
						}}
					>
						Переход в бот поддержки
					</Button>
				</div>
			</div>
		</div>
	)
}

export default FailOrder
