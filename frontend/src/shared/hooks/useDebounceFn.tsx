import { Dispatch, SetStateAction, useEffect, useRef, useState } from "react";

export const useDebounceFnRes = <G, S>({
  value,
  callback,
  delay,
}: {
  value: G;
  callback: (value: G) => S;
  delay: number;
}) => {
  const [debouncedValue, setDebouncedValue] = useState<S | null>(null);
  const timer = useRef<NodeJS.Timeout>();
  useEffect(() => {
    clearTimeout(timer.current);

    timer.current = setTimeout(() => {
      const newValue = callback(value);
      setDebouncedValue(newValue);
    }, delay);

    return () => clearTimeout(timer.current);
  }, [value]);

  return [debouncedValue, setDebouncedValue] as [
    S,
    Dispatch<SetStateAction<S>>,
  ];
};
