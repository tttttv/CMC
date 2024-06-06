import { create } from "zustand";

interface OrderData {
  item_sell: string;
  item_buy: string;
  price_sell: number;
  price_buy: number;
  payment_amount: number;
  withdraw_amount: number;
  anchor: "BUY" | "SELL";
}
interface PlaceOrderState {
  fromChain: string;
  toChain: string;
  setFromChain: (chain: string) => void;
  setToChain: (chain: string) => void;
  price: string;
  setPrice: (price: string) => void;
  orderData: OrderData | null;
  setOrderData: (data: OrderData | null) => void;
}
const usePlaceOrder = create<PlaceOrderState>((set) => ({
  fromChain: "",
  toChain: "",
  price: "",
  orderData: null,
  setOrderData: (data) => set({ orderData: data }),
  setFromChain: (chain) => set({ fromChain: chain }),
  setToChain: (chain) => set({ toChain: chain }),
  setPrice: (price) => set({ price }),
}));

export default usePlaceOrder;
