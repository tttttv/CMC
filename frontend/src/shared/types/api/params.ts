export type PriceAnchor = "SELL" | "BUY";

export interface PriceParams {
  payment_method: number;
  payment_chain?: string;
  withdraw_method: number;
  withdraw_chain?: string;
  payment_amount?: number;
  withdraw_amount?: number;
  amount: number;
  anchor: PriceAnchor;
}

export interface Order {
  name: string;
  card_number: string;
  payment_method: string;
  amount: number;
  price: number;
  token: string;
  chain: string;
  address: string;
  email: string;
  item_id: string;
}
