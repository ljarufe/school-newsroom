(function () {
  "use strict";

  const valueOf = (id) => {
    const input = document.getElementById(id);
    return input ? input.value.trim() : "";
  };

  const setText = (root, selector, value) => {
    const element = root.querySelector(selector);
    if (element) {
      element.textContent = value;
    }
  };

  const setHidden = (root, selector, hidden) => {
    const element = root.querySelector(selector);
    if (element) {
      element.hidden = hidden;
    }
  };

  const initialiseTabPersistence = (root) => {
    const panel = root.closest('[role="tabpanel"]');
    const tabs = panel?.closest('[data-controller~="w-tabs"]');
    const form = root.closest("form");
    if (!panel || !tabs || !form) {
      return;
    }

    const storageKey = "news:seo-assistant:active-tab";
    const storageMaxAgeMs = 60 * 1000;
    const currentPath = window.location.pathname;
    const isCreatePage = currentPath.includes("/pages/add/");
    const isEditPage = /\/pages\/\d+\/edit\/?$/.test(currentPath);
    let pendingState = null;

    try {
      const rawState = window.sessionStorage.getItem(storageKey);
      window.sessionStorage.removeItem(storageKey);

      if (rawState) {
        const parsedState = JSON.parse(rawState);
        const ageMs = Date.now() - parsedState.savedAt;
        const samePath = parsedState.pathname === currentPath;
        const createToEditTransition =
          parsedState.wasCreatePage === true && isEditPage;

        if (
          parsedState.panelId === panel.id &&
          Number.isFinite(parsedState.savedAt) &&
          ageMs >= 0 &&
          ageMs <= storageMaxAgeMs &&
          (samePath || createToEditTransition)
        ) {
          pendingState = parsedState;
        }
      }
    } catch (_error) {
      pendingState = null;
    }

    const successfulSave = Boolean(
      document.querySelector(
        '.messages [data-w-messages-target="container"] > li.success',
      ),
    );
    const hasValidationErrors = Boolean(
      form.querySelector(
        '[aria-invalid="true"], .error-message, .w-field--error',
      ),
    );
    const panelHash = `#${panel.id}`;
    const anotherPanelWasRequested = Boolean(
      window.location.hash && window.location.hash !== panelHash,
    );

    if (
      pendingState &&
      successfulSave &&
      !hasValidationErrors &&
      !anotherPanelWasRequested
    ) {
      const trigger = tabs.querySelector(
        `[role="tab"][aria-controls="${panel.id}"]`,
      );

      if (trigger) {
        trigger.click();

        if (window.location.hash !== panelHash) {
          window.history.replaceState(window.history.state, "", panelHash);
        }
      }
    }

    form.addEventListener("submit", (event) => {
      const isDraftSave = event.submitter?.classList.contains("action-save");

      if (!isDraftSave || panel.hidden) {
        return;
      }

      try {
        window.sessionStorage.setItem(
          storageKey,
          JSON.stringify({
            panelId: panel.id,
            pathname: currentPath,
            wasCreatePage: isCreatePage,
            savedAt: Date.now(),
          }),
        );
      } catch (_error) {
        // The editor remains functional when session storage is unavailable.
      }
    });
  };

  const initialise = (root) => {
    initialiseTabPersistence(root);
    const watchedIds = [
      "id_title",
      "id_slug",
      "id_summary",
      "id_seo_title",
      "id_search_description",
      "id_og_title",
      "id_og_description",
      "id_canonical_url",
    ];

    const update = () => {
      const pageTitle = valueOf("id_title");
      const seoTitle = valueOf("id_seo_title");
      const summary = valueOf("id_summary");
      const description = valueOf("id_search_description");
      const ogTitle = valueOf("id_og_title");
      const ogDescription = valueOf("id_og_description");
      const canonical = valueOf("id_canonical_url");
      const slug = valueOf("id_slug");
      const effectiveTitle = seoTitle || pageTitle;
      const effectiveDescription = description || summary;
      const currentSlug = root.dataset.currentSlug;
      const servedPublicUrl = root.dataset.publicUrl;
      let previewUrl = canonical;
      if (!previewUrl && servedPublicUrl && currentSlug && slug) {
        const currentSuffix = `/${currentSlug}/`;
        previewUrl = servedPublicUrl.endsWith(currentSuffix)
          ? `${servedPublicUrl.slice(0, -currentSuffix.length)}/${slug}/`
          : servedPublicUrl;
      }
      if (!previewUrl) {
        previewUrl = slug ? `/${slug}/` : servedPublicUrl;
      }

      setText(root, "[data-seo-title-count]", seoTitle.length);
      setText(root, "[data-seo-description-count]", description.length);
      setText(root, "[data-seo-preview-title]", effectiveTitle);
      setText(root, "[data-seo-preview-description]", effectiveDescription);
      setText(root, "[data-seo-preview-url]", previewUrl);
      setText(root, "[data-seo-social-title]", ogTitle || effectiveTitle);
      setText(
        root,
        "[data-seo-social-description]",
        ogDescription || effectiveDescription,
      );
      setHidden(root, "[data-seo-title-fallback]", Boolean(seoTitle));
      setHidden(root, "[data-seo-description-fallback]", Boolean(description));
      setHidden(root, "[data-seo-og-title-fallback]", Boolean(ogTitle));
      setHidden(
        root,
        "[data-seo-og-description-fallback]",
        Boolean(ogDescription),
      );
    };

    watchedIds.forEach((id) => {
      const input = document.getElementById(id);
      if (input) {
        input.addEventListener("input", update);
        input.addEventListener("change", update);
      }
    });
    update();
  };

  const start = () => {
    document.querySelectorAll("[data-seo-assistant]").forEach(initialise);
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
