export interface PriceParams {
  anchor: "token" | "currency";
  amount?: number;
  quantity?: number;
  payment_method: string | number;
  token: string;
  chain: string;
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
