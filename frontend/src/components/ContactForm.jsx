import { useState } from "react";

import { submitContactRequest } from "../lib/api";

const initialFormValues = {
  first_name: "",
  last_name: "",
  email: "",
  phone: "",
  subject: "",
  message: "",
};

export function ContactForm() {
  const [formValues, setFormValues] = useState(initialFormValues);
  const [fieldErrors, setFieldErrors] = useState({});
  const [statusMessage, setStatusMessage] = useState("");
  const [statusTone, setStatusTone] = useState("idle");
  const [isSubmitting, setIsSubmitting] = useState(false);

  function handleChange(event) {
    const { name, value } = event.target;

    setFormValues((currentValues) => ({
      ...currentValues,
      [name]: value,
    }));

    setFieldErrors((currentErrors) => {
      if (!(name in currentErrors)) {
        return currentErrors;
      }

      const nextErrors = { ...currentErrors };
      delete nextErrors[name];
      return nextErrors;
    });

    if (statusTone !== "idle") {
      setStatusMessage("");
      setStatusTone("idle");
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setIsSubmitting(true);
    setFieldErrors({});
    setStatusMessage("");
    setStatusTone("idle");

    try {
      const response = await submitContactRequest(formValues);
      setFormValues(initialFormValues);
      setStatusMessage(response?.message || "Contact request submitted successfully.");
      setStatusTone("success");
    } catch (requestError) {
      const nextFieldErrors = requestError?.fieldErrors || {};

      setFieldErrors(nextFieldErrors);
      setStatusMessage(
        Object.keys(nextFieldErrors).length > 0
          ? "Please correct the highlighted fields and try again."
          : requestError.message || "Unable to send contact request."
      );
      setStatusTone("error");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form className="contact-form fade-up" onSubmit={handleSubmit} noValidate>
      <div className="contact-form__header">
        <span className="eyebrow">Enquiries</span>
        <h4>Send the LetsGoSouth team a direct message</h4>
        <p>
          Share what you are planning and we will reply with the right next step.
        </p>
      </div>

      <div className="contact-form__grid">
        <label className="contact-form__field" htmlFor="contact-first-name">
          <span>First name</span>
          <input
            id="contact-first-name"
            name="first_name"
            type="text"
            autoComplete="given-name"
            value={formValues.first_name}
            onChange={handleChange}
            aria-invalid={fieldErrors.first_name ? "true" : "false"}
          />
          {fieldErrors.first_name ? (
            <p className="contact-form__field-error">{fieldErrors.first_name}</p>
          ) : null}
        </label>

        <label className="contact-form__field" htmlFor="contact-last-name">
          <span>Last name</span>
          <input
            id="contact-last-name"
            name="last_name"
            type="text"
            autoComplete="family-name"
            value={formValues.last_name}
            onChange={handleChange}
            aria-invalid={fieldErrors.last_name ? "true" : "false"}
          />
          {fieldErrors.last_name ? (
            <p className="contact-form__field-error">{fieldErrors.last_name}</p>
          ) : null}
        </label>

        <label className="contact-form__field" htmlFor="contact-email">
          <span>Email</span>
          <input
            id="contact-email"
            name="email"
            type="email"
            autoComplete="email"
            value={formValues.email}
            onChange={handleChange}
            aria-invalid={fieldErrors.email ? "true" : "false"}
          />
          {fieldErrors.email ? (
            <p className="contact-form__field-error">{fieldErrors.email}</p>
          ) : null}
        </label>

        <label className="contact-form__field" htmlFor="contact-phone">
          <span>Phone</span>
          <input
            id="contact-phone"
            name="phone"
            type="tel"
            autoComplete="tel"
            value={formValues.phone}
            onChange={handleChange}
            aria-invalid={fieldErrors.phone ? "true" : "false"}
          />
          {fieldErrors.phone ? (
            <p className="contact-form__field-error">{fieldErrors.phone}</p>
          ) : null}
        </label>

        <label
          className="contact-form__field contact-form__field--full"
          htmlFor="contact-subject"
        >
          <span>Subject</span>
          <input
            id="contact-subject"
            name="subject"
            type="text"
            autoComplete="off"
            value={formValues.subject}
            onChange={handleChange}
            aria-invalid={fieldErrors.subject ? "true" : "false"}
          />
          {fieldErrors.subject ? (
            <p className="contact-form__field-error">{fieldErrors.subject}</p>
          ) : null}
        </label>

        <label
          className="contact-form__field contact-form__field--full"
          htmlFor="contact-message"
        >
          <span>Message</span>
          <textarea
            id="contact-message"
            name="message"
            rows="6"
            value={formValues.message}
            onChange={handleChange}
            aria-invalid={fieldErrors.message ? "true" : "false"}
          />
          {fieldErrors.message ? (
            <p className="contact-form__field-error">{fieldErrors.message}</p>
          ) : null}
        </label>
      </div>

      {statusMessage ? (
        <div
          className={`contact-form__status contact-form__status--${statusTone}`}
          role={statusTone === "error" ? "alert" : "status"}
        >
          {statusMessage}
        </div>
      ) : null}

      <button className="button contact-form__submit" type="submit" disabled={isSubmitting}>
        {isSubmitting ? "Sending enquiry..." : "Send enquiry"}
      </button>
    </form>
  );
}
