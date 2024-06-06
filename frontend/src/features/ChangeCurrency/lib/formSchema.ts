import { z } from "zod";

export const FormSchema = z.object({
  fullName: z.string().optional(),
  fromWalletAddress: z
    .string({ required_error: "Это поле обязательное" })
    .min(1, { message: "Это поле обязательное" }),
  toWalletAddress: z
    .string({ required_error: "Это поле обязательное" })
    .min(1, { message: "Это поле обязательное" }),
  fromCardNumber: z
    .string({ required_error: "Это поле обязательное" })
    .min(19, { message: "Номер карты состоит из 16 цифр" })
    .max(19, { message: "Номер карты состоит из 16 цифр" }),
  toCardNumber: z
    .string({ required_error: "Это поле обязательное" })
    .min(19, { message: "Номер карты состоит из 16 цифр" })
    .max(19, { message: "Номер карты состоит из 16 цифр" }),
  email: z
    .string({ required_error: "Это поле обязательное" })
    .min(1, { message: "Это поле обязательное" })
    .email({
      message: "Нужно ввести правильную почту! (example@gmail.com)",
    }),
  agreement: z.boolean(),
  personalData: z.boolean(),
});
