import { useEffect, useState } from "react";

import { StatusPanel } from "../StatusPanel";

const VALID_STATUSES = ["draft", "published", "archived"];

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
    ["duration_days", "Duration days", { minimum: 1 }],
    ["duration_nights", "Duration nights", { minimum: 0 }],
    ["display_order", "Display order", { minimum: 0 }],
  ];

  integerRules.forEach(([fieldName, label, config]) => {
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

    if (numberValue < config.minimum) {
      errors[fieldName] =
        config.minimum === 1
          ? `${label} must be greater than 0.`
          : `${label} must be ${config.minimum} or greater.`;
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

  return errors;
}

function buildPackagePayload(values) {
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

    setFieldErrors((currentErrors) => {
      if (!(name in currentErrors)) {
        return currentErrors;
      }

      const nextErrors = { ...currentErrors };
      delete nextErrors[name];
      return nextErrors;
    });
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

      <section className="package-form__images" aria-labelledby="package-images-heading">
        <div className="package-form__images-header">
          <div>
            <h2 id="package-images-heading">Package images</h2>
            <p>
              Upload one or more package images through the protected backend endpoint.
            </p>
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

      <div className="hero__actions">
        <button className="button" type="submit" disabled={isSaving}>
          {isSaving ? "Saving..." : submitLabel}
        </button>
      </div>
    </form>
  );
}
