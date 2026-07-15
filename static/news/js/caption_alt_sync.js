(function () {
  "use strict";

  window.schoolNewsroom = window.schoolNewsroom || {};
  window.schoolNewsroom.images = window.schoolNewsroom.images || {};

  const setupCaptionAltSync = (captionInput, altInput) => {
    if (!captionInput || !altInput || altInput.dataset.captionSyncInitialized) {
      return;
    }

    altInput.dataset.captionSyncInitialized = "true";

    let syncing = false;
    let isSynchronizable =
      altInput.value.trim() === "" || altInput.value === captionInput.value;

    if (isSynchronizable && altInput.value !== captionInput.value) {
      syncing = true;
      altInput.value = captionInput.value;
      altInput.dispatchEvent(new Event("input", { bubbles: true }));
      syncing = false;
    }

    captionInput.addEventListener("input", () => {
      if (!isSynchronizable) {
        return;
      }
      syncing = true;
      altInput.value = captionInput.value;
      altInput.dispatchEvent(new Event("input", { bubbles: true }));
      syncing = false;
    });

    altInput.addEventListener("input", () => {
      if (!syncing) {
        isSynchronizable = false;
      }
    });
  };

  window.schoolNewsroom.images.setupCaptionAltSync = setupCaptionAltSync;

  const initialiseNewsPageImageMetadata = () => {
    [
      ["id_featured_image_caption", "id_featured_image_alt_text"],
      ["id_og_image_caption", "id_og_image_alt_text"],
    ].forEach(([captionId, altId]) => {
      setupCaptionAltSync(
        document.getElementById(captionId),
        document.getElementById(altId),
      );
    });
  };

  if (document.readyState === "loading") {
    document.addEventListener(
      "DOMContentLoaded",
      initialiseNewsPageImageMetadata,
    );
  } else {
    initialiseNewsPageImageMetadata();
  }
})();
