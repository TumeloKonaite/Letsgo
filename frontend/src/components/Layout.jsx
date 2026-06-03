import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useEffect } from "react";

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
  return (
    <div className="site-shell">
      <ScrollManager />
      <header className="site-header">
        <div className="site-header__inner">
          <NavLink className="brand" to="/">
            <span className="brand__mark">
              LET'S <span className="brand__accent">GO!</span>
            </span>
            <span className="brand__sub">South Africa</span>
          </NavLink>

          <nav className="site-nav" aria-label="Primary">
            <NavLink className="site-nav__link" to="/">
              Home
            </NavLink>
            <a className="site-nav__link" href="/#about">
              About Us
            </a>
            <NavLink className="site-nav__link" to="/packages">
              Packages
            </NavLink>
            <a className="site-nav__link" href="/#contact">
              Contact
            </a>
            <NavLink className="button" to="/packages">
              Book a Tour
            </NavLink>
          </nav>
        </div>
      </header>

      <Outlet />
    </div>
  );
}
