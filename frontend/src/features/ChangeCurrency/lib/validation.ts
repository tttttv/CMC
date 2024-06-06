export const validateCurrencyInput = (value: string) => {
  if (+value === 0 || value === "") {
    return "0";
  }

  let preparedValue = value.trim().replace(",", ".").replace(/^0+/, "");
  if (preparedValue.startsWith(".")) {
    preparedValue = `0${preparedValue}`;
  }

  const strArray = Array.from(preparedValue);
  if (strArray.filter((c) => c === ".").length > 1) return undefined;
  if (!/^\d*\.?\d*$/.test(preparedValue)) return undefined;

  return preparedValue;
};
