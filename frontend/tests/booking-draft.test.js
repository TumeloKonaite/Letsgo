import assert from "node:assert/strict";
import test from "node:test";

import {
  BOOKING_DRAFT_STORAGE_KEY,
  createEmptyBookingDraft,
  deserializeBookingDraft,
  mergeBookingDraft,
  persistBookingDraft,
  removeBookingDraft,
  restoreBookingDraft,
} from "../src/booking/bookingDraft.js";

function createStorage(initialValue = null) {
  const values = new Map();
  if (initialValue !== null) {
    values.set(BOOKING_DRAFT_STORAGE_KEY, initialValue);
  }

  return {
    getItem(key) {
      return values.get(key) ?? null;
    },
    setItem(key, value) {
      values.set(key, value);
    },
    removeItem(key) {
      values.delete(key);
    },
    has(key) {
      return values.has(key);
    },
  };
}

test("missing storage restores the default booking draft", () => {
  assert.deepEqual(restoreBookingDraft(createStorage()), createEmptyBookingDraft());
  assert.deepEqual(restoreBookingDraft(null), createEmptyBookingDraft());
});

test("supported fields survive a persistence round trip without changing dates", () => {
  const storage = createStorage();
  const draft = mergeBookingDraft(createEmptyBookingDraft(), {
    packageId: 12,
    packageSlug: "garden-route",
    packageTitle: "Garden Route Escape",
    availabilityId: 42,
    startDate: "2027-01-09",
    endDate: "2027-01-15",
    numberOfPeople: 3,
    customerName: "Amina Dlamini",
    customerEmail: "amina@example.com",
    customerPhone: "+27 82 555 0100",
    specialRequests: "Vegetarian meals, please.",
  });

  persistBookingDraft(storage, draft);

  assert.deepEqual(restoreBookingDraft(storage), draft);
  assert.equal(restoreBookingDraft(storage).startDate, "2027-01-09");
});

test("corrupt, structurally invalid, and unsupported stored data falls back safely", () => {
  const invalidValues = [
    "not json",
    JSON.stringify({ version: 2, draft: {} }),
    JSON.stringify({ version: 1, draft: [] }),
    JSON.stringify({ version: 1, draft: { packageId: "12" } }),
    JSON.stringify({ version: 1, draft: { startDate: "09/01/2027" } }),
    JSON.stringify({ version: 1, draft: { startDate: "2027-02-29" } }),
    JSON.stringify({ version: 1, draft: { numberOfPeople: 0 } }),
  ];

  for (const invalidValue of invalidValues) {
    assert.deepEqual(deserializeBookingDraft(invalidValue), createEmptyBookingDraft());
  }
});

test("unknown properties are discarded when restoring and updating", () => {
  const serialized = JSON.stringify({
    version: 1,
    draft: {
      packageId: 12,
      packageTitle: "Garden Route Escape",
      price: "9999.00",
      capacity: 20,
      status: "available",
    },
  });
  const restored = deserializeBookingDraft(serialized);
  const updated = mergeBookingDraft(restored, { customerName: "Amina", remainingSpots: 4 });

  assert.equal(restored.packageId, 12);
  assert.equal(updated.customerName, "Amina");
  assert.equal("price" in restored, false);
  assert.equal("capacity" in restored, false);
  assert.equal("status" in restored, false);
  assert.equal("remainingSpots" in updated, false);
});

test("clearing removes the persisted draft", () => {
  const storage = createStorage();
  persistBookingDraft(storage, { ...createEmptyBookingDraft(), packageId: 12 });
  assert.equal(storage.has(BOOKING_DRAFT_STORAGE_KEY), true);

  removeBookingDraft(storage);

  assert.equal(storage.has(BOOKING_DRAFT_STORAGE_KEY), false);
  assert.deepEqual(restoreBookingDraft(storage), createEmptyBookingDraft());
});

test("storage read, write, and removal failures do not escape", () => {
  const throwingStorage = {
    getItem() {
      throw new Error("blocked");
    },
    setItem() {
      throw new Error("blocked");
    },
    removeItem() {
      throw new Error("blocked");
    },
  };

  assert.deepEqual(restoreBookingDraft(throwingStorage), createEmptyBookingDraft());
  assert.doesNotThrow(() => persistBookingDraft(throwingStorage, createEmptyBookingDraft()));
  assert.doesNotThrow(() => removeBookingDraft(throwingStorage));
});
