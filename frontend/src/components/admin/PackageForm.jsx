import { useEffect, useState } from "react";

import { StatusPanel } from "../StatusPanel";

const VALID_STATUSES = ["draft", "published", "archived"];

function createClientKey(prefix) {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return `${prefix}-${crypto.randomUUID()}`;
  }

  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function nextDisplayOrder(items) {
  if (items.length === 0) {
    return 0;
  }

  return Math.max(...items.map((item) => Number(item.display_order) || 0)) + 1;
}

function resequenceDisplayOrder(items) {
  return items.map((item, index) => ({
    ...item,
    display_order: String(index),
  }));
}

function createEmptyItineraryItem(order = 0) {
  return {
    client_key: createClientKey("itinerary"),
    id: null,
    title: "",
    description: "",
    duration: "",
    display_order: String(order),
  };
}

function createEmptyInclusionItem(type, order = 0) {
  return {
    client_key: createClientKey(type),
    id: null,
    name: "",
    type,
    display_order: String(order),
  };
}

function normalizeItineraryItems(items) {
  return (items ?? []).map((item, index) => ({
    client_key: createClientKey("itinerary"),
    id: item.id ?? null,
    title: item.title ?? "",
    description: item.description ?? "",
    duration: item.duration ?? "",
    display_order:
      item.display_order === null || item.display_order === undefined
        ? String(index)
        : String(item.display_order),
  }));
}

function normalizeInclusionItems(items, type) {
  return (items ?? []).map((item, index) => ({
    client_key: createClientKey(type),
    id: item.id ?? null,
    name: item.name ?? "",
    type,
    display_order:
      item.display_order === null || item.display_order === undefined
        ? String(index)
        : String(item.display_order),
  }));
}

export function createDefaultPackageValues() {
  return {
    title: "",
    slug: "",
    short_description: "",
    description: "",
    destination: "",
    duration_days: "",
    duration_nights: "",
    price_from: "",
    currency: "ZAR",
    itinerary: [],
    cost_includes: [],
    cost_excludes: [],
    is_active: true,
    status: "draft",
    is_published: false,
    is_featured: false,
    display_order: "0",
  };
}

export function normalizePackageFormValues(packageItem) {
  const defaults = createDefaultPackageValues();

  if (!packageItem) {
    return defaults;
  }

  const inclusions = Array.isArray(packageItem.inclusions) ? packageItem.inclusions : [];

  return {
    ...defaults,
    title: packageItem.title ?? "",
    slug: packageItem.slug ?? "",
    short_description: packageItem.short_description ?? "",
    description: packageItem.description ?? "",
    destination: packageItem.destination ?? "",
    duration_days:
      packageItem.duration_days === null || packageItem.duration_days === undefined
        ? ""
        : String(packageItem.duration_days),
    duration_nights:
      packageItem.duration_nights === null || packageItem.duration_nights === undefined
        ? ""
        : String(packageItem.duration_nights),
    price_from:
      packageItem.price_from === null || packageItem.price_from === undefined
        ? ""
        : String(packageItem.price_from),
    currency: packageItem.currency ?? defaults.currency,
    itinerary: normalizeItineraryItems(packageItem.itinerary),
    cost_includes: normalizeInclusionItems(
      inclusions.filter((item) => item.type === "included"),
      "included"
    ),
    cost_excludes: normalizeInclusionItems(
      inclusions.filter((item) => item.type === "excluded"),
      "excluded"
    ),
    is_active: Boolean(packageItem.is_active ?? defaults.is_active),
    status: packageItem.status ?? defaults.status,
    is_published: Boolean(packageItem.is_published ?? defaults.is_published),
    is_featured: Boolean(packageItem.is_featured ?? defaults.is_featured),
    display_order:
      packageItem.display_order === null || packageItem.display_order === undefined
        ? defaults.display_order
        : String(packageItem.display_order),
  };
}

