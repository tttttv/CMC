import axios from "axios";

import getCookieValue from "../helpers/getCookie";
import { Messages, OrderHash, OrderState } from "../types/api/enitites";
import { Order } from "../types/api/params";

class OrderAPI {
  private apiUrl: string;
  constructor(apiUrl: string) {
    this.apiUrl = apiUrl;
  }

  private getHash = () => {
    return getCookieValue("order_hash") || "";
  };
  private createConfig = (url: string, data: FormData, method?: string) => {
    return {
      method: method || "post",
      maxBodyLength: Infinity,
      url,
      data,
    };
  };

  createOrder = async (order: Order) => {
    const data = new FormData();
    for (const [key, value] of Object.entries(order)) {
      data.append(key, value);
    }
    const config = this.createConfig(`${this.apiUrl}/order/`, data);
    return await axios.request<OrderHash>(config);
  };

  getOrderState = async () => {
    return await axios.get<OrderState>(`${this.apiUrl}/order/state/`, {
      params: {
        order_hash: this.getHash(),
      },
    });
  };

  cancelOrder = async () => {
    const data = new FormData();
    data.append("order_hash", this.getHash());

    const config = this.createConfig(`${this.apiUrl}/order/cancel/`, data);

    return await axios.request<{ code: number; message: string }>(config);
  };

  getOrderMessages = async () => {
    return await axios.get<Messages>(`${this.apiUrl}/order/messages/`, {
      params: {
        order_hash: this.getHash(),
      },
    });
  };

  sendOrderMessage = async (text: string) => {
    const data = new FormData();
    data.append("order_hash", this.getHash());
    data.append("text", text);

    const config = this.createConfig(
      `${this.apiUrl}/order/send_message/`,
      data
    );
    return await axios.request(config);
  };

  sendImageMessage = async (base64Img: string) => {
    const data = new FormData();
    data.append("order_hash", this.getHash());

    data.append("file", base64Img);

    const config = this.createConfig(`${this.apiUrl}/order/send_file/`, data);

    return await axios.request(config);
  };

  continueOrder = async () => {
    const data = new FormData();
    data.append("order_hash", this.getHash());

    const config = this.createConfig(
      `${this.apiUrl}/order/continue_with_new_price/`,
      data
    );

    return await axios.request(config);
  };

  getAPILink = () => {
    return `${this.apiUrl}/order`;
  };

  confirmWithdraw = async () => {
    const data = new FormData();
    data.append("order_hash", this.getHash());

    const config = this.createConfig(
      `${this.apiUrl}/order/confirm_withdraw/`,
      data
    );

    return await axios.request(config);
  };

  confirmPayment = async () => {
    const data = new FormData();
    data.append("order_hash", this.getHash());

    const config = this.createConfig(
      `${this.apiUrl}/order/confirm_payment/`,
      data
    );

    return await axios.request(config);
    {
    }
  };

  openDispute = async () => {
    const data = new FormData();
    data.append("order_hash", this.getHash());

    const config = this.createConfig(
      `${this.apiUrl}/order/open_dispute/`,
      data
    );

    return await axios.request(config);
  };
}

const orderAPI = new OrderAPI("https://api.fleshlight.fun/api");
export { orderAPI };
