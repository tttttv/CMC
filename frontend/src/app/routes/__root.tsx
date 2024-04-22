import { Outlet, createRootRoute } from '@tanstack/react-router'

import Wrapper from '$/widgets/Wrapper'

export const Route = createRootRoute({
	component: () => {
		return (
			<Wrapper>
				<Outlet />
			</Wrapper>
		)
	},
})
