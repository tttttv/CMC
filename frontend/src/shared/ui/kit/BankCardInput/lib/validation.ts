export const validateCardInput: (value: string) => {
  value: string;
  errorStatus: "LENGTH" | "LETTER" | "ONE_LETTER" | undefined;
} = (value) => {
  if (value.length > 19) {
    return { value: "", errorStatus: "LENGTH" };
  }
  if (!Array.from(value.trim()).every((char) => /^[0-9\s]*$/.test(char))) {
    if (value.length === 1) {
      // фикс бага, когда вводится одна буква
      return { value: "", errorStatus: "ONE_LETTER" };
    }

    return { value: "", errorStatus: "LETTER" };
  }

  const newValue = value
    .replace(" ", "")
    .split(/(\d{4})/)
    .filter((w: string) => w.length > 0)
    .map((w: string) => {
      return w.trim();
    })
    .join(" ")
    .split(" ")
    .filter((w: string) => w !== "")
    .join(" ");
  return {
    value: newValue,
    errorStatus: undefined,
  };
};