function validateDisplayOrder(rawValue, label) {
  if (!String(rawValue ?? "").trim()) {
    return `${label} is required.`;
  }

  const value = Number(rawValue);
  if (!Number.isInteger(value)) {
    return `${label} must be a whole number.`;
  }

  if (value < 0) {
    return `${label} must be 0 or greater.`;
  }

  return "";
}

function validatePackageForm(values) {
  const errors = {};

  const requiredTextFields = [
    ["title", "Title", 200],
    ["slug", "Slug", 255],
    ["description", "Description"],
    ["destination", "Destination", 150],
  ];

  requiredTextFields.forEach(([fieldName, label, maxLength]) => {
    const value = String(values[fieldName] ?? "").trim();

    if (!value) {
      errors[fieldName] = `${label} is required.`;
      return;
    }

    if (maxLength && value.length > maxLength) {
      errors[fieldName] = `${label} must be ${maxLength} characters or fewer.`;
    }
  });

  const shortDescription = String(values.short_description ?? "").trim();
  if (shortDescription.length > 500) {
    errors.short_description = "Short description must be 500 characters or fewer.";
  }

  const currency = String(values.currency ?? "").trim().toUpperCase();
  if (!/^[A-Z]{3}$/.test(currency)) {
    errors.currency = "Currency must be a valid 3-letter code.";
  }

  const normalizedStatus = String(values.status ?? "").trim().toLowerCase();
  if (!VALID_STATUSES.includes(normalizedStatus)) {
    errors.status = "Status must be draft, published, or archived.";
  }

  const integerRules = [
    ["duration_days", "Duration days", 1],
    ["duration_nights", "Duration nights", 0],
    ["display_order", "Display order", 0],
  ];

  integerRules.forEach(([fieldName, label, minimum]) => {
    const rawValue = String(values[fieldName] ?? "").trim();

    if (!rawValue) {
      errors[fieldName] = `${label} is required.`;
      return;
    }

    const numberValue = Number(rawValue);
    if (!Number.isInteger(numberValue)) {
      errors[fieldName] = `${label} must be a whole number.`;
      return;
    }

    if (numberValue < minimum) {
      errors[fieldName] =
        minimum === 1
          ? `${label} must be greater than 0.`
          : `${label} must be ${minimum} or greater.`;
    }
  });

  const priceFrom = String(values.price_from ?? "").trim();
  if (!priceFrom) {
    errors.price_from = "Price from is required.";
  } else {
    const numberValue = Number(priceFrom);

    if (!Number.isFinite(numberValue)) {
      errors.price_from = "Price from must be a valid number.";
    } else if (numberValue < 0) {
      errors.price_from = "Price from must be 0 or greater.";
    }
  }

  const itineraryOrders = new Set();
  values.itinerary.forEach((item, index) => {
    const title = String(item.title ?? "").trim();
    const description = String(item.description ?? "").trim();
    const duration = String(item.duration ?? "").trim();
    const orderError = validateDisplayOrder(
      item.display_order,
      "Stop display order"
    );
    const orderValue = Number(item.display_order);

    if (!title) {
      errors[`itinerary.${index}.title`] = "Stop title is required.";
    } else if (title.length > 200) {
      errors[`itinerary.${index}.title`] =
        "Stop title must be 200 characters or fewer.";
    }

    if (!description) {
      errors[`itinerary.${index}.description`] = "Stop description is required.";
    }

    if (duration.length > 100) {
      errors[`itinerary.${index}.duration`] =
        "Stop duration must be 100 characters or fewer.";
    }

    if (orderError) {
      errors[`itinerary.${index}.display_order`] = orderError;
    } else if (itineraryOrders.has(orderValue)) {
      errors.itinerary =
        "Each itinerary stop must have a unique display order.";
    } else {
      itineraryOrders.add(orderValue);
    }
  });

  ["cost_includes", "cost_excludes"].forEach((fieldName) => {
    const orders = new Set();
    const itemLabel = fieldName === "cost_includes" ? "included" : "excluded";

    values[fieldName].forEach((item, index) => {
      const name = String(item.name ?? "").trim();
      const orderError = validateDisplayOrder(
        item.display_order,
        "Item display order"
      );
      const orderValue = Number(item.display_order);

      if (!name) {
        errors[`${fieldName}.${index}.name`] = "Item name is required.";
      } else if (name.length > 200) {
        errors[`${fieldName}.${index}.name`] =
          "Item name must be 200 characters or fewer.";
      }

      if (orderError) {
        errors[`${fieldName}.${index}.display_order`] = orderError;
      } else if (orders.has(orderValue)) {
        errors[fieldName] = `Each ${itemLabel} item must have a unique display order.`;
      } else {
        orders.add(orderValue);
      }
    });
  });

  return errors;
}

