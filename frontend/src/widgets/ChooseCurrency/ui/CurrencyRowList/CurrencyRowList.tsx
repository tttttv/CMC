import { BankList } from './lists/BankList'

interface Props {
	property: string
}

export const CurrencyRowList = ({ property }: Props) =>
	property === 'getting' ? <></> : <BankList />
