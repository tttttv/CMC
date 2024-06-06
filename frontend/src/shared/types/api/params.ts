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
  email: string;
  payment_method: number;
  payment_chain: string;
  payment_address: string;
  payment_amount: number;
  withdraw_method: number;
  withdraw_chain: string;
  withdraw_address: string;
  withdraw_amount: number;
  item_sell: string;
  price_sell: number;
  item_buy: string;
  price_buy: number;
}