function buildPackagePayload(values) {
  const itinerary = [...values.itinerary]
    .map((item) => ({
      ...(Number.isInteger(item.id) ? { id: item.id } : {}),
      title: item.title.trim(),
      description: item.description.trim(),
      duration: item.duration.trim() || null,
      display_order: Number(item.display_order),
    }))
    .sort((leftItem, rightItem) => leftItem.display_order - rightItem.display_order);

  const inclusions = [...values.cost_includes, ...values.cost_excludes]
    .map((item) => ({
      ...(Number.isInteger(item.id) ? { id: item.id } : {}),
      name: item.name.trim(),
      type: item.type,
      display_order: Number(item.display_order),
    }))
    .sort((leftItem, rightItem) => {
      if (leftItem.type !== rightItem.type) {
        return leftItem.type.localeCompare(rightItem.type);
      }

      return leftItem.display_order - rightItem.display_order;
    });

  return {
    title: values.title.trim(),
    slug: values.slug.trim(),
    short_description: values.short_description.trim() || null,
    description: values.description.trim(),
    destination: values.destination.trim(),
    duration_days: Number(values.duration_days),
    duration_nights: Number(values.duration_nights),
    price_from: Number(values.price_from),
    currency: values.currency.trim().toUpperCase(),
    itinerary,
    inclusions,
    is_active: Boolean(values.is_active),
    status: values.status.trim().toLowerCase(),
    is_published: Boolean(values.is_published),
    is_featured: Boolean(values.is_featured),
    display_order: Number(values.display_order),
  };
}

function FieldError({ message }) {
  if (!message) {
    return null;
  }

  return <p className="package-form__field-error">{message}</p>;
}

function ImagePreviewTile({
  image,
  label,
  removeLabel,
  onRemove,
  isQueued = false,
  isPendingRemoval = false,
  onRestore,
}) {
  const previewUrl = isQueued ? image.previewUrl : image.url;
  const altText = image.alt_text || image.name || label;

  return (
    <article className={`package-image-card${isPendingRemoval ? " package-image-card--pending" : ""}`}>
      <div className="package-image-card__media">
        <img src={previewUrl} alt={altText} />
      </div>

      <div className="package-image-card__body">
        <div className="package-image-card__meta">
          <strong>{label}</strong>
          <span>{altText}</span>
        </div>

        {isPendingRemoval ? (
          <button
            className="button-secondary admin-action package-image-card__action"
            type="button"
            onClick={onRestore}
          >
            Restore
          </button>
        ) : (
          <button
            className="button-secondary admin-action admin-action--danger package-image-card__action"
            type="button"
            onClick={onRemove}
          >
            {removeLabel}
          </button>
        )}
      </div>
    </article>
  );
}

function ArrayEditorHeader({
  headingId,
  title,
  description,
  buttonLabel,
  onAdd,
  disabled,
}) {
  return (
    <div className="package-form__section-header">
      <div>
        <h2 id={headingId}>{title}</h2>
        <p>{description}</p>
      </div>
      <button
        className="button-secondary admin-action"
        type="button"
        onClick={onAdd}
        disabled={disabled}
      >
        {buttonLabel}
      </button>
    </div>
  );
}

