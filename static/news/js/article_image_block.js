(function () {
  window.schoolNewsroom = window.schoolNewsroom || {};
  window.schoolNewsroom.blocks = window.schoolNewsroom.blocks || {};

  const BaseStructBlockDefinition =
    window.wagtailStreamField &&
    window.wagtailStreamField.blocks &&
    window.wagtailStreamField.blocks.StructBlockDefinition;

  if (!BaseStructBlockDefinition) {
    return;
  }

  function inputForPrefix(prefix, fieldName) {
    return document.querySelector(`[name="${prefix}-${fieldName}"]`);
  }

  function setupCaptionAltSync(prefix) {
    const captionInput = inputForPrefix(prefix, "caption");
    const altInput = inputForPrefix(prefix, "alt_text");

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
  }

  class ArticleImageBlockDefinition extends BaseStructBlockDefinition {
    render(placeholder, prefix, initialState, initialError) {
      const block = super.render(
        placeholder,
        prefix,
        initialState,
        initialError,
      );
      setupCaptionAltSync(prefix);
      return block;
    }
  }

  window.schoolNewsroom.blocks.ArticleImageBlock = ArticleImageBlockDefinition;
  window.telepath.register(
    "schoolNewsroom.blocks.ArticleImageBlock",
    ArticleImageBlockDefinition,
  );
})();
