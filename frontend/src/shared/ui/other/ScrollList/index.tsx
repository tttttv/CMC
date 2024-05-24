import { OverlayScrollbarsComponent } from 'overlayscrollbars-react'

import '$/app/styles/scrollbar.scss'

interface Props {
	children: React.ReactNode
	listClassName?: string
}
const ScrollableList = ({ children, listClassName }: Props) => {
	return (
		<OverlayScrollbarsComponent
			element={'div'}
			defer
			className={listClassName}
			options={{
				scrollbars: {
					autoHideDelay: 300,
				},
			}}
		>
			{children}
		</OverlayScrollbarsComponent>
	)
}

export default ScrollableList
