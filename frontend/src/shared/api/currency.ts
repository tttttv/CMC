import axios from "axios";

import type { PriceExchange, Values } from "../types/api/enitites";
import { PriceParams } from "../types/api/params";

class CurrencyAPI {
  private apiUrl: string;
  constructor(apiUrl: string) {
    this.apiUrl = apiUrl;
  }
  getFromValues = async () => {
    return await axios.get<Values>(`${this.apiUrl}/exchange/from`);
  };
  getToValues = async () => {
    return await axios.get<Values>(`${this.apiUrl}/exchange/to`);
  };

  getPrice = async (params: PriceParams) => {
    return await axios.get<PriceExchange>(`${this.apiUrl}/exchange/price`, {
      params,
    });
  };
}

const currencyAPI = new CurrencyAPI("https://api.fleshlight.fun/api");
export { currencyAPI };
