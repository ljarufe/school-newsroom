(function () {
  "use strict";

  const blockTypeInput = (block) =>
    block.querySelector(':scope input[type="hidden"][name$="-type"]');

  const isDeletedBlock = (block) => {
    const deletedInput = block.querySelector(
      ':scope input[type="hidden"][name$="-deleted"]',
    );
    return (
      deletedInput?.value === "1" ||
      deletedInput?.value === "true" ||
      block.hidden
    );
  };

  const editableInput = (block, suffix) =>
    block.querySelector(
      `input[name$="-${suffix}"], textarea[name$="-${suffix}"]`,
    );

  const hasBlockErrors = (block) =>
    Boolean(
      block.querySelector(
        '[aria-invalid="true"], .w-field--error, .error-message',
      ),
    );

  const isRenderedFocusableControl = (control) => {
    if (
      !control ||
      control.disabled ||
      control.hidden ||
      control.getAttribute("aria-disabled") === "true" ||
      control.getAttribute("aria-hidden") === "true" ||
      control.matches('input[type="hidden"]') ||
      control.tabIndex < 0
    ) {
      return false;
    }
    const style = window.getComputedStyle(control);
    return (
      control.getClientRects().length > 0 &&
      style.display !== "none" &&
      style.visibility !== "hidden"
    );
  };

  const imagePrimaryControl = (block) => {
    const imageField = block.querySelector('[data-contentpath="image"]');
    if (!imageField) {
      return null;
    }
    return (
      Array.from(
        imageField.querySelectorAll(
          ".chooser button, [data-chooser-action-change], " +
            "[data-chooser-action-choose], .w-dropdown__toggle",
        ),
      ).find(isRenderedFocusableControl) || null
    );
  };

  const updateImagePrimaryControl = (block) => {
    block
      .querySelectorAll("[data-news-image-primary-editor]")
      .forEach((control) => {
        delete control.dataset.newsImagePrimaryEditor;
        delete control.dataset.newsPrimaryEditor;
      });
    const control = imagePrimaryControl(block);
    if (control) {
      control.dataset.newsImagePrimaryEditor = "";
      control.dataset.newsPrimaryEditor = "";
    }
  };

  const visibleImageMetadataControls = (block) =>
    Array.from(
      block.querySelectorAll(
        ':is([data-contentpath="caption"], ' +
          '[data-contentpath="alt_text"], [data-contentpath="credit"]) ' +
          'input:not([type="hidden"]), textarea, select, button, ' +
          '[contenteditable="true"]',
      ),
    ).filter(isRenderedFocusableControl);

  const setBooleanData = (element, name, value) => {
    element.dataset[name] = String(Boolean(value));
  };

  const mediaLabel = (type) => {
    if (type === "youtube") {
      return "Video de YouTube";
    }
    if (type === "spotify") {
      return "Audio o pódcast de Spotify";
    }
    return "";
  };

  const addImageMetadataPreview = (block) => {
    if (block.querySelector("[data-news-image-meta]")) {
      return;
    }

    const preview = document.createElement("div");
    preview.className = "news-writing-image-meta";
    preview.dataset.newsImageMeta = "";

    const caption = document.createElement("p");
    caption.className = "news-writing-image-meta__caption";
    caption.dataset.newsImageCaption = "";

    const credit = document.createElement("p");
    credit.className = "news-writing-image-meta__credit";
    credit.dataset.newsImageCredit = "";

    preview.append(caption, credit);
    const content = block.querySelector(":scope > .w-panel .w-panel__content");
    content?.append(preview);
  };

  const updateImageMetadataPreview = (block) => {
    addImageMetadataPreview(block);
    const preview = block.querySelector("[data-news-image-meta]");
    const captionPreview = block.querySelector("[data-news-image-caption]");
    const creditPreview = block.querySelector("[data-news-image-credit]");
    const caption = editableInput(block, "caption")?.value.trim() || "";
    const credit = editableInput(block, "credit")?.value.trim() || "";

    if (captionPreview && captionPreview.textContent !== caption) {
      captionPreview.textContent = caption;
    }
    if (creditPreview && creditPreview.textContent !== credit) {
      creditPreview.textContent = credit;
    }
    if (captionPreview) {
      captionPreview.hidden = !caption;
    }
    if (creditPreview) {
      creditPreview.hidden = !credit;
    }
    if (preview) {
      preview.hidden = !caption && !credit;
    }
  };

  const addMediaPreview = (block, type) => {
    const urlInput = block.querySelector(
      'input[type="url"], input[name$="-value"]',
    );
    if (!urlInput || block.querySelector("[data-news-media-preview]")) {
      return;
    }

    const preview = document.createElement("button");
    preview.type = "button";
    preview.className = "news-writing-media-preview";
    preview.dataset.newsMediaPreview = "";
    preview.dataset.newsPrimaryEditor = "";

    const provider = document.createElement("span");
    provider.className = "news-writing-media-preview__provider";
    provider.textContent = mediaLabel(type);

    const url = document.createElement("span");
    url.className = "news-writing-media-preview__url";
    url.dataset.newsMediaPreviewUrl = "";

    preview.append(provider, url);
    preview.addEventListener("click", () => {
      block.dataset.newsBlockSelected = "true";
      window.requestAnimationFrame(() => urlInput.focus());
    });

    const content = block.querySelector(":scope > .w-panel .w-panel__content");
    content?.prepend(preview);
  };

  const updateBlockPresentation = (block) => {
    const type = blockTypeInput(block)?.value;
    if (!type) {
      return;
    }

    block.dataset.newsBlockType = type;
    setBooleanData(block, "newsBlockError", hasBlockErrors(block));

    if (type === "paragraph") {
      const editor = block.querySelector('[contenteditable="true"]');
      if (editor) {
        editor.dataset.newsPrimaryEditor = "";
      }
    }

    if (type === "article_image") {
      const imageInput = editableInput(block, "image");
      updateImageMetadataPreview(block);
      updateImagePrimaryControl(block);
      setBooleanData(block, "newsHasImage", imageInput?.value);
      setBooleanData(
        block,
        "newsHasCaption",
        editableInput(block, "caption")?.value.trim(),
      );
      setBooleanData(
        block,
        "newsHasCredit",
        editableInput(block, "credit")?.value.trim(),
      );
    }

    if (type === "youtube" || type === "spotify") {
      addMediaPreview(block, type);
      const urlInput = block.querySelector(
        'input[type="url"], input[name$="-value"]',
      );
      const previewUrl = block.querySelector("[data-news-media-preview-url]");
      const nextPreviewUrl = urlInput?.value.trim() || "Sin URL";
      if (previewUrl && previewUrl.textContent !== nextPreviewUrl) {
        previewUrl.textContent = nextPreviewUrl;
      }
      setBooleanData(block, "newsHasMediaUrl", urlInput?.value.trim());
    }
  };

  const activeBlocks = (root) =>
    Array.from(root.querySelectorAll("[data-streamfield-child]")).filter(
      (block) => blockTypeInput(block)?.value && !isDeletedBlock(block),
    );

  const blockHasContent = (block) => {
    const type = block.dataset.newsBlockType || blockTypeInput(block)?.value;
    if (type === "paragraph") {
      const editor = block.querySelector('[contenteditable="true"]');
      return Boolean(
        editor?.textContent.trim() ||
          editor?.querySelector("hr, .Draftail-DividerBlock"),
      );
    }
    if (type === "article_image") {
      return Boolean(
        editableInput(block, "image")?.value ||
          editableInput(block, "caption")?.value.trim() ||
          editableInput(block, "alt_text")?.value.trim() ||
          editableInput(block, "credit")?.value.trim(),
      );
    }
    if (type === "youtube" || type === "spotify") {
      return Boolean(
        block
          .querySelector('input[type="url"], input[name$="-value"]')
          ?.value.trim(),
      );
    }
    return true;
  };

  const visibleFocusableControl = (root) =>
    Array.from(
      root.querySelectorAll(
        'input:not([type="hidden"]), textarea, select, button, ' +
          '[contenteditable="true"]',
      ),
    ).find(
      (control) =>
        control.getClientRects().length > 0 &&
        !control.matches(
          ".c-sf-add-button, .c-sf-block__actions button, " +
            ".w-panel__controls button",
        ),
    );

  const firstInvalidControl = (root) => {
    const explicitInvalid = Array.from(
      root.querySelectorAll(
        'input:not([type="hidden"])[aria-invalid="true"], ' +
          'textarea[aria-invalid="true"], select[aria-invalid="true"], ' +
          'button[aria-invalid="true"], ' +
          '[contenteditable="true"][aria-invalid="true"]',
      ),
    ).find((control) => control.getClientRects().length > 0);
    if (explicitInvalid) {
      return explicitInvalid;
    }

    const leafErrorFields = Array.from(
      root.querySelectorAll(".w-field--error"),
    ).filter((field) => !field.querySelector(".w-field--error"));
    return leafErrorFields
      .map(visibleFocusableControl)
      .find((control) => Boolean(control));
  };

  const firstAuthoringControl = (root) =>
    Array.from(
      root.querySelectorAll(
        '[data-news-block-type="paragraph"] [contenteditable="true"], ' +
          "[data-streamfield-stream-container] .c-sf-add-button",
      ),
    ).find((control) => control.getClientRects().length > 0);

  const initialiseDialog = (launcher, dialog) => {
    if (dialog.dataset.newsWritingModeInitialised) {
      return;
    }
    dialog.dataset.newsWritingModeInitialised = "true";

    const writingRoot = dialog.querySelector("[data-news-writing-mode]");
    const status = launcher.querySelector("[data-news-writing-status]");
    const liveStatus = launcher.querySelector(
      "[data-news-writing-live-status]",
    );
    const openButton = launcher.querySelector("[data-news-writing-open]");
    const pageTitle = writingRoot?.querySelector(
      "[data-news-writing-page-title]",
    );
    const titleInput = document.getElementById("id_title");
    let shouldFocusErrors =
      launcher.dataset.newsWritingHasErrors === "true";
    let nestedDialogOpener = null;
    let nestedDialogBlock = null;

    if (!writingRoot || !status || !openButton) {
      return;
    }

    const updatePageTitle = () => {
      if (pageTitle) {
        pageTitle.textContent =
          titleInput?.value.trim() || "Noticia sin título";
      }
    };

    const updatePresentation = () => {
      const blocks = activeBlocks(writingRoot);
      blocks.forEach(updateBlockPresentation);
      const hasContent = blocks.some(blockHasContent);
      const nextStatus = hasContent ? "Con contenido" : "Sin contenido";
      if (status.textContent !== nextStatus) {
        status.textContent = nextStatus;
        if (liveStatus) {
          liveStatus.textContent = `Estado del contenido: ${nextStatus}.`;
        }
      }
    };

    const selectBlock = (block) => {
      writingRoot
        .querySelectorAll('[data-news-block-selected="true"]')
        .forEach((selected) => {
          if (selected !== block) {
            selected.dataset.newsBlockSelected = "false";
          }
        });
      if (block) {
        block.dataset.newsBlockSelected = "true";
      }
    };

    writingRoot.addEventListener("focusin", (event) => {
      if (!event.target.closest("[data-news-content-traversal-target]")) {
        selectBlock(event.target.closest("[data-streamfield-child]"));
      }
      updatePresentation();
    });
    writingRoot.addEventListener("focusout", () => {
      window.requestAnimationFrame(updatePresentation);
    });
    writingRoot.addEventListener("pointerdown", (event) => {
      selectBlock(event.target.closest("[data-streamfield-child]"));
    });
    writingRoot.addEventListener("input", updatePresentation);
    writingRoot.addEventListener("change", updatePresentation);

    const primaryTraversalTarget = (block) => {
      const type = block.dataset.newsBlockType || blockTypeInput(block)?.value;
      if (type === "paragraph") {
        return block.querySelector(
          '[contenteditable="true"][data-news-primary-editor]',
        );
      }
      if (type === "youtube" || type === "spotify") {
        if (block.dataset.newsBlockError !== "true") {
          return block.querySelector("[data-news-media-preview]");
        }
        return block.querySelector(
          'input[type="url"], input[name$="-value"]',
        );
      }
      if (type === "article_image") {
        return imagePrimaryControl(block);
      }
      return null;
    };

    const focusTraversalTarget = (block, control) => {
      const isCompactMediaPreview = control.matches(
        "[data-news-media-preview]",
      );
      if (isCompactMediaPreview) {
        selectBlock(null);
        control.dataset.newsContentTraversalTarget = "";
      } else {
        selectBlock(block);
      }

      control.focus();

      if (isCompactMediaPreview) {
        window.requestAnimationFrame(() => {
          delete control.dataset.newsContentTraversalTarget;
        });
        return;
      }

      if (!control.matches('[contenteditable="true"]')) {
        return;
      }
      window.requestAnimationFrame(() => {
        if (document.activeElement !== control) {
          return;
        }
        const selection = window.getSelection();
        if (selection?.rangeCount && control.contains(selection.anchorNode)) {
          return;
        }
        const range = document.createRange();
        range.selectNodeContents(control);
        range.collapse(false);
        selection?.removeAllRanges();
        selection?.addRange(range);
      });
    };

    writingRoot.addEventListener("keydown", (event) => {
      if (
        event.key !== "Tab" ||
        event.altKey ||
        event.ctrlKey ||
        event.metaKey
      ) {
        return;
      }

      const source = event.target.closest("[data-news-primary-editor]");
      let sourceBlock = source?.closest("[data-streamfield-child]");
      if (!sourceBlock && !event.shiftKey) {
        const imageBlock = event.target.closest(
          '[data-news-block-type="article_image"]',
        );
        const metadataControls = imageBlock
          ? visibleImageMetadataControls(imageBlock)
          : [];
        if (
          metadataControls.length &&
          event.target === metadataControls.at(-1)
        ) {
          sourceBlock = imageBlock;
        }
      }
      if (!sourceBlock) {
        return;
      }

      const blocks = activeBlocks(writingRoot);
      const sourceIndex = blocks.indexOf(sourceBlock);
      if (sourceIndex < 0) {
        return;
      }
      const destinationIndex = sourceIndex + (event.shiftKey ? -1 : 1);
      const destinationBlock = blocks[destinationIndex];
      if (!destinationBlock) {
        return;
      }

      const destinationControl = primaryTraversalTarget(destinationBlock);
      if (!destinationControl) {
        return;
      }

      event.preventDefault();
      focusTraversalTarget(destinationBlock, destinationControl);
    });

    new MutationObserver(updatePresentation).observe(writingRoot, {
      childList: true,
      subtree: true,
    });

    titleInput?.addEventListener("input", updatePageTitle);

    const visibleNestedModal = () =>
      Array.from(document.querySelectorAll(".modal.in, .modal.show")).find(
        (modal) => {
          const style = window.getComputedStyle(modal);
          return (
            style.display !== "none" &&
            style.visibility !== "hidden" &&
            !dialog.contains(modal)
          );
        },
      );

    const allowFocusInNestedSurfaces = () => {
      if (dialog.getAttribute("aria-hidden") === "true") {
        return;
      }
      visibleNestedModal()?.setAttribute(
        "data-a11y-dialog-ignore-focus-trap",
        "",
      );
      document.querySelectorAll("[data-tippy-root]").forEach((surface) => {
        if (surface.getClientRects().length > 0) {
          surface.setAttribute("data-a11y-dialog-ignore-focus-trap", "");
        }
      });
    };

    new MutationObserver(allowFocusInNestedSurfaces).observe(document.body, {
      childList: true,
      subtree: true,
    });

    writingRoot.addEventListener("click", (event) => {
      const chooserAction = event.target.closest(
        "[data-chooser-action-choose], [data-chooser-action-change]",
      );
      if (!chooserAction) {
        return;
      }

      nestedDialogOpener = chooserAction;
      nestedDialogBlock = chooserAction.closest("[data-streamfield-child]");
      let focusAttempts = 0;
      const focusNestedDialog = () => {
        const nestedModal = visibleNestedModal();
        if (nestedModal) {
          allowFocusInNestedSurfaces();
          if (!nestedModal.contains(document.activeElement)) {
            visibleFocusableControl(nestedModal)?.focus();
          }
          return;
        }
        focusAttempts += 1;
        if (focusAttempts < 40) {
          window.setTimeout(focusNestedDialog, 50);
        }
      };
      window.setTimeout(focusNestedDialog, 0);
    });

    document.addEventListener(
      "keydown",
      (event) => {
        if (
          event.key !== "Escape" ||
          dialog.getAttribute("aria-hidden") === "true"
        ) {
          return;
        }

        const nestedModal = visibleNestedModal();
        if (!nestedModal) {
          return;
        }

        event.preventDefault();
        event.stopImmediatePropagation();
        const closeButton =
          nestedModal.querySelector(
            '[data-modal-close], .close, [aria-label="Cerrar"]',
          ) ||
          Array.from(nestedModal.querySelectorAll("button")).find((button) =>
            button.textContent.trim().toLowerCase().startsWith("cerrar"),
          );
        const restoreUsefulFocus = () => {
          const target =
            nestedDialogOpener?.isConnected &&
            nestedDialogOpener.getClientRects().length > 0
              ? nestedDialogOpener
              : visibleFocusableControl(nestedDialogBlock);
          target?.focus({ preventScroll: true });
        };
        const restoreAfterParentFocus = (focusEvent) => {
          if (!dialog.contains(focusEvent.target)) {
            return;
          }
          document.removeEventListener(
            "focusin",
            restoreAfterParentFocus,
            true,
          );
          window.setTimeout(restoreUsefulFocus, 0);
        };
        document.addEventListener(
          "focusin",
          restoreAfterParentFocus,
          true,
        );
        closeButton?.click();
        let restoreAttempts = 0;
        const restoreNestedDialogFocus = () => {
          if (visibleNestedModal()) {
            restoreAttempts += 1;
            if (restoreAttempts < 40) {
              window.setTimeout(restoreNestedDialogFocus, 50);
            }
            return;
          }
          window.setTimeout(() => {
            document.removeEventListener(
              "focusin",
              restoreAfterParentFocus,
              true,
            );
            restoreUsefulFocus();
          }, 750);
        };
        window.setTimeout(restoreNestedDialogFocus, 0);
      },
      true,
    );

    openButton.addEventListener("click", () => {
      shouldFocusErrors =
        launcher.dataset.newsWritingHasErrors === "true";
    });

    dialog.addEventListener("w-dialog:shown", () => {
      openButton.setAttribute("aria-expanded", "true");
      updatePageTitle();
      updatePresentation();
      window.requestAnimationFrame(() => {
        window.requestAnimationFrame(() => {
          const target = shouldFocusErrors
            ? firstInvalidControl(writingRoot)
            : firstAuthoringControl(writingRoot);
          target?.focus();
          shouldFocusErrors = false;
        });
      });
    });

    dialog.addEventListener("w-dialog:hidden", () => {
      openButton.setAttribute("aria-expanded", "false");
      updatePresentation();
      openButton.focus();
      window.requestAnimationFrame(() => openButton.focus());
    });

    document.addEventListener(
      "click",
      (event) => {
        const anchor = event.target.closest('a[href^="#"]');
        if (!anchor || !anchor.hash) {
          return;
        }
        const target = document.getElementById(
          decodeURIComponent(anchor.hash.slice(1)),
        );
        if (!target || !writingRoot.contains(target)) {
          return;
        }

        event.preventDefault();
        shouldFocusErrors = true;
        openButton.click();
      },
      true,
    );

    updatePageTitle();
    updatePresentation();
  };

  const initialiseLauncher = (launcher) => {
    if (launcher.dataset.newsWritingLauncherInitialised) {
      return;
    }
    launcher.dataset.newsWritingLauncherInitialised = "true";

    const dialogId = launcher.dataset.newsWritingDialogId;
    const connect = () => {
      const dialog = document.getElementById(dialogId);
      if (!dialog) {
        return false;
      }
      initialiseDialog(launcher, dialog);
      return true;
    };

    if (!connect()) {
      const observer = new MutationObserver(() => {
        if (connect()) {
          observer.disconnect();
        }
      });
      observer.observe(document.documentElement, {
        childList: true,
        subtree: true,
      });
    }
  };

  const start = () => {
    document
      .querySelectorAll("[data-news-writing-launcher]")
      .forEach(initialiseLauncher);
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
