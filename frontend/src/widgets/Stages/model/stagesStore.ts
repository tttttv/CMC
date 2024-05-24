import { create } from 'zustand'

interface StagesState {
	time: number
	stage: string
	crypto: string
	newAmount: number
	setCrypto: (crypto: string) => void
	setStage: (stage: string) => void
	setTime: (time: number) => void
	setNewAmount: (amount: number) => void
}
export const useStagesStore = create<StagesState>(set => {
	return {
		time: 0,
		stage: '',
		crypto: '',
		newAmount: 0,
		setCrypto: (crypto: string) => set({ crypto }),
		setStage: (stage: string) => set({ stage }),
		setTime: (time: number) => set({ time }),
		setNewAmount: (amount: number) => set({ newAmount: amount }),
	}
})
