(() => {
  const isContextualAuthorProfileForm = (form) =>
    form?.querySelector('input[name="display_name"]') &&
    form.querySelector("#id_photo-chooser");

  let activeContext;

  const restoreParentModal = () => {
    if (!activeContext) return;
    const context = activeContext;
    activeContext = undefined;
    if (context.placeholder.isConnected) {
      context.placeholder.replaceWith(context.parentModal);
      window.jQuery(context.parentModal).modal("show");
    }
  };

  document.addEventListener(
    "click",
    (event) => {
      const trigger = event.target.closest("[data-chooser-action-choose]");
      if (trigger) {
        const form = trigger.closest("form");
        const parentModal = trigger.closest(".modal");
        if (
          isContextualAuthorProfileForm(form) &&
          parentModal?.parentElement === document.body &&
          trigger.closest("#id_photo-chooser")
        ) {
          event.preventDefault();
          const context = {
            parentModal,
            placeholder: document.createComment("contextual-author-profile-modal"),
          };
          context.parentModal.after(context.placeholder);
          context.parentModal.remove();
          activeContext = context;
          return;
        }
      }

      const action = event.target.closest(
        "[data-dismiss='modal'], [data-chooser-modal-choice]",
      );
      if (action && activeContext && action.closest(".modal")) {
        restoreParentModal();
      }
    },
    true,
  );
})();
