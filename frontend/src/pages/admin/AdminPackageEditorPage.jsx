// Coordinate package saves and staged image operations, retaining failed work for retry.

import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import {
  createPackage,
  deleteAdminPackageImage,
  getAdminPackage,
  getAdminPackageImages,
  uploadAdminPackageImage,
  updatePackage,
} from "../../api/adminPackagesApi";
import { useAuth } from "../../auth/AuthProvider";
import {
  createDefaultPackageValues,
  normalizePackageFormValues,
  PackageForm,
} from "../../components/admin/PackageForm";
import { StatusPanel } from "../../components/StatusPanel";

function createLocalImageId() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }

  return `queued-image-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function sortPackageImages(images) {
  return [...images].sort((leftImage, rightImage) => {
    if (leftImage.is_cover !== rightImage.is_cover) {
      return leftImage.is_cover ? -1 : 1;
    }

    if (leftImage.display_order !== rightImage.display_order) {
      return leftImage.display_order - rightImage.display_order;
    }

    return leftImage.id - rightImage.id;
  });
}

function buildImageActionErrorMessage(actionLabel, failedItems) {
  if (failedItems.length === 0) {
    return "";
  }

  const names = failedItems
    .map(({ name, error }) => {
      const detail = error?.message ? ` (${error.message})` : "";
      return `${name}${detail}`;
    })
    .join(", ");

  const pluralSuffix = failedItems.length === 1 ? "" : "s";
  return `${actionLabel} failed for ${failedItems.length} image${pluralSuffix}: ${names}`;
}

export function AdminPackageEditorPage() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const { packageId } = useParams();
  const routePackageId = packageId ? Number.parseInt(packageId, 10) : null;
  const previewUrlsRef = useRef(new Set());
  const queuedImagesRef = useRef([]);
  const [createdPackageId, setCreatedPackageId] = useState(null);
  const activePackageId = routePackageId ?? createdPackageId;
  const isCreateMode = activePackageId === null;
  const [initialValues, setInitialValues] = useState(() => createDefaultPackageValues());
  const [loading, setLoading] = useState(!isCreateMode);
  const [loadError, setLoadError] = useState("");
  const [saveError, setSaveError] = useState("");
  const [fieldErrors, setFieldErrors] = useState({});
  const [isSaving, setIsSaving] = useState(false);
  const [savePhase, setSavePhase] = useState("");
  const [persistedImages, setPersistedImages] = useState([]);
  const [queuedImages, setQueuedImages] = useState([]);
  const [removedImages, setRemovedImages] = useState([]);

  function revokeQueuedImagePreviews(imagesToRevoke) {
    imagesToRevoke.forEach((image) => {
      if (!previewUrlsRef.current.has(image.previewUrl)) {
        return;
      }

      URL.revokeObjectURL(image.previewUrl);
      previewUrlsRef.current.delete(image.previewUrl);
    });
  }

  useEffect(() => {
    queuedImagesRef.current = queuedImages;
  }, [queuedImages]);

  useEffect(() => {
    return () => {
      previewUrlsRef.current.forEach((previewUrl) => {
        URL.revokeObjectURL(previewUrl);
      });
      previewUrlsRef.current.clear();
    };
  }, []);

  useEffect(() => {
    if (!routePackageId) {
      setCreatedPackageId(null);
    }
  }, [routePackageId]);

  useEffect(() => {
    if (!routePackageId) {
      if (isCreateMode) {
        revokeQueuedImagePreviews(queuedImagesRef.current);
        setQueuedImages([]);
        setInitialValues(createDefaultPackageValues());
        setPersistedImages([]);
        setRemovedImages([]);
        setLoading(false);
        setLoadError("");
      }

      return;
    }

    let isMounted = true;

    async function loadPackage() {
      setLoading(true);
      setLoadError("");
      setSaveError("");
      setFieldErrors({});

      try {
        const [packagePayload, packageImagesPayload] = await Promise.all([
          getAdminPackage(routePackageId),
          getAdminPackageImages(routePackageId),
        ]);

        if (!isMounted) {
          return;
        }

        revokeQueuedImagePreviews(queuedImagesRef.current);
        setQueuedImages([]);
        setInitialValues(normalizePackageFormValues(packagePayload));
        setPersistedImages(sortPackageImages(packageImagesPayload));
        setRemovedImages([]);
      } catch (requestError) {
        if (!isMounted) {
          return;
        }

        setLoadError(requestError.message || "Could not load package.");
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    loadPackage();

    return () => {
      isMounted = false;
    };
  }, [isCreateMode, routePackageId]);

  function handleQueueImages(files) {
    const nextQueuedImages = Array.from(files || []).map((file) => {
      const previewUrl = URL.createObjectURL(file);
      previewUrlsRef.current.add(previewUrl);

      return {
        id: createLocalImageId(),
        file,
        name: file.name,
        previewUrl,
      };
    });

    if (nextQueuedImages.length === 0) {
      return;
    }

    setSaveError("");
    setQueuedImages((currentImages) => [...currentImages, ...nextQueuedImages]);
  }

  function handleRemoveQueuedImage(imageId) {
    setQueuedImages((currentImages) => {
      const imageToRemove = currentImages.find((image) => image.id === imageId);
      if (imageToRemove) {
        revokeQueuedImagePreviews([imageToRemove]);
      }

      return currentImages.filter((image) => image.id !== imageId);
    });
  }

  function handleRemovePersistedImage(imageId) {
    setRemovedImages((currentImages) => {
      if (currentImages.some((image) => image.id === imageId)) {
        return currentImages;
      }

      const imageToRemove = persistedImages.find((image) => image.id === imageId);
      if (!imageToRemove) {
        return currentImages;
      }

      return [...currentImages, imageToRemove];
    });
  }

  function handleRestorePersistedImage(imageId) {
    setRemovedImages((currentImages) =>
      currentImages.filter((image) => image.id !== imageId)
    );
  }

  async function uploadQueuedImages(packageRecordId) {
    const uploadedImages = [];
    const failedUploads = [];

    for (const queuedImage of queuedImages) {
      const formData = new FormData();
      formData.append("file", queuedImage.file);

      try {
        const uploadedImage = await uploadAdminPackageImage(packageRecordId, formData);
        uploadedImages.push(uploadedImage);
      } catch (requestError) {
        failedUploads.push({
          id: queuedImage.id,
          name: queuedImage.name,
          error: requestError,
        });
      }
    }

    if (uploadedImages.length > 0) {
      setPersistedImages((currentImages) =>
        sortPackageImages([...currentImages, ...uploadedImages])
      );
    }

    if (queuedImages.length > 0) {
      // Keep only failed uploads queued so a retry does not duplicate saved images.
      const failedUploadIds = new Set(failedUploads.map((item) => item.id));
      const successfulQueuedImages = queuedImages.filter(
        (image) => !failedUploadIds.has(image.id)
      );

      revokeQueuedImagePreviews(successfulQueuedImages);
      setQueuedImages((currentImages) =>
        currentImages.filter((image) => failedUploadIds.has(image.id))
      );
    }

    return failedUploads;
  }

  async function deleteRemovedImages(packageRecordId) {
    const failedDeletions = [];

    for (const image of removedImages) {
      try {
        await deleteAdminPackageImage(packageRecordId, image.id);
      } catch (requestError) {
        failedDeletions.push({
          id: image.id,
          name: image.alt_text || `Image ${image.id}`,
          error: requestError,
        });
      }
    }

    const failedDeletionIds = new Set(failedDeletions.map((item) => item.id));
    const succeededDeletionIds = removedImages
      .filter((image) => !failedDeletionIds.has(image.id))
      .map((image) => image.id);

    if (succeededDeletionIds.length > 0) {
      const succeededSet = new Set(succeededDeletionIds);
      setPersistedImages((currentImages) =>
        currentImages.filter((image) => !succeededSet.has(image.id))
      );
    }

    setRemovedImages((currentImages) =>
      currentImages.filter((image) => failedDeletionIds.has(image.id))
    );

    return failedDeletions;
  }

  async function handleSubmit(payload) {
    if (isSaving) {
      return;
    }

    setIsSaving(true);
    setSaveError("");
    setFieldErrors({});
    setSavePhase("saving");

    try {
      // Save first: image endpoints require a persisted package ID.
      let packageRecordId = activePackageId;

      if (isCreateMode) {
        const createdPackage = await createPackage(payload);
        packageRecordId = createdPackage.id;
        setCreatedPackageId(createdPackage.id);
        setInitialValues(normalizePackageFormValues(createdPackage));
      } else {
        const updatedPackage = await updatePackage(packageRecordId, payload);
        setInitialValues(normalizePackageFormValues(updatedPackage));
      }

      if (queuedImages.length > 0) {
        setSavePhase("uploading");
        const failedUploads = await uploadQueuedImages(packageRecordId);

        if (failedUploads.length > 0) {
          setSaveError(buildImageActionErrorMessage("Upload", failedUploads));
          return;
        }
      }

      if (removedImages.length > 0) {
        setSavePhase("removing");
        const failedDeletions = await deleteRemovedImages(packageRecordId);

        if (failedDeletions.length > 0) {
          setSaveError(buildImageActionErrorMessage("Removal", failedDeletions));
          return;
        }
      }

      navigate("/admin/packages", { replace: true });
    } catch (requestError) {
      setSaveError(requestError.message || "Could not save package.");
      setFieldErrors(requestError.fieldErrors || {});
    } finally {
      setSavePhase("");
      setIsSaving(false);
    }
  }

  const removedImageIds = new Set(removedImages.map((image) => image.id));
  const visiblePersistedImages = persistedImages.filter(
    (image) => !removedImageIds.has(image.id)
  );
  const submitNotice =
    savePhase === "uploading"
      ? `Uploading ${queuedImages.length} image${queuedImages.length === 1 ? "" : "s"}...`
      : savePhase === "removing"
        ? `Removing ${removedImages.length} image${removedImages.length === 1 ? "" : "s"}...`
        : isSaving
          ? "Saving package..."
          : "";

  return (
    <main className="page">
      <div className="container">
        <section className="page-hero fade-up">
          <div className="page-hero__panel admin-dashboard__hero">
            <span className="eyebrow-dark">Protected admin</span>
            <h1>{isCreateMode ? "Create package" : "Edit package"}</h1>
            <p>
              {isCreateMode
                ? "Create a new tourism package from the protected admin dashboard."
                : "Update an existing tourism package and save changes back to the protected admin API."}
            </p>

            <div className="hero__actions">
              <Link className="button-secondary" to="/admin/packages">
                Back to packages
              </Link>
              <button className="button-secondary" type="button" onClick={() => logout("/")}>
                Log out
              </button>
            </div>
          </div>
        </section>

        <section className="section">
          {loading ? (
            <StatusPanel
              title="Loading existing package..."
              message="Fetching package details from the protected admin API."
            />
          ) : null}

          {!loading && loadError ? (
            <StatusPanel
              title="Could not load package."
              message={loadError}
              tone="error"
              action={(
                <Link className="button-secondary" to="/admin/packages">
                  Back to packages
                </Link>
              )}
            />
          ) : null}

          {!loading && !loadError ? (
            <PackageForm
              initialValues={initialValues}
              onSubmit={handleSubmit}
              submitLabel={isCreateMode ? "Create package" : "Save changes"}
              isSaving={isSaving}
              submitNotice={submitNotice}
              submitError={saveError}
              externalFieldErrors={fieldErrors}
              packageImages={visiblePersistedImages}
              removedImages={removedImages}
              queuedImages={queuedImages}
              onSelectImages={handleQueueImages}
              onRemoveQueuedImage={handleRemoveQueuedImage}
              onRemovePersistedImage={handleRemovePersistedImage}
              onRestorePersistedImage={handleRestorePersistedImage}
              imageUploadHelpText={
                isCreateMode
                  ? "Selected images will upload to the backend when you save this package."
                  : "Selected images will upload to the backend when you save changes."
              }
            />
          ) : null}
        </section>
      </div>
    </main>
  );
}
