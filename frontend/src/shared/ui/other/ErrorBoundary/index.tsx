import { Component, ReactNode } from 'react'

interface ErrorBoundaryProps {
	children: ReactNode
}

interface ErrorBoundaryState {
	error?: Error
}

export default class ErrorBoundary extends Component<
	ErrorBoundaryProps,
	ErrorBoundaryState
> {
	constructor(props: ErrorBoundaryProps) {
		super(props)
		this.state = {}
	}

	componentDidCatch(error: Error) {
		this.setState({ error })
	}

	render() {
		if (this.state.error) {
			return (
				<div>
					<h1>Something went wrong.</h1>
					<p>{this.state.error.message}</p>
				</div>
			)
		}

		return this.props.children
	}
}
