import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import styles from './index.module.scss'

// eslint-disable-next-line react-refresh/only-export-components
export const queryClient = new QueryClient({
	defaultOptions: {
		queries: {
			retry: false,
		},
	},
})
const Wrapper = ({ children }: { children: React.ReactNode }) => {
	return (
		<QueryClientProvider client={queryClient}>
			<div className={styles.wrapper}>{children}</div>
		</QueryClientProvider>
	)
}

export default Wrapper
