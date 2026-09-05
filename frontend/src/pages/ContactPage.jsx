// Combine business contact details with the public enquiry form.

import { Link } from "react-router-dom";

import { ContactForm } from "../components/ContactForm";
import { PublicPageHero } from "../components/PublicPageHero";
import { contactDetails } from "../data/about";

const contactItems = [
  {
    kind: "phone",
    label: "Call us",
    value: contactDetails.phone,
    href: `tel:${contactDetails.phone.replace(/\s+/g, "")}`,
  },
  {
    kind: "email",
    label: "Email us",
    value: contactDetails.email,
    href: `mailto:${contactDetails.email}`,
  },
  {
    kind: "address",
    label: "Visit us",
    value: contactDetails.address,
  },
  {
    kind: "hours",
    label: "Office hours",
    value: contactDetails.officeHours,
  },
];

const trustPoints = [
  "Local travel guidance",
  "Personalized recommendations",
  "Quick response times",
  "Safari and cultural expertise",
];

export function ContactPage() {
  return (
    <main className="page">
      <PublicPageHero
        eyebrow="Contact Us"
        title="Start your South African travel enquiry here."
        description="Tell us what kind of trip you want to plan and we will help you take the next step, whether you are comparing packages or looking for practical travel support."
        variant="page-hero--contact"
      />

      <div className="container">
        <section className="section contact-page">
          <div className="contact-page__layout">
            <div className="contact-page__details">
              <div className="contact-panel fade-up">
                <span className="eyebrow-dark">Reach Out</span>
                <h2>Speak to the LetsGoSouth team</h2>
                <p>
                  Use the enquiry form for package questions, custom trip
                  planning, or availability requests.
                </p>
              </div>

              <div className="contact-panel contact-panel--trust fade-up">
                <span className="eyebrow-dark">Why enquire with us?</span>
                <div className="contact-trust-list" role="list" aria-label="Enquiry trust points">
                  {trustPoints.map((item) => (
                    <span className="contact-trust-item" key={item} role="listitem">
                      {item}
                    </span>
                  ))}
                </div>
              </div>

              <div className="contact-card-grid">
                {contactItems.map((item) => (
                  <article className="contact-card fade-up" key={item.label}>
                    <span className="contact-card__label">{item.label}</span>
                    {item.kind === "email" ? (
                      <a
                        className="contact-card__value contact-card__value--email"
                        href={item.href}
                      >
                        <span>travel@</span>
                        <wbr />
                        <span>letsgosouth.africa</span>
                      </a>
                    ) : item.href ? (
                      <a className="contact-card__value" href={item.href}>
                        {item.value}
                      </a>
                    ) : (
                      <p className="contact-card__value">{item.value}</p>
                    )}
                  </article>
                ))}
              </div>

              <div className="contact-panel fade-up">
                <h3>Prefer to browse first?</h3>
                <p>
                  Explore currently published trips, then come back with the
                  packages and destinations that interest you most.
                </p>
                <Link className="button" to="/packages">
                  Browse Packages
                </Link>
              </div>
            </div>

            <ContactForm />
          </div>
        </section>
      </div>
    </main>
  );
}
