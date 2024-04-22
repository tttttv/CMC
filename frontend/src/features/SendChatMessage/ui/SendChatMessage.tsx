import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useRef, useState } from 'react'

import { validateInputFile } from '../lib/validation'

import { orderAPI } from '$/shared/api/order'
import { ErrorModal } from '$/shared/ui/modals/ErrorModal'
import styles from './SendChatMessage.module.scss'

const GREEN = 'var(--green-color)'
const LIGHTGRAY = 'var(--lightgray-color)'
const LIME = 'var(--lime-color)'
const GRAY = 'var(--gray-color)'

export const SendChatMessage = () => {
	const queryClient = useQueryClient()
	const focused = useRef(false)
	const inputRef = useRef<HTMLInputElement>(null)
	const imageInputRef = useRef<HTMLInputElement>(null)
	const [errorText, setErrorText] = useState('')
	const [inputValue, setInputValue] = useState('')
	const [isImageLoaded, setImageLoaded] = useState(false)

	const { mutate: sendMessageToServer } = useMutation({
		mutationKey: ['sendMessage'],
		mutationFn: (text: string) => orderAPI.sendOrderMessage(text),
		onSuccess: async () => {
			queryClient.invalidateQueries({
				queryKey: ['messages'],
			})
		},
		onError: () => {
			queryClient.invalidateQueries({
				queryKey: ['messages'],
			})
		},
	})

	const { mutate: sendImageToServer } = useMutation({
		mutationKey: ['sendImage'],
		mutationFn: orderAPI.sendImageMessage,
		onSuccess: async () => {
			await queryClient.invalidateQueries({
				queryKey: ['messages'],
			})
		},
	})

	const sendMessage = () => {
		sendMessageToServer(inputValue)
		setInputValue('')
		inputRef.current?.blur()
		setImageLoaded(false)
	}

	const sendDisabled = inputValue === '' && !isImageLoaded

	return (
		<div className={styles.container}>
			<div
				className={styles.inputContainer}
				onClick={() => inputRef.current?.focus()}
			>
				<input
					ref={inputRef}
					value={inputValue}
					placeholder="Введите сообщение..."
					onChange={e => setInputValue(e.target.value)}
					onFocus={() => (focused.current = true)}
					onBlur={() => (focused.current = false)}
					onKeyDown={e => e.key === 'Enter' && focused.current && sendMessage()}
					className={styles.input}
				/>
				<div className={styles.inputButtons}>
					<div className={styles.image}>
						<input
							className={styles.imageInput}
							type="file"
							accept="image/*"
							ref={imageInputRef}
							onChange={e => {
								const isRightFile = validateInputFile(e.target.files?.[0])
								if (isRightFile) {
									sendImageToServer(e.target.files![0])
									imageInputRef.current!.value = ''
								} else {
									setErrorText('Доступны расширения jpg, jpeg, png, gif')
								}
							}}
						/>
						<svg
							width="24"
							height="24"
							viewBox="0 0 24 24"
							fill="none"
							xmlns="http://www.w3.org/2000/svg"
						>
							<path
								d="M19.954 10.9857L15.9543 19.7504C15.8029 20.083 15.588 20.3821 15.3219 20.6308C15.0559 20.8795 14.7439 21.0729 14.4037 21.1999C14.0636 21.3269 13.702 21.385 13.3396 21.371C12.9772 21.3569 12.6211 21.271 12.2917 21.118L3.60622 17.0817C3.27687 16.9287 2.98062 16.7117 2.73438 16.4432C2.48814 16.1746 2.29673 15.8597 2.17108 15.5165C2.04543 15.1733 1.98801 14.8084 2.00208 14.4428C2.01615 14.0772 2.10145 13.718 2.25311 13.3856L6.25281 4.62089C6.40446 4.28854 6.61948 3.98958 6.88562 3.74109C7.15176 3.4926 7.46379 3.29944 7.8039 3.17265C8.14401 3.04585 8.50554 2.9879 8.86785 3.0021C9.23015 3.0163 9.58614 3.10238 9.91547 3.25542L18.6009 7.29165C19.2655 7.60071 19.7814 8.16339 20.0351 8.85605C20.2888 9.54871 20.2596 10.3147 19.954 10.9857Z"
								fill={isImageLoaded ? GREEN : GRAY}
							/>
							<path
								d="M16.3353 19.9795L6.94671 18.1434C6.22784 18.0028 5.59374 17.5798 5.18391 16.9675C4.77408 16.3552 4.62208 15.6036 4.76135 14.8782L6.57933 5.40466C6.64826 5.04544 6.78664 4.70345 6.98656 4.39821C7.18648 4.09297 7.44403 3.83046 7.74449 3.62567C8.04496 3.42089 8.38246 3.27783 8.73771 3.20468C9.09297 3.13153 9.45902 3.12972 9.81498 3.19934L19.2056 5.03549C19.5616 5.10503 19.9005 5.24464 20.2029 5.44636C20.5054 5.64808 20.7655 5.90796 20.9685 6.21114C21.1714 6.51433 21.3132 6.85489 21.3857 7.21338C21.4582 7.57186 21.46 7.94124 21.391 8.30043L19.5722 17.775C19.5031 18.1342 19.3646 18.4762 19.1646 18.7814C18.9645 19.0867 18.7068 19.3491 18.4062 19.5538C18.1056 19.7585 17.768 19.9015 17.4127 19.9745C17.0574 20.0476 16.6913 20.0493 16.3353 19.9795Z"
								fill={isImageLoaded ? LIME : LIGHTGRAY}
							/>
							<path
								d="M20.4441 8.67309L18.832 17.0716C18.7083 17.7144 18.3368 18.2813 17.799 18.6477C17.2612 19.0141 16.6013 19.15 15.9642 19.0254L7.64177 17.3986L7.58759 17.3873C7.55129 17.3795 7.51499 17.3706 7.47921 17.3612C6.87986 17.2005 6.36329 16.8162 6.03391 16.286C5.70454 15.7557 5.5869 15.1191 5.70479 14.5047L7.31691 6.1062C7.37802 5.78783 7.50067 5.48472 7.67786 5.21419C7.85505 4.94366 8.08331 4.71099 8.34961 4.52948C8.61591 4.34797 8.91502 4.22117 9.22988 4.15632C9.54474 4.09147 9.86918 4.08984 10.1847 4.15153L18.5071 5.77837C18.8227 5.84003 19.1231 5.96383 19.3913 6.14269C19.6594 6.32155 19.89 6.55197 20.0699 6.82078C20.2498 7.0896 20.3754 7.39154 20.4396 7.70937C20.5038 8.02719 20.5053 8.35467 20.4441 8.67309Z"
								fill={isImageLoaded ? LIME : LIGHTGRAY}
							/>
							<path
								d="M12.9653 18.4384L7.4748 17.3657L7.47921 17.3616C6.87986 17.2009 6.36329 16.8166 6.03391 16.2863C5.70454 15.7561 5.5869 15.1194 5.70479 14.505L6.10769 12.4067L7.35554 11.2325C7.53674 11.062 7.75531 10.9372 7.99343 10.8682C8.23155 10.7992 8.48246 10.788 8.72568 10.8356C8.9689 10.8831 9.19753 10.988 9.39292 11.1417C9.58831 11.2954 9.74491 11.4935 9.84995 11.7199L10.9511 14.0945L12.9653 18.4384Z"
								fill={isImageLoaded ? GREEN : GRAY}
							/>
							<path
								d="M12.2244 9.9035C12.842 9.63986 13.1309 8.92093 12.8696 8.29772C12.6084 7.67452 11.8959 7.38303 11.2784 7.64666C10.6608 7.9103 10.3719 8.62923 10.6332 9.25244C10.8944 9.87565 11.6069 10.1671 12.2244 9.9035Z"
								fill={isImageLoaded ? GREEN : GRAY}
							/>
							<path
								d="M10.9519 14.0951L9.53003 15.4329C9.38121 15.5728 9.16499 15.3643 9.29669 15.2079L10.6967 13.5478L10.9519 14.0951Z"
								fill={isImageLoaded ? LIME : LIGHTGRAY}
							/>
							<path
								d="M19.2351 14.9812L18.8337 17.0711C18.7727 17.3895 18.65 17.6926 18.4729 17.9632C18.2957 18.2338 18.0674 18.4665 17.8011 18.6481C17.5348 18.8296 17.2357 18.9565 16.9208 19.0214C16.606 19.0863 16.2815 19.0879 15.966 19.0263L7.64353 17.3995L7.58934 17.3882L7.47656 17.3662L7.48097 17.362L10.9526 14.0955L14.8545 10.4256C15.6344 9.69302 16.8968 9.93869 17.3487 10.913L19.2351 14.9812Z"
								fill={isImageLoaded ? GREEN : GRAY}
							/>
						</svg>
					</div>

					<div className={styles.divider}></div>
					<button
						className={styles.send}
						onClick={() => sendMessage()}
						disabled={sendDisabled}
					>
						<svg
							width="18"
							height="18"
							viewBox="0 0 18 18"
							xmlns="http://www.w3.org/2000/svg"
						>
							<path
								d="M17.7832 0.217449C17.682 0.116704 17.5541 0.046952 17.4146 0.0163941C17.2751 -0.0141638 17.1298 -0.00425713 16.9957 0.0449493L0.495733 6.04495C0.353434 6.09892 0.230923 6.19491 0.144471 6.32016C0.0580196 6.44542 0.0117188 6.59401 0.0117188 6.7462C0.0117188 6.89839 0.0580196 7.04698 0.144471 7.17223C0.230923 7.29749 0.353434 7.39348 0.495733 7.44745L6.93823 10.0199L11.6932 5.24995L12.7507 6.30745L7.97323 11.0849L10.5532 17.5275C10.6088 17.667 10.705 17.7866 10.8294 17.8709C10.9537 17.9551 11.1005 18.0001 11.2507 17.9999C11.4023 17.9968 11.5494 17.9479 11.6725 17.8595C11.7957 17.7711 11.8892 17.6475 11.9407 17.5049L17.9407 1.00495C17.9918 0.872257 18.0042 0.727772 17.9763 0.588342C17.9484 0.448912 17.8814 0.320282 17.7832 0.217449Z"
								fill="#5C5C5C"
							/>
						</svg>
					</button>
				</div>
			</div>
			{errorText && (
				<ErrorModal
					text={errorText}
					closeFunction={() => setErrorText('')}
					useMyFunction
				/>
			)}
		</div>
	)
}
