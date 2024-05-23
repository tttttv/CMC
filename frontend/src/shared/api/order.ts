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
    const config = this.createConfig(`${this.apiUrl}/order`, data);
    return await axios.request<OrderHash>(config);
  };

  getOrderState = async () => {
    return await axios.get<OrderState>(`${this.apiUrl}/order/state`, {
      params: {
        order_hash: this.getHash(),
      },
    });
  };

  cancelOrder = async () => {
    const data = new FormData();
    data.append("order_hash", this.getHash());

    const config = this.createConfig(`${this.apiUrl}/order/cancel`, data);

    return await axios.request<{ code: number; message: string }>(config);
  };

  payOrder = async () => {
    const data = new FormData();
    data.append("order_hash", this.getHash());

    const config = this.createConfig(`${this.apiUrl}/order/paid`, data);

    return await axios.request(config);
  };

  getOrderMessages = async () => {
    return await axios.get<Messages>(`${this.apiUrl}/order/message`, {
      params: {
        order_hash: this.getHash(),
      },
    });
  };

  sendOrderMessage = async (text: string) => {
    const data = new FormData();
    data.append("order_hash", this.getHash());
    data.append("text", text);

    const config = this.createConfig(`${this.apiUrl}/order/message/send`, data);
    return await axios.request(config);
  };

  sendImageMessage = async (base64Img: string) => {
    const data = new FormData();
    data.append("order_hash", this.getHash());

    data.append("image", base64Img);

    const config = this.createConfig(
      `${this.apiUrl}/order/message/send_image`,
      data
    );

    return await axios.request(config);
  };

  continueOrder = async () => {
    const data = new FormData();
    data.append("order_hash", this.getHash());

    const config = this.createConfig(`${this.apiUrl}/order/continue`, data);

    return await axios.request(config);
  };

  getAPILink = () => {
    return `${this.apiUrl}/order`;
  };
}

const orderAPI = new OrderAPI("http://127.0.0.1:8000/api");
export { orderAPI };
