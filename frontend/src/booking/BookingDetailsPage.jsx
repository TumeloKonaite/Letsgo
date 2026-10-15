import { useRef, useState } from "react";
import { Link, Navigate } from "react-router-dom";

import { formatDateRange } from "../lib/formatters.js";
import { useBooking } from "./BookingContext.jsx";
import { submitBookingRequest } from "./bookingApi.js";
import { hasBookingSelection } from "./bookingDraft.js";
import { createSubmissionLock, getBookingErrorState, validateBookingDraft } from "./bookingForm.js";

const FIELD_IDS = {
  numberOfPeople: "booking-number-of-people",
  customerName: "booking-customer-name",
  customerEmail: "booking-customer-email",
  customerPhone: "booking-customer-phone",
  specialRequests: "booking-special-requests",
};

function FieldError({ field, errors }) {
  return errors[field] ? (
    <p className="booking-form__field-error" id={`${FIELD_IDS[field]}-error`}>
      {errors[field]}
    </p>
  ) : null;
}

export function BookingDetailsPage() {
  const { draft, updateDraft } = useBooking();
  const [fieldErrors, setFieldErrors] = useState({});
  const [statusMessage, setStatusMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [booking, setBooking] = useState(null);
  const submissionLock = useRef(null);
  if (!submissionLock.current) submissionLock.current = createSubmissionLock();
  const formRef = useRef(null);

  if (!hasBookingSelection(draft)) {
    return <Navigate to="/packages" replace />;
  }

  function clearFieldError(field) {
    setFieldErrors((currentErrors) => {
      if (!(field in currentErrors)) return currentErrors;
      const nextErrors = { ...currentErrors };
      delete nextErrors[field];
      return nextErrors;
    });
    setStatusMessage("");
  }

  function handleTextChange(event) {
    const { name, value } = event.target;
    updateDraft({ [name]: value });
    clearFieldError(name);
  }

  function handleGuestChange(event) {
    const value = event.target.valueAsNumber;
    if (Number.isInteger(value)) updateDraft({ numberOfPeople: value });
    clearFieldError("numberOfPeople");
  }

  function focusFirstError(errors) {
    const firstField = Object.keys(FIELD_IDS).find((field) => errors[field]);
    if (firstField) formRef.current?.querySelector(`#${FIELD_IDS[firstField]}`)?.focus();
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (booking) return;

    const validationErrors = validateBookingDraft(draft);
    if (Object.keys(validationErrors).length > 0) {
      setFieldErrors(validationErrors);
      setStatusMessage("Please correct the highlighted fields and try again.");
      focusFirstError(validationErrors);
      return;
    }

    if (!submissionLock.current.acquire()) return;
    setIsSubmitting(true);
    setFieldErrors({});
    setStatusMessage("");
    try {
      setBooking(await submitBookingRequest(draft));
    } catch (requestError) {
      const errorState = getBookingErrorState(requestError);
      setFieldErrors(errorState.fieldErrors);
      setStatusMessage(errorState.message);
      if (Object.keys(errorState.fieldErrors).length > 0) focusFirstError(errorState.fieldErrors);
    } finally {
      submissionLock.current.release();
      setIsSubmitting(false);
    }
  }

  if (booking) {
    return (
      <main className="page">
        <div className="container booking-page">
          <section className="booking-success" role="status" aria-live="polite">
            <span className="eyebrow-dark">Request received</span>
            <h1>Thank you, {booking.customer_name || draft.customerName}</h1>
            <p>Your booking request has been submitted. Our team will contact you to confirm the details.</p>
            <p className="booking-success__reference">Booking reference: <strong>{booking.id}</strong></p>
            <Link className="button" to="/packages">Browse packages</Link>
          </section>
        </div>
      </main>
    );
  }

  const isConflict = statusMessage.includes("choose another departure");

  return (
    <main className="page">
      <div className="container booking-page">
        <header className="booking-page__header">
          <span className="eyebrow-dark">Booking request</span>
          <h1>Tell us who is travelling</h1>
          <p>This sends a booking request. Our team will contact you to confirm availability, details, and pricing.</p>
        </header>

        <div className="booking-layout">
          <aside className="booking-review" aria-labelledby="booking-review-title">
            <h2 id="booking-review-title">Your selected trip</h2>
            <dl>
              <div><dt>Package</dt><dd>{draft.packageTitle}</dd></div>
              <div><dt>Departure</dt><dd>{formatDateRange(draft.startDate, draft.endDate)}</dd></div>
              <div><dt>Guests</dt><dd>{draft.numberOfPeople}</dd></div>
              <div><dt>Name</dt><dd>{draft.customerName || "Not entered yet"}</dd></div>
              <div><dt>Email</dt><dd>{draft.customerEmail || "Not entered yet"}</dd></div>
              <div><dt>Phone</dt><dd>{draft.customerPhone || "Not entered yet"}</dd></div>
              <div><dt>Special requests</dt><dd>{draft.specialRequests || "None"}</dd></div>
            </dl>
          </aside>

          <form ref={formRef} className="booking-form" onSubmit={handleSubmit} noValidate>
            <label className="booking-form__field" htmlFor={FIELD_IDS.numberOfPeople}>
              <span>Number of people</span>
              <input id={FIELD_IDS.numberOfPeople} name="numberOfPeople" type="number" required min="1" max="100" step="1" value={draft.numberOfPeople} onChange={handleGuestChange} aria-invalid={fieldErrors.numberOfPeople ? "true" : "false"} aria-describedby={fieldErrors.numberOfPeople ? `${FIELD_IDS.numberOfPeople}-error` : undefined} />
              <FieldError field="numberOfPeople" errors={fieldErrors} />
            </label>
            <label className="booking-form__field" htmlFor={FIELD_IDS.customerName}>
              <span>Full name</span>
              <input id={FIELD_IDS.customerName} name="customerName" type="text" required maxLength="255" autoComplete="name" value={draft.customerName} onChange={handleTextChange} aria-invalid={fieldErrors.customerName ? "true" : "false"} aria-describedby={fieldErrors.customerName ? `${FIELD_IDS.customerName}-error` : undefined} />
              <FieldError field="customerName" errors={fieldErrors} />
            </label>
            <label className="booking-form__field" htmlFor={FIELD_IDS.customerEmail}>
              <span>Email address</span>
              <input id={FIELD_IDS.customerEmail} name="customerEmail" type="email" required maxLength="320" autoComplete="email" value={draft.customerEmail} onChange={handleTextChange} aria-invalid={fieldErrors.customerEmail ? "true" : "false"} aria-describedby={fieldErrors.customerEmail ? `${FIELD_IDS.customerEmail}-error` : undefined} />
              <FieldError field="customerEmail" errors={fieldErrors} />
            </label>
            <label className="booking-form__field" htmlFor={FIELD_IDS.customerPhone}>
              <span>Phone number</span>
              <input id={FIELD_IDS.customerPhone} name="customerPhone" type="tel" required minLength="5" maxLength="50" autoComplete="tel" value={draft.customerPhone} onChange={handleTextChange} aria-invalid={fieldErrors.customerPhone ? "true" : "false"} aria-describedby={fieldErrors.customerPhone ? `${FIELD_IDS.customerPhone}-error` : undefined} />
              <FieldError field="customerPhone" errors={fieldErrors} />
            </label>
            <label className="booking-form__field booking-form__field--full" htmlFor={FIELD_IDS.specialRequests}>
              <span>Special requests (optional)</span>
              <textarea id={FIELD_IDS.specialRequests} name="specialRequests" rows="5" maxLength="2000" value={draft.specialRequests} onChange={handleTextChange} aria-invalid={fieldErrors.specialRequests ? "true" : "false"} aria-describedby={fieldErrors.specialRequests ? `${FIELD_IDS.specialRequests}-error` : undefined} />
              <FieldError field="specialRequests" errors={fieldErrors} />
            </label>

            <div className="booking-form__status" role="alert" aria-live="assertive">
              {statusMessage ? <p>{statusMessage}</p> : null}
              {isConflict ? <Link to={`/packages/${draft.packageSlug}`}>Choose another departure</Link> : null}
            </div>

            <button className="button booking-form__submit" type="submit" disabled={isSubmitting} aria-busy={isSubmitting ? "true" : "false"}>
              {isSubmitting ? "Submitting booking request..." : "Submit booking request"}
            </button>
          </form>
        </div>
      </div>
    </main>
  );
}
