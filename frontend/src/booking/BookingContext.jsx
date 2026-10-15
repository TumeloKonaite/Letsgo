import { createContext, useCallback, useContext, useMemo, useState } from "react";

import {
  createEmptyBookingDraft,
  mergeBookingDraft,
  persistBookingDraft,
  removeBookingDraft,
  restoreBookingDraft,
} from "./bookingDraft.js";

const BookingContext = createContext(null);

function getSessionStorage() {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

export function BookingProvider({ children }) {
  const [draft, setDraft] = useState(() => restoreBookingDraft(getSessionStorage()));

  const updateDraft = useCallback((partialDraft) => {
    setDraft((currentDraft) => {
      const nextDraft = mergeBookingDraft(currentDraft, partialDraft);
      persistBookingDraft(getSessionStorage(), nextDraft);
      return nextDraft;
    });
  }, []);

  const clearDraft = useCallback(() => {
    removeBookingDraft(getSessionStorage());
    setDraft(createEmptyBookingDraft());
  }, []);

  const value = useMemo(
    () => ({ draft, updateDraft, clearDraft }),
    [draft, updateDraft, clearDraft]
  );

  return <BookingContext.Provider value={value}>{children}</BookingContext.Provider>;
}

export function useBooking() {
  const context = useContext(BookingContext);
  if (!context) {
    throw new Error("useBooking must be used inside BookingProvider");
  }
  return context;
}