function ItemCardActions({ onMoveUp, onMoveDown, onRemove, isFirst, isLast, disabled }) {
  return (
    <div className="package-form__item-actions">
      <button
        className="button-secondary admin-action"
        type="button"
        onClick={onMoveUp}
        disabled={disabled || isFirst}
      >
        Move up
      </button>
      <button
        className="button-secondary admin-action"
        type="button"
        onClick={onMoveDown}
        disabled={disabled || isLast}
      >
        Move down
      </button>
      <button
        className="button-secondary admin-action admin-action--danger"
        type="button"
        onClick={onRemove}
        disabled={disabled}
      >
        Delete
      </button>
    </div>
  );
}

function ItineraryEditor({
  items,
  fieldErrors,
  isSaving,
  onAdd,
  onChange,
  onMove,
  onRemove,
}) {
  return (
    <section className="package-form__section" aria-labelledby="package-itinerary-heading">
      <ArrayEditorHeader
        headingId="package-itinerary-heading"
        title="Itinerary"
        description="Add ordered tour stops with descriptions and optional stop durations."
        buttonLabel="Add itinerary stop"
        onAdd={onAdd}
        disabled={isSaving}
      />

      <FieldError message={fieldErrors.itinerary} />

      {items.length > 0 ? (
        <div className="package-form__item-list">
          {items.map((item, index) => (
            <article className="package-form__item-card" key={item.client_key}>
              <div className="package-form__item-card-header">
                <strong>Stop {index + 1}</strong>
                <span>Visible order: {item.display_order}</span>
              </div>

              <div className="package-form__grid">
                <label className="package-form__field package-form__field--full">
                  <span>Stop title</span>
                  <input
                    type="text"
                    value={item.title}
                    onChange={(event) => onChange(index, "title", event.target.value)}
                    maxLength={200}
                    aria-invalid={Boolean(fieldErrors[`itinerary.${index}.title`])}
                  />
                  <FieldError message={fieldErrors[`itinerary.${index}.title`]} />
                </label>

                <label className="package-form__field">
                  <span>Duration</span>
                  <input
                    type="text"
                    value={item.duration}
                    onChange={(event) => onChange(index, "duration", event.target.value)}
                    maxLength={100}
                    aria-invalid={Boolean(fieldErrors[`itinerary.${index}.duration`])}
                  />
                  <FieldError message={fieldErrors[`itinerary.${index}.duration`]} />
                </label>

                <label className="package-form__field">
                  <span>Display order</span>
                  <input
                    type="number"
                    min="0"
                    step="1"
                    value={item.display_order}
                    onChange={(event) =>
                      onChange(index, "display_order", event.target.value)
                    }
                    aria-invalid={Boolean(
                      fieldErrors[`itinerary.${index}.display_order`]
                    )}
                  />
                  <FieldError
                    message={fieldErrors[`itinerary.${index}.display_order`]}
                  />
                </label>

                <label className="package-form__field package-form__field--full">
                  <span>Description</span>
                  <textarea
                    value={item.description}
                    onChange={(event) =>
                      onChange(index, "description", event.target.value)
                    }
                    rows={4}
                    aria-invalid={Boolean(
                      fieldErrors[`itinerary.${index}.description`]
                    )}
                  />
                  <FieldError message={fieldErrors[`itinerary.${index}.description`]} />
                </label>
              </div>

              <ItemCardActions
                onMoveUp={() => onMove(index, -1)}
                onMoveDown={() => onMove(index, 1)}
                onRemove={() => onRemove(index)}
                isFirst={index === 0}
                isLast={index === items.length - 1}
                disabled={isSaving}
              />
            </article>
          ))}
        </div>
      ) : (
        <p className="package-form__section-empty">
          No itinerary stops added yet.
        </p>
      )}
    </section>
  );
}

