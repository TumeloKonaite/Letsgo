import assert from "node:assert/strict";
import test from "node:test";

import {
  buildBookingPayload,
  createBookingSelection,
  createSubmissionLock,
  getBookingErrorState,
  getUnavailableDepartureLabel,
  isDepartureBookable,
  validateBookingDraft,
} from "../src/booking/bookingForm.js";

const available = { id: 42, status: "available", spots_available: 3, start_date: "2027-01-09", end_date: "2027-01-15" };
const packageDetail = { id: 12, slug: "garden-route", title: "Garden Route Escape", price_from: "9999", capacity: 20 };

test("only available departures with remaining spots are bookable", () => {
  assert.equal(isDepartureBookable(available), true);
  assert.equal(isDepartureBookable({ ...available, spots_available: 0 }), false);
  assert.equal(isDepartureBookable({ ...available, status: "closed" }), false);
  assert.equal(isDepartureBookable({ ...available, status: "sold_out" }), false);
  assert.equal(getUnavailableDepartureLabel({ ...available, status: "closed" }), "Booking closed");
  assert.equal(getUnavailableDepartureLabel({ ...available, spots_available: 0 }), "Sold out");
});

test("selection stores only display identity values and resets guest count", () => {
  assert.deepEqual(createBookingSelection(packageDetail, available), {
    packageId: 12, packageSlug: "garden-route", packageTitle: "Garden Route Escape",
    availabilityId: 42, startDate: "2027-01-09", endDate: "2027-01-15", numberOfPeople: 1,
  });
});

test("booking payload matches the backend contract and trims strings", () => {
  const payload = buildBookingPayload({
    ...createBookingSelection(packageDetail, available), numberOfPeople: 3,
    customerName: "  Amina Dlamini ", customerEmail: " amina@example.com ",
    customerPhone: " +27 82 555 0100 ", specialRequests: "   ",
  });
  assert.deepEqual(payload, {
    package_id: 12, availability_id: 42, customer_name: "Amina Dlamini",
    customer_email: "amina@example.com", customer_phone: "+27 82 555 0100",
    number_of_people: 3, special_requests: null,
  });
  assert.deepEqual(Object.keys(payload), ["package_id", "availability_id", "customer_name", "customer_email", "customer_phone", "number_of_people", "special_requests"]);
});

test("booking validation enforces backend field limits", () => {
  const valid = { ...createBookingSelection(packageDetail, available), customerName: "Amina", customerEmail: "amina@example.com", customerPhone: "12345", specialRequests: "" };
  assert.deepEqual(validateBookingDraft(valid), {});
  const errors = validateBookingDraft({ ...valid, numberOfPeople: 101, customerName: "", customerEmail: "invalid", customerPhone: "1234", specialRequests: "x".repeat(2001) });
  assert.deepEqual(Object.keys(errors), ["numberOfPeople", "customerName", "customerEmail", "customerPhone", "specialRequests"]);
});

test("submission lock prevents a duplicate pending request", () => {
  const lock = createSubmissionLock();
  assert.equal(lock.acquire(), true);
  assert.equal(lock.acquire(), false);
  lock.release();
  assert.equal(lock.acquire(), true);
});

test("409 and 422 failures produce conflict and field-specific states", () => {
  const conflict = getBookingErrorState(Object.assign(new Error("No places remain."), { status: 409 }));
  assert.equal(conflict.isConflict, true);
  assert.match(conflict.message, /choose another departure/);
  const invalid = getBookingErrorState(Object.assign(new Error("Invalid"), { status: 422, fieldErrors: { customer_email: "Invalid email", number_of_people: "Too many guests" } }));
  assert.deepEqual(invalid.fieldErrors, { customerEmail: "Invalid email", numberOfPeople: "Too many guests" });
});
