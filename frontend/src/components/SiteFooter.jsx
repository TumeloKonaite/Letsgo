import { Link } from "react-router-dom";

import { useAuth } from "../auth/AuthProvider";
import { contactDetails } from "../data/about";

export function SiteFooter() {
  const { isAuthenticated, logout } = useAuth();

  return (
    <footer className="footer">
      <div className="container footer-grid">
        <div className="footer-grid__intro fade-up">
          <h3>LET&apos;S GO SOUTH AFRICA</h3>
          <p className="footer-copy">
            Warm, practical travel planning for visitors who want to experience
            South Africa through safari, culture, scenery, and local knowledge.
          </p>
          <div className="footer-actions">
            <Link className="button" to="/packages">
              Browse Packages
            </Link>
            <Link className="footer-admin-link" to="/contact">
              Send Enquiry
            </Link>
          </div>
        </div>

        <div className="fade-up">
          <h4>Explore</h4>
          <div className="footer-links">
            <Link to="/packages">Packages</Link>
            <Link to="/packages">Safari Tours</Link>
            <Link to="/packages">Cultural Experiences</Link>
            <Link to="/packages">Airport Transfers</Link>
            <Link to="/packages">Destination Guides</Link>
          </div>
        </div>

        <div className="fade-up">
          <h4>Company</h4>
          <div className="footer-links">
            <Link to="/about">About Us</Link>
            <Link to="/contact">Contact Us</Link>
            <Link to="/contact">Travel Enquiry</Link>
            <Link to={isAuthenticated ? "/admin/dashboard" : "/admin/login"}>
              {isAuthenticated ? "Admin dashboard" : "Admin login"}
            </Link>
          </div>
        </div>

        <div className="fade-up">
          <h4>Contact</h4>
          <div className="footer-links">
            <a href={`tel:${contactDetails.phone.replace(/\s+/g, "")}`}>
              {contactDetails.phone}
            </a>
            <a href={`mailto:${contactDetails.email}`}>{contactDetails.email}</a>
            <span>{contactDetails.address}</span>
            <span>{contactDetails.officeHours}</span>
            {isAuthenticated ? (
              <div className="footer-utility">
                <button
                  className="footer-admin-link footer-admin-link--button"
                  type="button"
                  onClick={() => logout("/")}
                >
                  Log out
                </button>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </footer>
  );
}
