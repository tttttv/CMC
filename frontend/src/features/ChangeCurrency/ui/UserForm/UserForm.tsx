import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { AxiosError } from "axios";
import { useEffect, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";
import { ErrorCodeModal } from "../modals/ErrorCodeModal";
import { orderAPI } from "$/shared/api/order";
import useCurrencyStore from "$/shared/storage/currency";
import usePlaceOrder from "$/shared/storage/placeOrder";

import Button from "$/shared/ui/kit/Button/Button";
import Checkbox from "$/shared/ui/kit/Checkbox";
import Input from "$/shared/ui/kit/Input";
import styles from "./UserForm.module.scss";
import { SetupWidgetEnv } from "./SetupWidgetEnv";
import { setupOrderHash } from "$/shared/helpers/orderHash/setup";
import { useCurrency } from "$/shared/hooks/useCurrency";
import { useExchangeSettings } from "$/shared/storage/exchangeSettings";
import { useWidgetEnv } from "$/pages/WidgetEnv/model/widgetEnv";
import { BankCardInput } from "$/shared/ui/kit/BankCardInput";
import { ChainSelect } from "./ChainSelect";
import { FormSchema } from "../../lib/formSchema";
import { Order } from "$/shared/types/api/params";
import { deleteSpaces } from "../../lib/form";

export const UserForm = () => {
  const { to, from } = useCurrency();
  const { toCurrency, fromCurrency } = useCurrencyStore();
  const { fromType, toType } = useExchangeSettings();
  const { fromChain, toChain, setToChain, setFromChain, orderData } =
    usePlaceOrder();
  const {
    name,
    email,
    withdrawing_token,
    withdrawing_address,
    withdrawing_chain,
  } = useWidgetEnv((state) => state.widgetEnv);

  const isNameBlocked = !!name;
  const isEmailBlocked = !!email;
  const isAddressBlocked = !!withdrawing_address;
  const isToChainBlocked = !!withdrawing_chain;

  const isFromCrypto = fromType === "crypto";
  const isHasCrypto = isFromCrypto || toType === "crypto";

  const fromChains = isHasCrypto
    ? from?.data?.crypto?.find(
        (chain) => String(chain.id) === String(fromCurrency)
      )?.chains || []
    : [];

  const toChains = isHasCrypto
    ? to.data?.crypto?.find(
        (chain) =>
          String(chain.id) === (String(toCurrency) || withdrawing_token)
      )?.chains || []
    : [];

  const [error, setErrorCode] = useState<{ code: number; message: string }>({
    code: -1,
    message: "",
  });

  const {
    control,
    handleSubmit,
    formState: { errors },
    register,
    watch,
    clearErrors,
    setError,
    setValue,
    getValues,
  } = useForm<z.infer<typeof FormSchema>>({
    resolver: zodResolver(FormSchema),
  });

  const { isPending: isOrderCreating, mutate: createOrder } = useMutation({
    mutationKey: ["order"],
    mutationFn: orderAPI.createOrder,
    onSuccess: (data) => {
      const { order_hash } = data.data;
      setupOrderHash(order_hash);

      navigate({
        to: "/$widgetId/order",
        params: {
          widgetId: JSON.stringify(localStorage.getItem("widgetId")),
        },
      });
    },
    onError: (error: AxiosError<{ message: string; code: number }>) => {
      if (error.response) {
        setErrorCode(error.response.data);
      }
    },
  });

  const agreement = watch(["agreement", "personalData"]);

  const buttonDisabled = !(
    orderData !== null &&
    (toType === "crypto" ? !!toChain : true) &&
    (fromType === "crypto" ? !!fromChain : true) &&
    agreement[0] &&
    agreement[1]
  );

  const navigate = useNavigate();
  const onSubmitHandler = (data: z.infer<typeof FormSchema>) => {
    const newOrder: Order = {
      email: data.email,
      payment_method: +fromCurrency,
      payment_chain: fromChain,
      payment_address: deleteSpaces(
        (fromType === "bank" ? data.fromCardNumber : data.fromWalletAddress) ||
          ""
      ),
      withdraw_method: +toCurrency,
      withdraw_chain: toChain,
      withdraw_address: deleteSpaces(
        (toType === "bank" ? data.toCardNumber : data.toWalletAddress) || ""
      ),
      name_withdraw: data.withdrawName,
      name_payment: data.paymentName,
      ...orderData!,
    };

    createOrder(newOrder);
  };

  const errorHandler = () => {
    const {
      fromCardNumber,
      fromWalletAddress,
      toCardNumber,
      toWalletAddress,
      email,
      paymentName,
      withdrawName,
    } = getValues();

    if (
      fromType === "bank" &&
      (paymentName === "" || fromCardNumber.length !== 19)
    )
      return;

    if (
      toType === "bank" &&
      (toCardNumber.length !== 19 || withdrawName === "")
    )
      return;
    if (fromType === "crypto" && fromWalletAddress === "") return;
    if (toType === "crypto" && toWalletAddress === "") return;

    if (errors?.email?.message) return;

    onSubmitHandler({
      email,
      withdrawName: withdrawName,
      paymentName: paymentName,
      fromCardNumber,
      fromWalletAddress,
      toCardNumber,
      toWalletAddress,
      agreement: true,
      personalData: true,
    });
  };

  const [fromChainDefault, setFromChainDefault] = useState<string>("");
  const [toChainDefault, setToChainDefault] = useState<string>("");

  useEffect(() => {
    if (fromType === "crypto") setFromChainDefault(fromChains[0]?.id);
  }, [fromCurrency]);
  useEffect(() => {
    if (toType === "crypto") setToChainDefault(toChains[0]?.id);
  }, [toCurrency]);

  return (
    <>
      <form
        className={styles.form}
        onSubmit={handleSubmit(onSubmitHandler, errorHandler)}
      >
        <ErrorCodeModal errorCode={error.code} errorText={error.message} />
        <h3 className={styles.title}>Ваши реквизиты</h3>
        <div className={styles.inputs}>
          {fromType === "bank" && (
            <Input
              disabled={isNameBlocked}
              register={register("paymentName")}
              label="ФИО Отправителя"
              importantMessage="Важно, если вы отправляете с карты"
              disabledStyle={isNameBlocked}
              errorText={errors.paymentName?.message}
              clearError={() => {
                clearErrors("paymentName");
              }}
            />
          )}
          {toType === "bank" && (
            <Input
              register={register("withdrawName")}
              label="ФИО Получателя"
              importantMessage="Важно, если вы отправляете с карты"
              errorText={errors.withdrawName?.message}
              clearError={() => {
                clearErrors("withdrawName");
              }}
            />
          )}

          {fromType === "bank" ? (
            <BankCardInput
              label={"Номер карты отправителя"}
              name="fromCardNumber"
              control={control}
              error={errors.fromCardNumber?.message || ""}
              setValue={(value) => setValue("fromCardNumber", value)}
              setError={(error) =>
                setError("fromCardNumber", {
                  type: "custom",
                  message: `${error}`,
                })
              }
              clearErrors={() => clearErrors("fromCardNumber")}
            />
          ) : (
            <Input
              register={register("fromWalletAddress")}
              label={`Адрес кошелька отправителя`}
              errorText={errors.fromWalletAddress?.message}
              clearError={() => clearErrors("fromWalletAddress")}
            />
          )}
          {toType === "bank" ? (
            <BankCardInput
              label={"Номер карты получателя"}
              name="toCardNumber"
              control={control}
              error={errors.toCardNumber?.message || ""}
              setValue={(value) => setValue("toCardNumber", value)}
              setError={(error) =>
                setError("toCardNumber", {
                  type: "custom",
                  message: `${error}`,
                })
              }
              clearErrors={() => clearErrors("toCardNumber")}
            />
          ) : (
            <Input
              register={register("toWalletAddress")}
              label={`Адрес кошелька получателя`}
              errorText={errors.toWalletAddress?.message}
              clearError={() => clearErrors("toWalletAddress")}
              disabledStyle={isAddressBlocked}
              disabled={isAddressBlocked}
            />
          )}

          {fromType === "crypto" && (
            <ChainSelect
              props={{
                control,
                chains: fromChains,
                isChainBlocked: false,
                setChain: (chain) => setFromChain(chain),
                chainDefaultValue: fromChainDefault,
                label: "Chain отправителя",
                name: "fromChain",
              }}
            />
          )}
          {toType === "crypto" && (
            <ChainSelect
              props={{
                control,
                chains: toChains,
                isChainBlocked: isToChainBlocked,
                setChain: (chain) => setToChain(chain),
                chainDefaultValue: toChainDefault,
                label: "Chain получателя",
                name: "toChain",
              }}
            />
          )}
          <Input
            register={register("email")}
            name="email"
            label="Адрес почты"
            errorText={errors.email?.message}
            clearError={() => clearErrors("email")}
            disabledStyle={isEmailBlocked}
            disabled={isEmailBlocked}
          />
        </div>
        <div className={styles.checkboxes}>
          <Controller
            control={control}
            name="personalData"
            defaultValue={false}
            render={({ field: { onChange, value } }) => (
              <Checkbox
                setChecked={onChange}
                label="	Даю согласие на обработку персональных данных"
                checked={value}
              />
            )}
          />
          <Controller
            control={control}
            name="agreement"
            render={({ field: { onChange, value } }) => (
              <Checkbox
                setChecked={onChange}
                label="Соглашаюсь с офертой"
                checked={value}
              />
            )}
          />
        </div>
        <Button disabled={buttonDisabled || isOrderCreating}>
          {isOrderCreating ? "Создаем обмен..." : "Перейти к оплате"}
        </Button>
      </form>
      <SetupWidgetEnv setValue={setValue} />
    </>
  );
};
