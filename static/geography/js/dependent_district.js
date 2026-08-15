(() => {
  const MINIMUM_QUERY_LENGTH = 3;

  const initialize = (container) => {
    if (container.dataset.districtInitialized === "true") {
      return;
    }
    const department = document.querySelector(container.dataset.departmentField);
    const valueInput = container.querySelector("[data-district-value]");
    const searchInput = container.querySelector("[data-district-search]");
    const results = container.querySelector("[data-district-results]");
    const hint = container.querySelector("[data-district-hint]");
    const clearButton = container.querySelector("[data-district-clear]");
    if (!department || !valueInput || !searchInput || !results || !clearButton) {
      return;
    }
    container.dataset.districtInitialized = "true";

    let requestController = null;
    let activeIndex = -1;

    const cancelRequest = () => {
      requestController?.abort();
      requestController = null;
    };

    const closeResults = () => {
      results.replaceChildren();
      results.hidden = true;
      searchInput.setAttribute("aria-expanded", "false");
      searchInput.removeAttribute("aria-activedescendant");
      activeIndex = -1;
    };

    const clearSelection = ({ clearSearch = true } = {}) => {
      cancelRequest();
      valueInput.value = "";
      if (clearSearch) {
        searchInput.value = "";
      }
      clearButton.hidden = true;
      closeResults();
    };

    const updateEnabledState = () => {
      const enabled = Boolean(department.value);
      searchInput.disabled = !enabled;
      if (!enabled) {
        clearSelection();
      }
    };

    const selectResult = (option) => {
      valueInput.value = option.dataset.code;
      searchInput.value = option.dataset.name;
      container.dataset.selectedDepartment = department.value;
      clearButton.hidden = false;
      closeResults();
      searchInput.focus();
    };

    const renderResults = (items) => {
      closeResults();
      items.forEach((item, index) => {
        const option = document.createElement("li");
        option.id = `${searchInput.id}_option_${index}`;
        option.className = "dependent-district__option";
        option.setAttribute("role", "option");
        option.dataset.code = item.code;
        option.dataset.name = item.name;
        option.textContent = item.province
          ? `${item.name} (${item.province})`
          : item.name;
        option.addEventListener("mousedown", (event) => {
          event.preventDefault();
          selectResult(option);
        });
        results.append(option);
      });
      if (items.length) {
        results.hidden = false;
        searchInput.setAttribute("aria-expanded", "true");
      } else {
        hint.textContent = "No se encontraron distritos compatibles.";
      }
    };

    const search = async () => {
      const query = searchInput.value.trim();
      cancelRequest();
      valueInput.value = "";
      clearButton.hidden = true;
      if (query.length < MINIMUM_QUERY_LENGTH) {
        hint.textContent = "Escribe al menos 3 caracteres.";
        closeResults();
        return;
      }
      requestController = new AbortController();
      const url = new URL(container.dataset.lookupUrl, window.location.origin);
      url.searchParams.set("departamento", department.value);
      url.searchParams.set("buscar", query);
      try {
        const response = await fetch(url, {
          headers: { Accept: "application/json" },
          signal: requestController.signal,
        });
        if (!response.ok) {
          throw new Error(`District lookup failed with ${response.status}`);
        }
        const payload = await response.json();
        hint.textContent = "Selecciona un distrito de los resultados.";
        renderResults(payload.results);
      } catch (error) {
        if (error.name !== "AbortError") {
          hint.textContent = "No se pudo consultar los distritos.";
          closeResults();
        }
      }
    };

    searchInput.addEventListener("input", search);
    searchInput.addEventListener("keydown", (event) => {
      const options = [...results.querySelectorAll('[role="option"]')];
      if (event.key === "Escape") {
        closeResults();
        return;
      }
      if (!options.length || !["ArrowDown", "ArrowUp", "Enter"].includes(event.key)) {
        return;
      }
      event.preventDefault();
      if (event.key === "Enter" && activeIndex >= 0) {
        selectResult(options[activeIndex]);
        return;
      }
      const movement = event.key === "ArrowDown" ? 1 : -1;
      activeIndex = (activeIndex + movement + options.length) % options.length;
      options.forEach((option, index) => {
        option.setAttribute("aria-selected", String(index === activeIndex));
      });
      searchInput.setAttribute("aria-activedescendant", options[activeIndex].id);
    });
    searchInput.addEventListener("blur", () => {
      window.setTimeout(closeResults, 0);
    });
    clearButton.addEventListener("click", () => {
      clearSelection();
      searchInput.focus();
    });
    department.addEventListener("change", () => {
      if (department.value !== container.dataset.selectedDepartment) {
        clearSelection();
      }
      container.dataset.selectedDepartment = department.value;
      updateEnabledState();
    });

    if (
      valueInput.value &&
      container.dataset.selectedDepartment !== department.value
    ) {
      clearSelection();
    }
    updateEnabledState();
  };

  const initializeAll = () => {
    document
      .querySelectorAll("[data-dependent-district]")
      .forEach(initialize);
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeAll, { once: true });
  } else {
    initializeAll();
  }
})();
