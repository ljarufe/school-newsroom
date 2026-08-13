(() => {
  const sectionSelect = document.querySelector("#news-section");
  const subsectionSelect = document.querySelector("[data-news-subsection]");

  if (!sectionSelect || !subsectionSelect) {
    return;
  }

  const updateSubsections = ({ clearIncompatible }) => {
    const parentSlug = sectionSelect.value;
    const subsectionOptions = subsectionSelect.querySelectorAll(
      "option[data-parent-section]",
    );
    const subsectionGroups = subsectionSelect.querySelectorAll(
      "optgroup[data-parent-section]",
    );

    subsectionOptions.forEach((option) => {
      const compatible = !parentSlug || option.dataset.parentSection === parentSlug;
      option.hidden = !compatible;
      if (!compatible && clearIncompatible && option.selected) {
        subsectionSelect.value = "";
      }
    });
    subsectionGroups.forEach((group) => {
      group.hidden = Boolean(parentSlug) && group.dataset.parentSection !== parentSlug;
    });
  };

  updateSubsections({ clearIncompatible: false });
  sectionSelect.addEventListener("change", () => {
    updateSubsections({ clearIncompatible: true });
  });
})();
