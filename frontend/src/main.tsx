import {
	RouterProvider,
	createHashHistory,
	createRouter,
} from '@tanstack/react-router'
import 'overlayscrollbars/overlayscrollbars.css'
import ReactDOM from 'react-dom/client'

import './index.css'
import { routeTree } from './routeTree.gen'

const hashHistory = createHashHistory()
const router = createRouter({
	routeTree,
	history: hashHistory,
})

declare module '@tanstack/react-router' {
	interface Register {
		router: typeof router
	}
}

ReactDOM.createRoot(document.getElementById('root')!).render(
	<RouterProvider router={router} />,
)
