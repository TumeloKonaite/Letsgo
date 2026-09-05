// Format API prices, date ranges, and availability labels for South African display.

export function formatCurrency(amount, currency) {
  const numericAmount = Number(amount);

  if (Number.isNaN(numericAmount)) {
    return `${currency} ${amount}`;
  }

  return new Intl.NumberFormat("en-ZA", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(numericAmount);
}

export function formatDateRange(startDate, endDate) {
  const start = new Date(startDate);
  const end = new Date(endDate);

  const formatter = new Intl.DateTimeFormat("en-ZA", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });

  return `${formatter.format(start)} - ${formatter.format(end)}`;
}

export function formatAvailabilityStatus(status, spotsAvailable) {
  const normalizedStatus = String(status || "")
    .trim()
    .toLowerCase()
    .replace(/_/g, "-");

  if (normalizedStatus === "available" && spotsAvailable <= 3) {
    return {
      label: "Limited",
      tone: "limited",
    };
  }

  if (normalizedStatus === "sold-out") {
    return {
      label: "Sold out",
      tone: "sold-out",
    };
  }

  return {
    label: normalizedStatus || "Available",
    tone: normalizedStatus || "available",
  };
}
