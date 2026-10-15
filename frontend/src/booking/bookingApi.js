import { request } from "../api/client.js";
import { buildBookingPayload } from "./bookingForm.js";

export function submitBookingRequest(draft) {
  return request(
    "/api/bookings",
    { method: "POST", body: JSON.stringify(buildBookingPayload(draft)) },
    "Unable to submit your booking request. Please try again."
  );
}
