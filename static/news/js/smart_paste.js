(function () {
  "use strict";

  const handledPasteEvents = new WeakSet();
  const editorialBlockSelector = [
    "address",
    "div",
    "p",
    "pre",
  ].join(",");
  const explicitStructureSelector = [
    "blockquote",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "ol",
    "table",
    "ul",
  ].join(",");

  const csrfToken = () =>
    document.querySelector('[name="csrfmiddlewaretoken"]')?.value || "";

  const blockType = (block) =>
    block?.querySelector(
      ':scope input[type="hidden"][name$="-type"]',
    )?.value || "";

  const streamBlockFor = (writingRoot) => {
    const streamContainer = writingRoot.querySelector(
      ".news-writing-mode__document [data-streamfield-stream-container]",
    );
    const rootBlock = streamContainer?.parentElement?.rootBlock;

    // Wagtail 7.4 binds the top-level StreamBlock controller here. Keep the
    // version-specific integration at this boundary instead of fabricating
    // management-form fields.
    if (
      !rootBlock ||
      !Array.isArray(rootBlock.children) ||
      typeof rootBlock.insert !== "function" ||
      typeof rootBlock.getState !== "function" ||
      typeof rootBlock.setState !== "function"
    ) {
      return null;
    }
    return rootBlock;
  };

  const writingModeIsActive = (writingRoot) => {
    const dialog = writingRoot.closest(".news-writing-dialog");
    return (
      dialog?.getAttribute("aria-hidden") !== "true" &&
      writingRoot.getClientRects().length > 0
    );
  };

  const nonemptyPlainLines = (source) =>
    source
      .replace(/\r\n?/g, "\n")
      .split("\n")
      .filter((line) => line.trim()).length;

  const hasStructuredClipboardContent = (htmlSource, plainText) => {
    if (nonemptyPlainLines(plainText) > 1) {
      return true;
    }
    if (!htmlSource.trim()) {
      return false;
    }

    const parsed = new DOMParser().parseFromString(htmlSource, "text/html");
    if (parsed.body.querySelector(explicitStructureSelector)) {
      return true;
    }

    const meaningfulBlocks = Array.from(
      parsed.body.querySelectorAll(editorialBlockSelector),
    ).filter((element) => {
      if (
        element.matches("div") &&
        element.querySelector(
          `${editorialBlockSelector},${explicitStructureSelector}`,
        )
      ) {
        return false;
      }
      return Boolean(
        element.textContent.replace(/\u00a0/g, " ").trim() ||
          element.querySelector("br"),
      );
    });
    return meaningfulBlocks.length > 1;
  };

  const pasteTargetFor = (event) =>
    event.target instanceof Element
      ? event.target
      : event.target?.parentElement || null;

  const isInternalEditorControl = (target) =>
    Boolean(
      target.closest(
        "input, textarea, select, option, button, " +
          ".handsontable, [id$='-handsontable-container']",
      ),
    );

  const canHandlePasteAt = (writingDocument, target) => {
    if (!target || !writingDocument.contains(target)) {
      return false;
    }
    if (isInternalEditorControl(target)) {
      return false;
    }

    const contentEditable = target.closest('[contenteditable="true"]');
    if (contentEditable) {
      return (
        blockType(contentEditable.closest("[data-streamfield-child]")) ===
        "paragraph"
      );
    }

    const field = target.closest("[data-contentpath]");
    return !field || blockType(field.closest("[data-streamfield-child]")) === "paragraph";
  };

  const paragraphIsCompletelyEmpty = (block) => {
    if (blockType(block) !== "paragraph") {
      return false;
    }
    const valueInput = block.querySelector(
      ':scope input[type="hidden"][name$="-value"]',
    );
    if (valueInput?.value) {
      try {
        const state = JSON.parse(valueInput.value);
        if (Array.isArray(state.blocks)) {
          return state.blocks.every(
            (item) =>
              item.type !== "atomic" &&
              !String(item.text || "")
                .replace(/\u00a0/g, " ")
                .trim(),
          );
        }
      } catch (error) {
        // Fall back to the rendered editor for malformed transient state.
      }
    }
    const editor = block.querySelector('[contenteditable="true"]');
    return (
      !editor?.textContent.replace(/\u00a0/g, " ").trim() &&
      !editor?.querySelector("hr, .Draftail-DividerBlock")
    );
  };

  const insertionPlanFor = (writingRoot, streamBlock, eventTarget) => {
    const targetElement = eventTarget.closest("[data-streamfield-child]");
    const selectedElement = writingRoot.querySelector(
      '[data-streamfield-child][data-news-block-selected="true"]',
    );
    const anchorElement = targetElement || selectedElement;
    const anchorChild = streamBlock.children.find(
      (child) => child.element === anchorElement,
    );

    if (!streamBlock.children.length) {
      return { mode: "start", anchorChild: null };
    }
    if (anchorChild && paragraphIsCompletelyEmpty(anchorElement)) {
      return { mode: "replace-empty", anchorChild };
    }
    if (anchorChild) {
      return { mode: "after", anchorChild };
    }
    return { mode: "end", anchorChild: null };
  };

  const resolveInsertion = (streamBlock, plan) => {
    const anchorIndex = plan.anchorChild
      ? streamBlock.children.indexOf(plan.anchorChild)
      : -1;
    if (
      plan.mode === "replace-empty" &&
      anchorIndex >= 0 &&
      paragraphIsCompletelyEmpty(plan.anchorChild.element)
    ) {
      return {
        index: anchorIndex,
        replacedChild: plan.anchorChild,
      };
    }
    if (plan.mode === "after" && anchorIndex >= 0) {
      return { index: anchorIndex + 1, replacedChild: null };
    }
    if (plan.mode === "start" && !streamBlock.children.length) {
      return { index: 0, replacedChild: null };
    }
    return {
      index: streamBlock.children.length,
      replacedChild: null,
    };
  };

  const canonicalValue = (value) => {
    if (Array.isArray(value)) {
      return value.map(canonicalValue);
    }
    if (value && typeof value === "object") {
      return Object.fromEntries(
        Object.keys(value)
          .sort()
          .map((key) => [key, canonicalValue(value[key])]),
      );
    }
    return value;
  };

  const controlValue = (control) => {
    if (control.matches('input[type="checkbox"], input[type="radio"]')) {
      return {
        checked: control.checked,
        value: control.value,
      };
    }
    if (control instanceof HTMLSelectElement && control.multiple) {
      return Array.from(control.selectedOptions, (option) => option.value);
    }
    if (
      control instanceof HTMLInputElement &&
      control.type === "hidden" &&
      control.name.endsWith("-value") &&
      ["{", "["].includes(control.value.trim().charAt(0))
    ) {
      try {
        return canonicalValue(JSON.parse(control.value));
      } catch (error) {
        // A malformed transient value still participates as its raw string.
      }
    }
    return control.value;
  };

  const streamSnapshotFor = (streamBlock) => ({
    children: Array.from(streamBlock.children),
    values: JSON.stringify(
      streamBlock.children.map((child) =>
        Array.from(
          child.element.querySelectorAll("input, textarea, select"),
          (control) => ({
            name: control.name,
            type: control.type,
            value: controlValue(control),
          }),
        ),
      ),
    ),
  });

  const streamMatchesSnapshot = (streamBlock, snapshot) =>
    streamBlock.children.length === snapshot.children.length &&
    streamBlock.children.every(
      (child, index) => child === snapshot.children[index],
    ) &&
    streamSnapshotFor(streamBlock).values === snapshot.values;

  const warningSummary = (warnings) => {
    const messages = [];
    const tableWasSimplified = warnings.some(
      (warning) =>
        warning.includes("celdas combinadas") ||
        warning.includes("filas irregulares"),
    );
    if (tableWasSimplified) {
      messages.push("Una tabla fue simplificada.");
    }
    warnings
      .filter(
        (warning) =>
          !warning.includes("celdas combinadas") &&
          !warning.includes("filas irregulares"),
      )
      .forEach((warning) => messages.push(warning));
    return messages.join(" ");
  };

  const initialiseSmartPaste = (writingRoot) => {
    if (writingRoot.dataset.newsSmartPasteInitialised) {
      return;
    }
    writingRoot.dataset.newsSmartPasteInitialised = "true";

    const writingDocument = writingRoot.querySelector(
      ".news-writing-mode__document",
    );
    const notice = writingRoot.querySelector("[data-news-smart-paste-notice]");
    const dialog = writingRoot.closest(".news-writing-dialog");
    const launcher = writingRoot.closest("[data-news-writing-launcher]");
    const liveStatus = launcher?.querySelector(
      "[data-news-writing-live-status]",
    );
    const endpoint = writingRoot.dataset.newsSmartPasteUrl;
    if (!writingDocument || !notice || !dialog || !endpoint) {
      return;
    }

    let processing = false;
    let requestVersion = 0;
    let noticeTimer = null;

    const showNotice = (message, { isError = false } = {}) => {
      window.clearTimeout(noticeTimer);
      notice.textContent = message;
      notice.dataset.newsPasteError = String(isError);
      notice.setAttribute("role", isError ? "alert" : "status");
      notice.hidden = false;
      if (liveStatus) {
        liveStatus.textContent = message;
      }
      noticeTimer = window.setTimeout(
        () => {
          notice.hidden = true;
        },
        isError ? 9000 : 7000,
      );
    };

    const invalidatePendingPaste = () => {
      requestVersion += 1;
      processing = false;
      window.clearTimeout(noticeTimer);
      notice.hidden = true;
    };

    dialog.addEventListener("w-dialog:shown", invalidatePendingPaste);
    dialog.addEventListener("w-dialog:hidden", invalidatePendingPaste);

    writingDocument.addEventListener(
      "paste",
      async (event) => {
        if (
          handledPasteEvents.has(event) ||
          !writingModeIsActive(writingRoot)
        ) {
          return;
        }
        const target = pasteTargetFor(event);
        if (!canHandlePasteAt(writingDocument, target)) {
          return;
        }

        const clipboard = event.clipboardData;
        if (!clipboard) {
          return;
        }
        const htmlSource = clipboard.getData("text/html");
        const plainText = clipboard.getData("text/plain");
        if (!hasStructuredClipboardContent(htmlSource, plainText)) {
          return;
        }

        handledPasteEvents.add(event);
        event.preventDefault();
        event.stopPropagation();
        if (processing) {
          showNotice(
            "Espera a que termine el pegado anterior antes de volver a pegar.",
            { isError: true },
          );
          return;
        }

        const streamBlock = streamBlockFor(writingRoot);
        if (!streamBlock) {
          showNotice(
            "No se pudo procesar el contenido pegado. " +
              "Cierra y vuelve a abrir el modo redacción.",
            { isError: true },
          );
          return;
        }

        const plan = insertionPlanFor(writingRoot, streamBlock, target);
        const streamSnapshot = streamSnapshotFor(streamBlock);
        const currentRequestVersion = ++requestVersion;
        processing = true;

        try {
          const response = await fetch(endpoint, {
            method: "POST",
            credentials: "same-origin",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": csrfToken(),
            },
            body: JSON.stringify({
              html: htmlSource,
              text: plainText,
            }),
          });
          let payload = {};
          try {
            payload = await response.json();
          } catch (error) {
            payload = {};
          }
          if (
            currentRequestVersion !== requestVersion ||
            !writingModeIsActive(writingRoot)
          ) {
            return;
          }
          if (!response.ok || !Array.isArray(payload.blocks)) {
            throw new Error(
              payload.error || "El servidor no devolvió una respuesta válida.",
            );
          }
          if (!payload.blocks.length) {
            throw new Error("No se encontraron bloques compatibles.");
          }

          const currentStreamBlock = streamBlockFor(writingRoot);
          if (
            currentStreamBlock !== streamBlock ||
            !streamMatchesSnapshot(streamBlock, streamSnapshot)
          ) {
            return;
          }
          const insertion = resolveInsertion(streamBlock, plan);
          const originalState = streamBlock.getState();
          let firstInsertedBlock = null;

          try {
            payload.blocks.forEach((block, offset) => {
              const inserted = streamBlock.insert(
                { type: block.type, value: block.value },
                insertion.index + offset,
                { animate: false, focus: false },
              );
              firstInsertedBlock ||= inserted;
            });
            if (insertion.replacedChild) {
              if (typeof insertion.replacedChild.delete !== "function") {
                throw new Error("The empty paragraph cannot be replaced.");
              }
              insertion.replacedChild.delete({ animate: false });
            }
          } catch (insertionError) {
            streamBlock.setState(originalState);
            throw insertionError;
          }

          writingRoot.dispatchEvent(new Event("input", { bubbles: true }));
          const count = payload.blocks.length;
          const warningText = warningSummary(payload.warnings || []);
          showNotice(
            `Se ${count === 1 ? "pegó" : "pegaron"} ${count} ` +
              `${count === 1 ? "bloque" : "bloques"}.` +
              (warningText ? ` ${warningText}` : ""),
          );
          window.requestAnimationFrame(() => {
            firstInsertedBlock?.focus({ soft: true });
          });
        } catch (requestError) {
          if (currentRequestVersion !== requestVersion) {
            return;
          }
          showNotice(
            "No se pudo procesar el contenido pegado. " +
              "El contenido existente no cambió.",
            { isError: true },
          );
        } finally {
          if (currentRequestVersion === requestVersion) {
            processing = false;
          }
        }
      },
      true,
    );
  };

  const start = () => {
    document
      .querySelectorAll("[data-news-writing-mode]")
      .forEach(initialiseSmartPaste);
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
