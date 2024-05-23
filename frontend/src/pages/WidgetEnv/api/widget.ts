import axios from "axios";
import { WidgetEnv } from "../../../shared/types/api/enitites";

class WidgetAPI {
  private apiUrl: string;
  constructor(apiUrl: string) {
    this.apiUrl = apiUrl;
  }

  async getWidgetEnv(widgetId: string) {
    const body = new FormData();
    const config = {
      method: "post",
      maxBodyLength: Infinity,
      url: `${this.apiUrl}/widget_settings`,
      data: body,
    };
    body.append("widget_hash", widgetId);
    return await axios.request<WidgetEnv>(config);
  }
}

export const widgetAPI = new WidgetAPI("http://127.0.0.1:8000/api");
