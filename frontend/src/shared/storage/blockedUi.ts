import { create } from "zustand";

interface BlockedUIStore {
  isTokenAlreadyBlocked: "getting" | "sending" | null;
  setTokenAlreadyBlocked: (value: "getting" | "sending") => void;
}

export const useBlockedUiStore = create<BlockedUIStore>((set) => ({
  isTokenAlreadyBlocked: null,
  setTokenAlreadyBlocked: (value) =>
    set(() => ({ isTokenAlreadyBlocked: value })),
}));
