import { BankList } from './lists/BankList'
import { CryptoList } from './lists/CryptoList'

interface Props {
	property: string
}
export const CurrencyColumnList = ({ property }: Props) =>
	property === 'getting' ? <CryptoList /> : <BankList />
