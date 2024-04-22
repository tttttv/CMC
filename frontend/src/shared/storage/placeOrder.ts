import { create } from 'zustand'

interface PlaceOrderState {
	chain: string
	amount: number
	price: number
	bestP2P: string
	bestP2PPrice: number
	setChain: (chain: string) => void
	setAmount: (amount: number) => void
	setPrice: (price: number) => void
	setBestP2P: (bestP2P: string) => void
	setBestP2PPrice: (bestP2PPrice: number) => void
}
const usePlaceOrder = create<PlaceOrderState>(set => ({
	chain: '',
	amount: 1,
	price: 0,
	bestP2P: '',
	bestP2PPrice: 0,
	setChain: (chain: string) => set({ chain }),
	setAmount: (amount: number) => set({ amount }),
	setPrice: (price: number) => set({ price }),
	setBestP2P: (bestP2P: string) => set({ bestP2P }),
	setBestP2PPrice: (bestP2PPrice: number) => set({ bestP2PPrice }),
}))

export default usePlaceOrder
