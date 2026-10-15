import { Navigate } from "react-router-dom";

import { StatusPanel } from "../components/StatusPanel.jsx";
import { useBooking } from "./BookingContext.jsx";
import { hasBookingSelection } from "./bookingDraft.js";

export function BookingDetailsPage() {
  const { draft } = useBooking();

  if (!hasBookingSelection(draft)) {
    return <Navigate to="/packages" replace />;
  }

  return (
    <main className="page">
      <div className="container">
        <StatusPanel
          title="Booking details"
          message="Your selected package and departure are ready. The booking form will be added next."
          tone="idle"
        />
      </div>
    </main>
  );
}
