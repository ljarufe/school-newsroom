(function () {
  window.schoolNewsroom = window.schoolNewsroom || {};
  window.schoolNewsroom.blocks = window.schoolNewsroom.blocks || {};

  const BaseStructBlockDefinition =
    window.wagtailStreamField &&
    window.wagtailStreamField.blocks &&
    window.wagtailStreamField.blocks.StructBlockDefinition;
  const setupCaptionAltSync =
    window.schoolNewsroom.images &&
    window.schoolNewsroom.images.setupCaptionAltSync;

  if (!BaseStructBlockDefinition || !setupCaptionAltSync) {
    return;
  }

  function inputForPrefix(prefix, fieldName) {
    return document.querySelector(`[name="${prefix}-${fieldName}"]`);
  }

  function setupBlockCaptionAltSync(prefix) {
    const captionInput = inputForPrefix(prefix, "caption");
    const altInput = inputForPrefix(prefix, "alt_text");
    setupCaptionAltSync(captionInput, altInput);
  }

  class ArticleImageBlockDefinition extends BaseStructBlockDefinition {
    render(placeholder, prefix, initialState, initialError) {
      const block = super.render(
        placeholder,
        prefix,
        initialState,
        initialError,
      );
      setupBlockCaptionAltSync(prefix);
      return block;
    }
  }

  window.schoolNewsroom.blocks.ArticleImageBlock = ArticleImageBlockDefinition;
  window.telepath.register(
    "schoolNewsroom.blocks.ArticleImageBlock",
    ArticleImageBlockDefinition,
  );
})();
