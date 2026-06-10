import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";

import { ChatWidget } from "./chat/ChatWidget";
import { SiteFooter } from "./SiteFooter";

function ScrollManager() {
  const location = useLocation();

  useEffect(() => {
    if (location.hash) {
      const element = document.getElementById(location.hash.slice(1));
      if (element) {
        element.scrollIntoView({ behavior: "smooth", block: "start" });
        return;
      }
    }

    window.scrollTo({ top: 0, behavior: "smooth" });
  }, [location.pathname, location.hash]);

  return null;
}

export function Layout() {
  const location = useLocation();
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  useEffect(() => {
    setIsMenuOpen(false);
  }, [location.pathname, location.hash]);

  return (
    <div className="site-shell">
      <ScrollManager />
      <header className="site-header">
        <div className="site-header__inner">
          <NavLink className="brand" to="/">
            <img
              className="brand__logo"
              src="/images/branding/lets-go-logo.png"
              alt="Let's Go South Africa"
            />
          </NavLink>

          <button
            className="site-header__toggle"
            type="button"
            aria-expanded={isMenuOpen ? "true" : "false"}
            aria-controls="primary-navigation"
            onClick={() => setIsMenuOpen((currentState) => !currentState)}
          >
            <span />
            <span />
            <span />
            <span className="sr-only">Toggle navigation</span>
          </button>

          <div className={`site-header__panel${isMenuOpen ? " is-open" : ""}`}>
            <nav className="site-nav" id="primary-navigation" aria-label="Primary">
              <NavLink className="site-nav__link" to="/" end>
                Home
              </NavLink>
              <NavLink className="site-nav__link" to="/about">
                About Us
              </NavLink>
              <NavLink className="site-nav__link" to="/packages">
                Packages
              </NavLink>
              <NavLink className="site-nav__link" to="/contact">
                Contact Us
              </NavLink>
              <NavLink className="button site-nav__cta" to="/packages">
                Book a Tour
              </NavLink>
            </nav>
          </div>
        </div>
      </header>

      <Outlet />
      <SiteFooter />
      <ChatWidget />
    </div>
  );
}
