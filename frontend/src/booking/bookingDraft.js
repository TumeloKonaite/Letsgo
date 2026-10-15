export const BOOKING_DRAFT_STORAGE_KEY = "letsgosa-booking-draft-v1";
export const BOOKING_DRAFT_SCHEMA_VERSION = 1;

const STRING_FIELDS = [
  "packageSlug",
  "packageTitle",
  "startDate",
  "endDate",
  "customerName",
  "customerEmail",
  "customerPhone",
  "specialRequests",
];
const ID_FIELDS = ["packageId", "availabilityId"];
const RECOGNIZED_FIELDS = [...ID_FIELDS, ...STRING_FIELDS, "numberOfPeople"];
const DATE_ONLY_PATTERN = /^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$/;

export function createEmptyBookingDraft() {
  return {
    packageId: 0,
    packageSlug: "",
    packageTitle: "",
    availabilityId: 0,
    startDate: "",
    endDate: "",
    numberOfPeople: 1,
    customerName: "",
    customerEmail: "",
    customerPhone: "",
    specialRequests: "",
  };
}

function isRecord(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function isValidDateOnly(value) {
  if (value === "") {
    return true;
  }

  const match = DATE_ONLY_PATTERN.exec(value);
  if (!match) {
    return false;
  }

  const [year, month, day] = value.split("-").map(Number);
  const isLeapYear = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  const daysInMonth = [31, isLeapYear ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  return day <= daysInMonth[month - 1];
}

function isValidField(field, value) {
  if (ID_FIELDS.includes(field)) {
    return Number.isInteger(value) && value >= 0;
  }

  if (field === "numberOfPeople") {
    return Number.isInteger(value) && value > 0;
  }

  if (field === "startDate" || field === "endDate") {
    return typeof value === "string" && isValidDateOnly(value);
  }

  return STRING_FIELDS.includes(field) && typeof value === "string";
}

export function normalizeBookingDraft(value) {
  if (!isRecord(value)) {
    return null;
  }

  const draft = createEmptyBookingDraft();
  for (const field of RECOGNIZED_FIELDS) {
    if (Object.hasOwn(value, field)) {
      if (!isValidField(field, value[field])) {
        return null;
      }
      draft[field] = value[field];
    }
  }
  return draft;
}

export function mergeBookingDraft(currentDraft, partialDraft) {
  if (!isRecord(partialDraft)) {
    return currentDraft;
  }

  const nextDraft = { ...currentDraft };
  for (const field of RECOGNIZED_FIELDS) {
    if (Object.hasOwn(partialDraft, field) && isValidField(field, partialDraft[field])) {
      nextDraft[field] = partialDraft[field];
    }
  }
  return nextDraft;
}

export function serializeBookingDraft(draft) {
  const normalizedDraft = normalizeBookingDraft(draft) ?? createEmptyBookingDraft();
  return JSON.stringify({ version: BOOKING_DRAFT_SCHEMA_VERSION, draft: normalizedDraft });
}

export function deserializeBookingDraft(serializedValue) {
  if (typeof serializedValue !== "string" || serializedValue.length === 0) {
    return createEmptyBookingDraft();
  }

  try {
    const storedValue = JSON.parse(serializedValue);
    if (
      !isRecord(storedValue) ||
      storedValue.version !== BOOKING_DRAFT_SCHEMA_VERSION
    ) {
      return createEmptyBookingDraft();
    }
    return normalizeBookingDraft(storedValue.draft) ?? createEmptyBookingDraft();
  } catch {
    return createEmptyBookingDraft();
  }
}

export function restoreBookingDraft(storage) {
  try {
    return deserializeBookingDraft(storage?.getItem(BOOKING_DRAFT_STORAGE_KEY));
  } catch {
    return createEmptyBookingDraft();
  }
}

export function persistBookingDraft(storage, draft) {
  try {
    storage?.setItem(BOOKING_DRAFT_STORAGE_KEY, serializeBookingDraft(draft));
  } catch {
    // Storage can be unavailable or blocked; in-memory state remains usable.
  }
}

export function removeBookingDraft(storage) {
  try {
    storage?.removeItem(BOOKING_DRAFT_STORAGE_KEY);
  } catch {
    // Clearing in-memory state must still work when storage access is blocked.
  }
}

export function hasBookingSelection(draft) {
  return (
    Number.isInteger(draft?.packageId) &&
    draft.packageId > 0 &&
    Number.isInteger(draft?.availabilityId) &&
    draft.availabilityId > 0
  );
}
