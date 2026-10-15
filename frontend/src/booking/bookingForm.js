const EMAIL_PATTERN = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

export const BOOKING_FIELD_NAMES = {
  number_of_people: "numberOfPeople",
  customer_name: "customerName",
  customer_email: "customerEmail",
  customer_phone: "customerPhone",
  special_requests: "specialRequests",
};

export function isDepartureBookable(availability) {
  return availability?.status === "available" && Number(availability?.spots_available) > 0;
}

export function getUnavailableDepartureLabel(availability) {
  if (Number(availability?.spots_available) <= 0) return "Sold out";
  const status = String(availability?.status || "").toLowerCase();
  if (status === "closed") return "Booking closed";
  if (status === "sold_out" || status === "sold-out") return "Sold out";
  return "Unavailable";
}

export function createBookingSelection(packageDetail, availability) {
  return {
    packageId: packageDetail.id,
    packageSlug: packageDetail.slug,
    packageTitle: packageDetail.title,
    availabilityId: availability.id,
    startDate: availability.start_date,
    endDate: availability.end_date,
    numberOfPeople: 1,
  };
}

export function buildBookingPayload(draft) {
  const specialRequests = String(draft.specialRequests || "").trim();
  return {
    package_id: draft.packageId,
    availability_id: draft.availabilityId,
    customer_name: String(draft.customerName || "").trim(),
    customer_email: String(draft.customerEmail || "").trim(),
    customer_phone: String(draft.customerPhone || "").trim(),
    number_of_people: draft.numberOfPeople,
    special_requests: specialRequests || null,
  };
}

export function validateBookingDraft(draft) {
  const errors = {};
  const name = String(draft.customerName || "").trim();
  const email = String(draft.customerEmail || "").trim();
  const phone = String(draft.customerPhone || "").trim();
  const specialRequests = String(draft.specialRequests || "").trim();

  if (!Number.isInteger(draft.numberOfPeople) || draft.numberOfPeople < 1) errors.numberOfPeople = "Enter at least 1 guest.";
  else if (draft.numberOfPeople > 100) errors.numberOfPeople = "A booking request can include at most 100 guests.";
  if (!name) errors.customerName = "Enter your full name.";
  else if (name.length > 255) errors.customerName = "Full name must be 255 characters or fewer.";
  if (!email) errors.customerEmail = "Enter your email address.";
  else if (email.length > 320 || !EMAIL_PATTERN.test(email)) errors.customerEmail = "Enter a valid email address of 320 characters or fewer.";
  if (!phone) errors.customerPhone = "Enter your phone number.";
  else if (phone.length < 5 || phone.length > 50) errors.customerPhone = "Phone number must be between 5 and 50 characters.";
  if (specialRequests.length > 2000) errors.specialRequests = "Special requests must be 2,000 characters or fewer.";
  return errors;
}

export function mapBookingFieldErrors(fieldErrors = {}) {
  return Object.entries(fieldErrors).reduce((mappedErrors, [field, message]) => {
    const draftField = BOOKING_FIELD_NAMES[field];
    if (draftField) mappedErrors[draftField] = message;
    return mappedErrors;
  }, {});
}

export function createSubmissionLock() {
  let locked = false;
  return {
    acquire() {
      if (locked) return false;
      locked = true;
      return true;
    },
    release() {
      locked = false;
    },
  };
}

export function getBookingErrorState(error) {
  const fieldErrors = mapBookingFieldErrors(error?.fieldErrors);
  if (error?.status === 409) {
    return {
      fieldErrors,
      isConflict: true,
      message: `${error.message} Return to the package page and choose another departure.`,
    };
  }
  if (Object.keys(fieldErrors).length > 0) {
    return { fieldErrors, isConflict: false, message: "Please correct the highlighted fields and try again." };
  }
  return {
    fieldErrors,
    isConflict: false,
    message: error?.message || "Unable to submit your booking request. Please try again.",
  };
}
