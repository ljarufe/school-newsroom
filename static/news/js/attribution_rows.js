(() => {
  const payloadFields = {
    AUTHOR: ["author_profile"],
    PUBLIC_CREDIT: ["display_name"],
    INTERNAL_CONTRIBUTOR: ["minor_contributor"],
  };

  const autosaveActiveAttribute = "data-w-autosave-active-value";

  const fieldContainer = (field) =>
    field.closest(".w-field__wrapper") || field.closest("li") || field.parentElement;

  const attributionRows = () =>
    Array.from(
      document.querySelectorAll(
        "#id_attributions-FORMS [data-inline-panel-child]",
      ),
    );

  const rowPayloadIsComplete = (row) => {
    const deleteField = row.querySelector('input[name$="-DELETE"]');
    if (deleteField?.checked) return true;

    const kind = row.querySelector('select[name$="-kind"]');
    if (!kind?.value) {
      // A completely blank extra form is ignored normally by the formset.
      return true;
    }

    const [payloadName] = payloadFields[kind.value] || [];
    if (!payloadName) return true;

    const payloadField = row.querySelector(`[name$="-${payloadName}"]`);
    if (!payloadField) return false;

    return Boolean(String(payloadField.value || "").trim());
  };

  const pauseAttributionAutosave = (form) => {
    if (
      form.dataset.attributionAutosavePaused === "true" ||
      form.getAttribute(autosaveActiveAttribute) === "false"
    ) {
      return;
    }

    form.dataset.attributionAutosavePaused = "true";
    form.dataset.attributionAutosavePreviousActive =
      form.getAttribute(autosaveActiveAttribute) || "";
    form.setAttribute(autosaveActiveAttribute, "false");
  };

  const resumeAttributionAutosave = (form) => {
    if (form.dataset.attributionAutosavePaused !== "true") return;

    const previous = form.dataset.attributionAutosavePreviousActive;
    if (previous) {
      form.setAttribute(autosaveActiveAttribute, previous);
    } else {
      form.removeAttribute(autosaveActiveAttribute);
    }

    delete form.dataset.attributionAutosavePaused;
    delete form.dataset.attributionAutosavePreviousActive;
  };

  const syncAutosaveState = () => {
    const form = document.querySelector(
      "#page-edit-form[data-controller~='w-autosave']",
    );
    if (!form) return;

    if (attributionRows().some((row) => !rowPayloadIsComplete(row))) {
      pauseAttributionAutosave(form);
    } else {
      resumeAttributionAutosave(form);
    }
  };

  const clearChooser = (field) => {
    const chooser = document.getElementById(`${field.id}-chooser`);
    const clearButton = chooser?.querySelector("[data-chooser-action-clear]");
    if (clearButton && !chooser.classList.contains("blank")) {
      clearButton.click();
      return;
    }
    field.value = "";
    field.dispatchEvent(new Event("change", { bubbles: true }));
  };

  const configureRow = (row, clearInactive = false) => {
    const kind = row.querySelector('select[name$="-kind"]');
    if (!kind) return;

    const enabled = new Set(payloadFields[kind.value] || []);
    Object.entries(payloadFields)
      .flatMap(([, names]) => names)
      .forEach((name) => {
        const field = row.querySelector(`[name$="-${name}"]`);
        if (!field) return;
        const isEnabled = enabled.has(name);
        fieldContainer(field).hidden = !isEnabled;
        if (clearInactive && !isEnabled) {
          if (name === "display_name") {
            field.value = "";
            field.dispatchEvent(new Event("input", { bubbles: true }));
            field.dispatchEvent(new Event("change", { bubbles: true }));
          } else {
            clearChooser(field);
          }
        }
      });
  };

  const configureRows = () => {
    attributionRows().forEach((row) => {
      if (row.dataset.attributionConfigured) return;

      row.dataset.attributionConfigured = "true";
      configureRow(row);

      row
        .querySelector('select[name$="-kind"]')
        ?.addEventListener("change", () => {
          configureRow(row, true);
          syncAutosaveState();
        });

      row.addEventListener("input", syncAutosaveState);
      row.addEventListener("change", syncAutosaveState);
    });

    syncAutosaveState();
  };

  document.addEventListener("DOMContentLoaded", configureRows);
  document.addEventListener("w-formset:ready", configureRows);
  document.addEventListener("w-formset:added", configureRows);
  document.addEventListener("w-formset:removed", () => {
    window.requestAnimationFrame(syncAutosaveState);
  });
})();
