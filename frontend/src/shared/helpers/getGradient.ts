import { TinyColor } from "@ctrl/tinycolor";

type Hex = string;
type Gradient = [Hex, Hex, Hex, Hex];

export const getGradient = (color: Hex) => {
  const tColor = new TinyColor(color);

  const gradient: Gradient = ["", "", "", ""];

  if (!tColor.isValid) return gradient;
  gradient[0] = color;
  gradient[1] = tColor.mix("#fff", 75).toHexString();
  gradient[2] = tColor.mix("#fff", 50).toHexString();
  gradient[3] = tColor.mix("#fff", 25).toHexString();

  return gradient;
};
