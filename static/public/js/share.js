(() => {
  "use strict";

  const messages = {
    copied: "Enlace copiado.",
    manual: "No se pudo copiar automáticamente. Selecciona y copia este enlace.",
    nativeCopied: "No se pudo abrir el menú para compartir. Enlace copiado.",
    nativeManual:
      "No se pudo abrir el menú para compartir. Selecciona y copia este enlace.",
  };
  const successDuration = 5000;

  const errorName = (error) =>
    error && typeof error.name === "string" ? error.name : "Error";

  document.querySelectorAll("[data-public-share]").forEach((component) => {
    const nativeButton = component.querySelector(
      '[data-share-channel="native"]',
    );
    const copyButton = component.querySelector('[data-share-channel="copy"]');
    const notification = component.querySelector("[data-share-notification]");
    const closeButton = component.querySelector("[data-share-close]");
    const manualFallback = component.querySelector(
      "[data-share-manual-fallback]",
    );
    const manualUrl = component.querySelector("[data-share-manual-url]");
    const status = component.querySelector("[data-share-status]");

    if (
      !nativeButton ||
      !copyButton ||
      !notification ||
      !closeButton ||
      !manualFallback ||
      !manualUrl ||
      !status
    ) {
      return;
    }

    const canonicalUrl = component.dataset.shareUrl || "";
    const payload = {
      title: component.dataset.shareTitle || "",
      url: canonicalUrl,
    };
    const description = component.dataset.shareDescription || "";
    if (description) {
      payload.text = description;
    }

    let notificationTimeout = null;
    let notificationVersion = 0;

    const resetManualFallback = () => {
      manualFallback.hidden = true;
      manualUrl.value = canonicalUrl;
      try {
        manualUrl.setSelectionRange(0, 0);
      } catch (_error) {
        // The readonly value still resets even if selection is unsupported.
      }
    };

    const hideNotification = () => {
      notificationVersion += 1;
      if (notificationTimeout !== null) {
        window.clearTimeout(notificationTimeout);
        notificationTimeout = null;
      }
      notification.hidden = true;
      status.textContent = "";
      resetManualFallback();
    };

    const showNotification = (message, { manual = false, autoDismiss = false }) => {
      hideNotification();
      status.textContent = message;
      notification.hidden = false;
      const currentVersion = notificationVersion;

      if (manual) {
        manualFallback.hidden = false;
        manualUrl.focus();
        try {
          manualUrl.select();
        } catch (_error) {
          // Focus still leaves the readonly canonical available for manual copying.
        }
      }

      if (autoDismiss) {
        notificationTimeout = window.setTimeout(() => {
          if (notificationVersion === currentVersion) {
            hideNotification();
          }
        }, successDuration);
      }
    };

    const writeCanonical = async () => {
      try {
        if (
          !navigator.clipboard ||
          typeof navigator.clipboard.writeText !== "function"
        ) {
          const unavailableError = new Error("Clipboard API unavailable");
          unavailableError.name = "NotSupportedError";
          throw unavailableError;
        }
        await navigator.clipboard.writeText(canonicalUrl);
        return true;
      } catch (error) {
        console.warn("public-share:clipboard-failed", errorName(error));
        return false;
      }
    };

    const activateCopy = async () => {
      hideNotification();
      if (await writeCanonical()) {
        showNotification(messages.copied, { autoDismiss: true });
      } else {
        showNotification(messages.manual, { manual: true });
      }
    };

    const activateNativeShare = async () => {
      hideNotification();
      try {
        await navigator.share(payload);
      } catch (error) {
        if (errorName(error) === "AbortError") {
          return;
        }
        console.warn("public-share:native-failed", errorName(error));
        if (await writeCanonical()) {
          showNotification(messages.nativeCopied, { autoDismiss: true });
        } else {
          showNotification(messages.nativeManual, { manual: true });
        }
      }
    };

    let nativeSupported = typeof navigator.share === "function";
    if (nativeSupported && typeof navigator.canShare === "function") {
      try {
        nativeSupported = navigator.canShare(payload);
      } catch (_error) {
        nativeSupported = false;
      }
    }

    if (nativeSupported) {
      nativeButton.hidden = false;
      nativeButton.addEventListener("click", () => {
        void activateNativeShare();
      });
    } else {
      nativeButton.remove();
    }

    copyButton.hidden = false;
    copyButton.addEventListener("click", () => {
      void activateCopy();
    });
    closeButton.addEventListener("click", hideNotification);
  });
})();
