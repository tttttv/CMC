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
  price: number;
  amount: number;
  quantity: number;
  better_amount: number;
  best_p2p: string;
  best_p2p_price: number;
}
// Order
export interface OrderHash {
  order_hash: string;
}
export interface OrderState {
  order: {
    amount: number;
    quantity: number;
    time_left: number; // last screen
    from: {
      bank_name: string;
      currency: string;
      id: number;
      logo: string;
    };
    to: {
      id: string;
      name: string;
      chains: Chain[];
      payment_methods: number[];
    };
    rate: number;
    order_hash: string;
  };
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
    | "WRONG" // COURSE HAS CHANGED
    | "CREATED"
    | "INITIATED";
  state_data: {
    terms?: {
      real_name: string;
      account_no: string;
      payment_id: string;
      payment_type: number;
    };
    time_left?: number;
    commentary?: string;
    address?: string;
    withdraw_quantity: number;
  };
}

export interface Message {
  uuid: string;
  text: string;
  dt: string;
  nick_name: string;
  image: string;
  side: "USER" | "TRADER" | "SUPPORT";
}
export interface Messages {
  title: string;
  avatar: string;
  messages: Message[];
}

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
  token: string | null;
  chain: string | null;
  address: string | null;
  full_name: string | null;
  email: string | null;
  color_palette: ColorScheme;
  payment_method: string[] | null;
}