function InclusionEditor({
  headingId,
  fieldName,
  title,
  description,
  items,
  fieldErrors,
  isSaving,
  onAdd,
  onChange,
  onMove,
  onRemove,
}) {
  return (
    <section className="package-form__section" aria-labelledby={headingId}>
      <ArrayEditorHeader
        headingId={headingId}
        title={title}
        description={description}
        buttonLabel={`Add ${title === "Cost Includes" ? "included" : "excluded"} item`}
        onAdd={onAdd}
        disabled={isSaving}
      />

      <FieldError message={fieldErrors[fieldName]} />

      {items.length > 0 ? (
        <div className="package-form__item-list">
          {items.map((item, index) => {
            return (
              <article className="package-form__item-card" key={item.client_key}>
                <div className="package-form__item-card-header">
                  <strong>{title === "Cost Includes" ? "Included" : "Excluded"} item {index + 1}</strong>
                  <span>Visible order: {item.display_order}</span>
                </div>

                <div className="package-form__grid">
                  <label className="package-form__field package-form__field--full">
                    <span>Item name</span>
                    <input
                      type="text"
                      value={item.name}
                      onChange={(event) => onChange(index, "name", event.target.value)}
                      maxLength={200}
                      aria-invalid={Boolean(fieldErrors[`${fieldName}.${index}.name`])}
                    />
                    <FieldError message={fieldErrors[`${fieldName}.${index}.name`]} />
                  </label>

                  <label className="package-form__field">
                    <span>Display order</span>
                    <input
                      type="number"
                      min="0"
                      step="1"
                      value={item.display_order}
                      onChange={(event) =>
                        onChange(index, "display_order", event.target.value)
                      }
                      aria-invalid={Boolean(
                        fieldErrors[`${fieldName}.${index}.display_order`]
                      )}
                    />
                    <FieldError
                      message={fieldErrors[`${fieldName}.${index}.display_order`]}
                    />
                  </label>
                </div>

                <ItemCardActions
                  onMoveUp={() => onMove(index, -1)}
                  onMoveDown={() => onMove(index, 1)}
                  onRemove={() => onRemove(index)}
                  isFirst={index === 0}
                  isLast={index === items.length - 1}
                  disabled={isSaving}
                />
              </article>
            );
          })}
        </div>
      ) : (
        <p className="package-form__section-empty">
          No items added yet.
        </p>
      )}
    </section>
  );
}

