(() => {
  const initializeTree = (tree) => {
    if (tree.dataset.newsTaxonomyReady === "true") {
      return;
    }
    tree.dataset.newsTaxonomyReady = "true";

    tree.querySelectorAll("[data-news-taxonomy-disclosure]").forEach((button) => {
      button.addEventListener("click", () => {
        const branch = button.closest("[data-news-taxonomy-branch]");
        const children = document.getElementById(button.getAttribute("aria-controls"));
        const rootName = branch.dataset.rootName;
        const expanded = button.getAttribute("aria-expanded") === "true";
        button.setAttribute("aria-expanded", String(!expanded));
        button.setAttribute(
          "aria-label",
          `${expanded ? "Mostrar" : "Ocultar"} subsecciones de ${rootName}`,
        );
        button.querySelector("[aria-hidden='true']").textContent = expanded ? "▸" : "▾";
        children.hidden = expanded;
      });
    });
  };

  const initializeAll = () => {
    document.querySelectorAll("[data-news-taxonomy-tree]").forEach(initializeTree);
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeAll, { once: true });
  } else {
    initializeAll();
  }
})();
