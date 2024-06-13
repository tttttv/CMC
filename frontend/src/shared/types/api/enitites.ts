// ---------------------------------- METHODS ----------------------------------
export interface Crypto {
  id: string;
  name: string;
  chains: Chain[];
  logo: string;
  exchange_from: number[];
}

export interface Fiat {
  id: string;
  name: string;
  payment_methods: PaymentMethod[];
}

export interface PaymentMethod {
  id: string;
  name: string;
  logo: string;
  exchange_to: number[];
}

export interface Chain {
  id: string;
  name: string;
  withdraw_commission: number;
}
export interface Methods {
  fiat: Fiat[];
  crypto: Crypto[];
}

export interface Values {
  methods: Methods;
}

export interface PriceExchange {
  price: string;
  payment_amount: number;
  withdraw_amount: number;
  better_amount: number;
  item_sell: string;
  item_buy: string;
  price_sell: number;
  price_buy: number;
}
// --------------------------------ORDER------------------------------
export interface OrderHash {
  order_hash: string;
}

interface Payment {
  id: number;
  currency_id: number;
  type: string;
  name: string;
  chain: string;
  address: string;
  logo: string;
}
interface Withdraw {
  id: number;
  currency_id: number;
  type: "fiat" | "crypto";
  name: string;
  chain: string;
  address: string;
  logo: string;
}
interface Order {
  payment: Payment;
  withdraw: Withdraw;
  rate: number;
  payment_amount: number;
  withdraw_amount: number;
  order_hash: string;
  stage: number;
  time_left: number;
  terms: Terms;
  commentary: string;
}
interface StateData {
  terms: Terms;
  time_left: number;
  withdraw_amount: number;
  payment_amount: number;
  commentary: string;
  address?: string;
}

interface Terms {
  id?: number;
  address?: string;
  chain?: string;
  chain_name?: string;
  qrcode?: string;
  real_name?: string;
  account_no?: string;
}

export interface OrderState {
  order: Order;
  state_data: StateData;
  state:
    | "INITIALIZATION"
    | "PENDING"
    | "RECEIVING"
    | "BUYING"
    | "TRADING"
    | "WITHDRAWING"
    | "SUCCESS"
    | "ERROR"
    | "TIMEOUT"
    | "WRONG"
    | "CREATED"
    | "INITIATED";
}

// -----------------------------ЧАТ------------------------------------
export interface Message {
  uuid: string;
  text: string;
  dt: string;
  nick_name: string;
  file: string;
  file_name: string;
  side: "USER" | "TRADER" | "SUPPORT";
}
export interface Messages {
  title: string;
  avatar: string;
  messages: Message[];
}

// -----------------------------Виджет-----------------------------
export interface ColorScheme {
  accentColor: string | null;
  secondaryAccentColor: string | null;
  textColor: string | null;
  secondaryTextColor: string | null;
  bodyColor: string | null;
  blockColor: string | null;
  contrastColor: string | null;
  buttonHoverColor: string | null;
  buttonDisabledColor: string | null;
  uiKitBackgroundColor: string | null;
  uiKitBorderColor: string | null;
}

export interface WidgetEnv {
  partner_code: string;
  withdrawing_token: string;
  withdrawing_chain: string;
  withdrawing_address: string;
  partner_commission: number;
  email: string;
  name: string;
  color_palette: ColorScheme;
  redirect_url: string;
}
