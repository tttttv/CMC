import axios from "axios";

import type { PriceExchange, Values } from "../types/api/enitites";
import { PriceParams } from "../types/api/params";

class CurrencyAPI {
  private apiUrl: string;
  constructor(apiUrl: string) {
    this.apiUrl = apiUrl;
  }
  getFromValues = async () => {
    return await axios.get<Values>(`${this.apiUrl}/exchange/payments`);
  };
  getToValues = async () => {
    return await axios.get<Values>(`${this.apiUrl}/exchange/withdraws`);
  };

  getPrice = async (params: PriceParams) => {
    return await axios.post<PriceExchange>(`${this.apiUrl}/exchange/price/`, {
      params,
    });
  };
}

const currencyAPI = new CurrencyAPI("https://api.fleshlight.fun/api");
export { currencyAPI };