export function PackageForm({
  initialValues,
  onSubmit,
  submitLabel,
  isSaving = false,
  submitNotice = "",
  submitError = "",
  externalFieldErrors = {},
  packageImages = [],
  removedImages = [],
  queuedImages = [],
  onSelectImages,
  onRemoveQueuedImage,
  onRemovePersistedImage,
  onRestorePersistedImage,
  imageUploadHelpText = "",
}) {
  const [values, setValues] = useState(() => normalizePackageFormValues(initialValues));
  const [fieldErrors, setFieldErrors] = useState({});

  useEffect(() => {
    setValues(normalizePackageFormValues(initialValues));
    setFieldErrors({});
  }, [initialValues]);

  useEffect(() => {
    setFieldErrors(externalFieldErrors || {});
  }, [externalFieldErrors]);

  function clearFieldErrors(keys) {
    setFieldErrors((currentErrors) => {
      const nextErrors = { ...currentErrors };
      let changed = false;

      keys.forEach((key) => {
        if (key in nextErrors) {
          delete nextErrors[key];
          changed = true;
        }
      });

      return changed ? nextErrors : currentErrors;
    });
  }

  function handleImageSelection(event) {
    const files = event.target.files;
    if (files?.length && onSelectImages) {
      onSelectImages(files);
    }

    event.target.value = "";
  }

  function handleChange(event) {
    const { name, type, checked, value } = event.target;

    setValues((currentValues) => ({
      ...currentValues,
      [name]: type === "checkbox" ? checked : value,
    }));

    clearFieldErrors([name]);
  }

  function updateCollectionItem(fieldName, index, property, value) {
    setValues((currentValues) => ({
      ...currentValues,
      [fieldName]: currentValues[fieldName].map((item, itemIndex) =>
        itemIndex === index ? { ...item, [property]: value } : item
      ),
    }));

    clearFieldErrors([`${fieldName}.${index}.${property}`, fieldName]);
  }

  function addCollectionItem(fieldName, nextItem) {
    setValues((currentValues) => ({
      ...currentValues,
      [fieldName]: [...currentValues[fieldName], nextItem],
    }));
    clearFieldErrors([fieldName]);
  }

  function removeCollectionItem(fieldName, index) {
    setValues((currentValues) => ({
      ...currentValues,
      [fieldName]: resequenceDisplayOrder(
        currentValues[fieldName].filter((_, itemIndex) => itemIndex !== index)
      ),
    }));
    clearFieldErrors([fieldName]);
  }

  function moveCollectionItem(fieldName, index, direction) {
    setValues((currentValues) => {
      const nextIndex = index + direction;
      const items = [...currentValues[fieldName]];

      if (nextIndex < 0 || nextIndex >= items.length) {
        return currentValues;
      }

      [items[index], items[nextIndex]] = [items[nextIndex], items[index]];

      return {
        ...currentValues,
        [fieldName]: resequenceDisplayOrder(items),
      };
    });
    clearFieldErrors([fieldName]);
  }

  async function handleSubmit(event) {
    event.preventDefault();

    if (isSaving) {
      return;
    }

    const nextErrors = validatePackageForm(values);
    setFieldErrors(nextErrors);

    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    await onSubmit(buildPackagePayload(values));
  }

  return (
    <form className="package-form fade-up" onSubmit={handleSubmit} noValidate>
      {submitError ? (
        <StatusPanel
          title="Could not save package."
          message={submitError}
          tone="error"
        />
      ) : null}

      {submitNotice ? (
        <div className="package-form__notice" role="status">
          {submitNotice}
        </div>
      ) : null}

      <section className="package-form__section" aria-labelledby="package-basic-heading">
        <div className="package-form__section-header">
          <div>
            <h2 id="package-basic-heading">Basic Information</h2>
            <p>Set the core package details shown across admin and public surfaces.</p>
          </div>
        </div>

        <div className="package-form__grid">
          <label className="package-form__field package-form__field--full" htmlFor="title">
            <span>Title</span>
            <input
              id="title"
              name="title"
              type="text"
              value={values.title}
              onChange={handleChange}
              maxLength={200}
              aria-invalid={Boolean(fieldErrors.title)}
            />
            <FieldError message={fieldErrors.title} />
          </label>

          <label className="package-form__field package-form__field--full" htmlFor="slug">
            <span>Slug</span>
            <input
              id="slug"
              name="slug"
              type="text"
              value={values.slug}
              onChange={handleChange}
              maxLength={255}
              aria-invalid={Boolean(fieldErrors.slug)}
            />
            <FieldError message={fieldErrors.slug} />
          </label>

          <label className="package-form__field package-form__field--full" htmlFor="short_description">
            <span>Short description</span>
            <textarea
              id="short_description"
              name="short_description"
              value={values.short_description}
              onChange={handleChange}
              maxLength={500}
              rows={3}
              aria-invalid={Boolean(fieldErrors.short_description)}
            />
            <FieldError message={fieldErrors.short_description} />
          </label>

          <label className="package-form__field package-form__field--full" htmlFor="description">
            <span>Description</span>
            <textarea
              id="description"
              name="description"
              value={values.description}
              onChange={handleChange}
              rows={8}
              aria-invalid={Boolean(fieldErrors.description)}
            />
            <FieldError message={fieldErrors.description} />
          </label>

          <label className="package-form__field" htmlFor="destination">
            <span>Destination</span>
            <input
              id="destination"
              name="destination"
              type="text"
              value={values.destination}
              onChange={handleChange}
              maxLength={150}
              aria-invalid={Boolean(fieldErrors.destination)}
            />
            <FieldError message={fieldErrors.destination} />
          </label>

          <label className="package-form__field" htmlFor="currency">
            <span>Currency</span>
            <input
              id="currency"
              name="currency"
              type="text"
              value={values.currency}
              onChange={handleChange}
              maxLength={3}
              aria-invalid={Boolean(fieldErrors.currency)}
            />
            <FieldError message={fieldErrors.currency} />
          </label>

          <label className="package-form__field" htmlFor="duration_days">
            <span>Duration days</span>
            <input
              id="duration_days"
              name="duration_days"
              type="number"
              min="1"
              step="1"
              value={values.duration_days}
              onChange={handleChange}
              aria-invalid={Boolean(fieldErrors.duration_days)}
            />
            <FieldError message={fieldErrors.duration_days} />
          </label>

          <label className="package-form__field" htmlFor="duration_nights">
            <span>Duration nights</span>
            <input
              id="duration_nights"
              name="duration_nights"
              type="number"
              min="0"
              step="1"
              value={values.duration_nights}
              onChange={handleChange}
              aria-invalid={Boolean(fieldErrors.duration_nights)}
            />
            <FieldError message={fieldErrors.duration_nights} />
          </label>

          <label className="package-form__field" htmlFor="price_from">
            <span>Price from</span>
            <input
              id="price_from"
              name="price_from"
              type="number"
              min="0"
              step="0.01"
              value={values.price_from}
              onChange={handleChange}
              aria-invalid={Boolean(fieldErrors.price_from)}
            />
            <FieldError message={fieldErrors.price_from} />
          </label>

          <label className="package-form__field" htmlFor="display_order">
            <span>Display order</span>
            <input
              id="display_order"
              name="display_order"
              type="number"
              min="0"
              step="1"
              value={values.display_order}
              onChange={handleChange}
              aria-invalid={Boolean(fieldErrors.display_order)}
            />
            <FieldError message={fieldErrors.display_order} />
          </label>
        </div>
      </section>

      <section className="package-form__section" aria-labelledby="package-images-heading">
        <div className="package-form__images-header">
          <div>
            <h2 id="package-images-heading">Images</h2>
            <p>Upload one or more package images through the protected backend endpoint.</p>
          </div>
        </div>

        <label className="package-form__upload" htmlFor="package-images-upload">
          <span>Add images</span>
          <input
            id="package-images-upload"
            type="file"
            accept="image/jpeg,image/png,image/webp"
            multiple
            onChange={handleImageSelection}
            disabled={isSaving}
          />
        </label>

        {imageUploadHelpText ? (
          <p className="package-form__images-help">{imageUploadHelpText}</p>
        ) : null}

        {packageImages.length > 0 ? (
          <div className="package-image-grid">
            {packageImages.map((image) => (
              <ImagePreviewTile
                key={image.id}
                image={image}
                label={image.is_cover ? "Cover image" : `Uploaded image #${image.display_order + 1}`}
                removeLabel="Remove"
                onRemove={() => onRemovePersistedImage?.(image.id)}
              />
            ))}
          </div>
        ) : (
          <p className="package-form__images-empty">
            No uploaded images are attached to this package yet.
          </p>
        )}

        {queuedImages.length > 0 ? (
          <>
            <div className="package-form__images-subheading">Queued for upload</div>
            <div className="package-image-grid">
              {queuedImages.map((image) => (
                <ImagePreviewTile
                  key={image.id}
                  image={image}
                  label={image.name}
                  removeLabel="Remove"
                  onRemove={() => onRemoveQueuedImage?.(image.id)}
                  isQueued
                />
              ))}
            </div>
          </>
        ) : null}

        {removedImages.length > 0 ? (
          <>
            <div className="package-form__images-subheading">Pending removal</div>
            <p className="package-form__images-help">
              These images will be removed from the package when you save.
            </p>
            <div className="package-image-grid">
              {removedImages.map((image) => (
                <ImagePreviewTile
                  key={image.id}
                  image={image}
                  label={image.is_cover ? "Cover image" : `Uploaded image #${image.display_order + 1}`}
                  removeLabel="Remove"
                  onRemove={() => onRemovePersistedImage?.(image.id)}
                  isPendingRemoval
                  onRestore={() => onRestorePersistedImage?.(image.id)}
                />
              ))}
            </div>
          </>
        ) : null}
      </section>

      <ItineraryEditor
        items={values.itinerary}
        fieldErrors={fieldErrors}
        isSaving={isSaving}
        onAdd={() =>
          addCollectionItem(
            "itinerary",
            createEmptyItineraryItem(nextDisplayOrder(values.itinerary))
          )
        }
        onChange={(index, property, value) =>
          updateCollectionItem("itinerary", index, property, value)
        }
        onMove={(index, direction) =>
          moveCollectionItem("itinerary", index, direction)
        }
        onRemove={(index) => removeCollectionItem("itinerary", index)}
      />

      <InclusionEditor
        headingId="package-includes-heading"
        fieldName="cost_includes"
        title="Cost Includes"
        description="Add everything the package price covers."
        items={values.cost_includes}
        fieldErrors={fieldErrors}
        isSaving={isSaving}
        onAdd={() =>
          addCollectionItem(
            "cost_includes",
            createEmptyInclusionItem("included", nextDisplayOrder(values.cost_includes))
          )
        }
        onChange={(index, property, value) =>
          updateCollectionItem("cost_includes", index, property, value)
        }
        onMove={(index, direction) =>
          moveCollectionItem("cost_includes", index, direction)
        }
        onRemove={(index) => removeCollectionItem("cost_includes", index)}
      />

      <InclusionEditor
        headingId="package-excludes-heading"
        fieldName="cost_excludes"
        title="Cost Excludes"
        description="Add everything guests should budget for separately."
        items={values.cost_excludes}
        fieldErrors={fieldErrors}
        isSaving={isSaving}
        onAdd={() =>
          addCollectionItem(
            "cost_excludes",
            createEmptyInclusionItem("excluded", nextDisplayOrder(values.cost_excludes))
          )
        }
        onChange={(index, property, value) =>
          updateCollectionItem("cost_excludes", index, property, value)
        }
        onMove={(index, direction) =>
          moveCollectionItem("cost_excludes", index, direction)
        }
        onRemove={(index) => removeCollectionItem("cost_excludes", index)}
      />

      <section className="package-form__section" aria-labelledby="package-status-heading">
        <div className="package-form__section-header">
          <div>
            <h2 id="package-status-heading">Status</h2>
            <p>Control draft state, visibility, and featured placement.</p>
          </div>
        </div>

        <div className="package-form__grid">
          <label className="package-form__field package-form__field--full" htmlFor="status">
            <span>Status</span>
            <select
              id="status"
              name="status"
              value={values.status}
              onChange={handleChange}
              aria-invalid={Boolean(fieldErrors.status)}
            >
              <option value="draft">Draft</option>
              <option value="published">Published</option>
              <option value="archived">Archived</option>
            </select>
            <FieldError message={fieldErrors.status} />
          </label>
        </div>

        <div className="package-form__toggles">
          <label className="package-form__toggle" htmlFor="is_active">
            <input
              id="is_active"
              name="is_active"
              type="checkbox"
              checked={values.is_active}
              onChange={handleChange}
            />
            <span>Active package</span>
          </label>

          <label className="package-form__toggle" htmlFor="is_published">
            <input
              id="is_published"
              name="is_published"
              type="checkbox"
              checked={values.is_published}
              onChange={handleChange}
            />
            <span>Published</span>
          </label>

          <label className="package-form__toggle" htmlFor="is_featured">
            <input
              id="is_featured"
              name="is_featured"
              type="checkbox"
              checked={values.is_featured}
              onChange={handleChange}
            />
            <span>Featured package</span>
          </label>
        </div>
      </section>

      <div className="hero__actions">
        <button className="button" type="submit" disabled={isSaving}>
          {isSaving ? "Saving..." : submitLabel}
        </button>
      </div>
    </form>
  );
}
