# Public package-booking contract

Status: **agreed for the first release**  
Last updated: 2026-10-15

This document is the product and API contract for visitor-facing package booking.
Implementation must follow it unless a replacement decision is recorded here first.

## Product rules

The visitor journey is:

```text
Package page -> select an available departure -> choose number of people
-> enter contact details -> review -> submit booking request
-> booking created as new -> admin contacts and confirms the customer
```

- A booking is a request, not an instantly confirmed purchase.
- Visitors do not need to sign in.
- Every new public booking has status `new`.
- Calls to action use **“Submit booking request”**. They must not say “Book now” or
  “Pay now”.
- The first release records one `number_of_people` value. Adult and child counts
  are not collected separately.
- `price_from` is indicative only. It is not multiplied by party size, used to
  calculate a total, or presented as a promised final price.
- No final payable total is shown in this flow.
- Online payment and automatic confirmation are not part of this release.
- The visitor selects an existing `package_availability` record. The system does
  not create or calculate appointment-style time slots.

## Public endpoint

### Create a booking request

```http
POST /api/bookings
Content-Type: application/json

{
  "package_id": 12,
  "availability_id": 42,
  "customer_name": "Amina Dlamini",
  "customer_email": "amina@example.com",
  "customer_phone": "+27 82 555 0100",
  "number_of_people": 3,
  "special_requests": "Vegetarian meals, please."
}
```

The request accepts only identifiers and visitor-entered booking information.
Package title, dates, price, currency, capacity, remaining places, publication
state, and availability status are server-owned. If the browser sends any such
values, they are not trusted or used. Unknown request fields are rejected.

### Request validation

- `package_id` and `availability_id` are required positive integers.
- `customer_name` is required, trimmed, non-blank, and at most 255 characters.
- `customer_email` is required, trimmed, syntactically valid, and at most 320
  characters. Email ownership verification is not part of this release.
- `customer_phone` is required, trimmed, 5 to 50 characters, and non-blank. The
  first release does not require one country's phone-number format.
- `number_of_people` is a required positive integer no greater than 100. A
  request within that limit but larger than the remaining places is a capacity
  conflict.
- `special_requests` is optional. When supplied it is trimmed, converted to
  `null` if blank, and limited to 2,000 characters.
- The availability must belong to `package_id`.

Malformed JSON, wrong JSON types, missing fields, unknown fields, and field-level
validation failures return `422 Unprocessable Entity` using FastAPI's validation
error shape.

### Success

Return `201 Created` with the server-created booking:

```json
{
  "id": 123,
  "package_id": 12,
  "package_title": "Example Package",
  "availability_id": 42,
  "customer_name": "Amina Dlamini",
  "customer_email": "amina@example.com",
  "customer_phone": "+27 82 555 0100",
  "number_of_people": 3,
  "special_requests": "Vegetarian meals, please.",
  "status": "new",
  "created_at": "2026-10-15T10:00:00Z",
  "updated_at": "2026-10-15T10:00:00Z"
}
```

For this endpoint, `availability_id` is always an integer even though legacy or
administratively created bookings may have no availability.

## Domain validation and errors

The server reloads the package and availability from the database using the two
IDs. Validation is applied in this order so one request has a predictable result:

1. Validate the request shape and fields (`422`).
2. Load the package. A missing, inactive, unpublished, or non-published package
   returns `404 Not Found`.
3. Load the availability. A missing availability returns `404 Not Found`.
4. Verify the availability belongs to the selected package. A mismatch returns
   `422 Unprocessable Entity`.
5. Recheck that the departure can accept the request. A cancelled, closed,
   expired, or sold-out departure, or one without enough remaining places,
   returns `409 Conflict`.

For this contract, a departure is expired when its `start_date` is earlier than
the server's current business date. A departure is bookable only when its status
is `available`, it is not expired, and `spots_available` is at least
`number_of_people`. Reaching exactly zero remaining places changes its status to
`sold_out` as part of the reservation transaction.

Error bodies use FastAPI's `detail` field. Capacity conflicts use this stable,
customer-safe response:

```json
{
  "detail": "This departure no longer has enough available places."
}
```

Closed, cancelled, expired, or already sold-out departures may use a more
specific customer-safe `detail`, but clients must branch on the `409` status and
must not depend on that prose. Internal publication or capacity details must not
be exposed by a `404` response.

## Capacity reservation

Capacity is reserved only when the booking request is successfully created. The
server must perform all of the following in one database transaction:

1. Lock the selected availability row, or perform an equivalent conditional
   atomic update.
2. Reload and validate package/departure eligibility and remaining capacity.
3. Decrement `spots_available` by `number_of_people`.
4. Set the availability to `sold_out` if no places remain.
5. Insert the booking with `status = new`, `package_id`, and `availability_id`.
6. Commit, then return `201`.

Any failure rolls back both the capacity change and booking insert. Browser data
may be stale, so preflight checks and UI disabling never replace the transactional
server check. Concurrent requests must not oversubscribe a departure; this must
be integration-tested against PostgreSQL.

## Cancellation inventory rule

When a capacity-reserving booking makes its first valid transition from any
non-cancelled status to `cancelled`, restore its `number_of_people` to the linked
availability in the same database transaction as the status change.

The transition must lock the booking and availability (or provide equivalent
atomicity), and set:

```text
spots_available = min(capacity, spots_available + number_of_people)
```

Restoration happens once only. Updating an already-cancelled booking does not
restore capacity again. `cancelled` is terminal, so transitions away from it are
invalid. All other status changes leave capacity unchanged. A booking must not be
hard-deleted as a substitute for cancellation; deletion does not define an
inventory adjustment in this contract.

If restoration would exceed configured capacity, cap the value at `capacity` and
record the invariant violation for operational investigation. Do not fail after
partially updating either record.

## Out of scope

- Online payment.
- Final price calculation.
- Adult, child, supplement, discount, or tax calculations.
- Automatically confirming bookings.
- Calculated appointment-style time slots.
- Email delivery, rate limiting, and anti-spam controls; these will be handled
  separately.

## Implementation acceptance criteria

- The endpoint accepts the documented payload and returns the documented `201`
  response with status `new`.
- Anonymous visitors can submit a request.
- Validation and domain failures return the documented HTTP status codes.
- Package/departure facts are reloaded and never trusted from the browser.
- Capacity validation, decrement, and booking insertion are atomic.
- Concurrent requests cannot oversubscribe a departure.
- First cancellation restores reserved places once without exceeding capacity.
- Other status changes do not alter capacity.
- Visitor copy says “Submit booking request” and describes pricing as indicative;
  it shows no final payable total.

