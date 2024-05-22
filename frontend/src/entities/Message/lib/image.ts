import { getDateFromMessage } from "$/widgets/Chat/lib/message";

export const generateImageName = (url: string) => {
  const matches = url.match(/data:([a-zA-Z0-9]+\/[a-zA-Z0-9-.+]+).*,/);
  const extenstion = matches ? matches[1].split("/")[1] : "";
  return `${(Math.random() + 1).toString(36).substring(7)}.${extenstion}`;
};

export const generateDateForOpenedImage = (datetime: string) => {
  return new Date(getDateFromMessage(datetime))
    .toLocaleDateString("ru-RU", {
      day: "numeric",
      month: "long",
      hour: "numeric",
      minute: "numeric",
    })
    .replace(" в ", ", ");
};
