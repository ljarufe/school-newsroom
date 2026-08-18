const { expect, test } = require("@playwright/test");

const login = async (page) => {
  await page.goto("/admin/login/");
  await page.locator("#id_username").fill(process.env.BROWSER_TEST_USERNAME);
  await page.locator("#id_password").fill(process.env.BROWSER_TEST_PASSWORD);
  await page.locator('button[type="submit"]').click();
  await page.waitForURL((url) => !url.pathname.endsWith("/login/"));
};

const openEditor = (page, pageId) => page.goto(`/admin/pages/${pageId}/edit/`);

const authorshipPanel = (page) =>
  page.locator("#panel-child-edicion_de_la_noticia-autoria_y_creditos-section");

const attributionRows = (panel) =>
  panel.locator('[data-inline-panel-child]:visible');

const authorProfileTitle = (row) =>
  row.locator('div[id$="-author_profile-title"]');

const minorContributorTitle = (row) =>
  row.locator('div[id$="-minor_contributor-title"]');

const addAttribution = async (panel, kind) => {
  const rowIndex = await attributionRows(panel).count();
  await panel.locator("#id_attributions-ADD").click();
  const row = attributionRows(panel).nth(rowIndex);
  await row.locator('select[name$="-kind"]').selectOption(kind);
  return row;
};

const recordAttributableConsoleError = (errors, message) => {
  if (
    message.type() === "error" &&
    !message.text().includes("Cross-Origin-Opener-Policy header has been ignored")
  ) {
    errors.push(message.text());
  }
};

const saveDraft = async (page) => {
  await Promise.all([
    page.waitForNavigation({ waitUntil: "domcontentloaded" }),
    page.getByRole("button", { name: "Guardar borrador", exact: true }).click(),
  ]);
  const formErrors = await page.locator(".error-message:visible").allTextContents();
  expect(formErrors).toEqual([]);
};

const submitForReview = async (page) => {
  const actionsToggle = page.locator(
    ".w-dropdown-button:has([name='action-publish']) [data-w-dropdown-target='toggle']",
  );
  await actionsToggle.click();
  return page.locator('[name="action-submit"]:visible');
};


const waitPastAutosaveInterval = async (page) => {
  const form = page.locator("#page-edit-form");
  const configuredInterval = Number(
    await form.getAttribute("data-w-autosave-interval-value"),
  );
  await page.waitForTimeout((configuredInterval || 500) + 250);
};

test("Director completes the native authorship and contextual editorial workflow", async ({
  page,
}) => {
  test.setTimeout(90_000);
  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("console", (message) =>
    recordAttributableConsoleError(pageErrors, message),
  );

  await login(page);
  await openEditor(page, process.env.BROWSER_TEST_PAGE_ID);
  const panel = authorshipPanel(page);
  await expect(
    panel.getByRole("heading", { name: "Autoría y créditos", exact: true }),
  ).toBeVisible();

  const schoolChooser = page.locator("#id_school-chooser");
  await schoolChooser
    .getByRole("button", { name: "Acciones" })
    .click();
  await schoolChooser
    .getByRole("button", { name: "Seleccionar otro Colegio" })
    .click();
  const schoolDialog = page.getByRole("dialog");
  await schoolDialog.locator("#tab-label-create").click();
  await schoolDialog.locator('input[name="name"]').fill("Colegio creado browser");
  await schoolDialog.locator('select[name="department"]').selectOption("04");
  await schoolDialog.getByRole("button", { name: "Crear", exact: true }).click();
  await expect(schoolChooser.locator("[data-chooser-title]")).toHaveText(
    "Colegio creado browser",
  );
  await schoolChooser.getByRole("button", { name: "Acciones" }).click();
  const [schoolEditPage] = await Promise.all([
    page.waitForEvent("popup"),
    schoolChooser.getByRole("link", { name: "Editar este Colegio" }).click(),
  ]);
  await schoolEditPage.locator('input[name="name"]').fill("Colegio editado browser");
  await Promise.all([
    schoolEditPage.waitForNavigation({ waitUntil: "domcontentloaded" }),
    schoolEditPage.getByRole("button", { name: "Guardar", exact: true }).click(),
  ]);
  await expect(
    schoolEditPage.getByText("Colegio editado browser", { exact: true }),
  ).toBeVisible();
  await schoolEditPage.close();

  const firstRow = attributionRows(panel).first();
  await firstRow.locator('select[name$="-kind"]').selectOption("AUTHOR");
  await expect(firstRow.locator('input[name$="-display_name"]')).toBeHidden();
  await expect(firstRow.locator('[id$="-minor_contributor-chooser"]')).toBeHidden();
  await firstRow
    .getByRole("button", { name: "Seleccionar Perfil público de autor" })
    .click();
  const chooser = page.getByRole("dialog");
  await expect(chooser).toBeVisible();
  const searchInput = chooser.locator('input[name="q"]');
  await searchInput.fill("Autora browser");
  await chooser
    .getByRole("link", {
      name: "Autora browser ficticia (autora-browser-ficticia)",
      exact: true,
    })
    .click();
  await expect(authorProfileTitle(firstRow)).toHaveText(
    "Autora browser ficticia (autora-browser-ficticia)",
  );

  const createdAuthorRow = await addAttribution(panel, "AUTHOR");
  const editForm = page.locator("#page-edit-form");
  await expect(editForm).toHaveAttribute(
    "data-w-autosave-active-value",
    "false",
  );
  // Cross the configured Wagtail autosave interval deliberately. An incomplete
  // chooser-backed row must not produce a validation request while it is edited.
  await waitPastAutosaveInterval(page);
  await createdAuthorRow
    .getByRole("button", { name: "Seleccionar Perfil público de autor" })
    .click();
  await chooser.locator("#tab-label-create").click();
  await chooser.locator('input[name="display_name"]').fill(
    "Autora creada browser ficticia",
  );
  await expect(chooser.locator('input[name="slug"]')).toHaveCount(0);
  await expect(chooser.locator("#id_photo-chooser")).toBeVisible();
  const photoChooser = chooser.locator("#id_photo-chooser");
  await photoChooser.locator("[data-chooser-action-choose]").click();
  const imageDialog = page
    .locator(".modal")
    .filter({ has: page.locator("a.image-choice") });
  await imageDialog.locator("[data-dismiss='modal']").click();
  await expect(imageDialog).toBeHidden();
  await expect(page.locator(".modal-backdrop")).toHaveCount(1);
  await expect(chooser.locator('input[name="position"]')).toBeEditable();

  await photoChooser.locator("[data-chooser-action-choose]").click();
  await imageDialog
    .locator('a.image-choice[title="Imagen browser ficticia"]')
    .click();
  await expect(photoChooser.locator("[data-chooser-title]")).toHaveText(
    "Imagen browser ficticia",
  );
  await expect(page.locator(".modal-backdrop")).toHaveCount(1);
  await expect(chooser.locator('input[name="position"]')).toBeEditable();
  await chooser.locator('input[name="position"]').fill("Editora");
  await chooser.getByRole("button", { name: "Crear", exact: true }).click();
  await expect(authorProfileTitle(createdAuthorRow)).toHaveText(
    "Autora creada browser ficticia (autora-creada-browser-ficticia)",
  );
  await expect(editForm).not.toHaveAttribute(
    "data-w-autosave-active-value",
    "false",
  );

  const creditRow = await addAttribution(panel, "PUBLIC_CREDIT");
  await creditRow.locator('input[name$="-display_name"]').fill(
    "Firma browser ordenada",
  );
  const internalRow = await addAttribution(panel, "INTERNAL_CONTRIBUTOR");
  await expect(editForm).toHaveAttribute(
    "data-w-autosave-active-value",
    "false",
  );
  await waitPastAutosaveInterval(page);
  await internalRow
    .getByRole("button", { name: "Seleccionar Colaborador menor" })
    .click();
  const minorSearch = chooser.locator('input[name="q"]');
  await expect(
    chooser.getByRole("link", {
      name: "Colaborador interno browser ficticio",
      exact: true,
    }),
  ).toBeVisible();
  await minorSearch.fill("interno");
  await expect(
    chooser.getByRole("link", {
      name: "Colaborador interno browser ficticio",
      exact: true,
    }),
  ).toBeVisible();
  await minorSearch.fill("");
  await expect(
    chooser.getByRole("link", {
      name: "Colaborador interno browser ficticio",
      exact: true,
    }),
  ).toBeVisible();
  await chooser
    .getByRole("link", { name: "Colaborador interno browser ficticio", exact: true })
    .click();
  await expect(minorContributorTitle(internalRow)).toHaveText(
    "Colaborador interno browser ficticio",
  );
  await expect(editForm).not.toHaveAttribute(
    "data-w-autosave-active-value",
    "false",
  );
  await expect(attributionRows(panel)).toHaveCount(4);
  expect(
    await attributionRows(panel)
      .locator('select[name$="-kind"]')
      .evaluateAll((selects) => selects.map((select) => select.value)),
  ).toEqual(["AUTHOR", "AUTHOR", "PUBLIC_CREDIT", "INTERNAL_CONTRIBUTOR"]);

  await saveDraft(page);
  await openEditor(page, process.env.BROWSER_TEST_PAGE_ID);
  const reopenedRows = attributionRows(panel);
  await expect(attributionRows(panel)).toHaveCount(4);
  const reopenedAuthorRow = reopenedRows.nth(1);
  await expect(authorProfileTitle(reopenedAuthorRow)).toHaveText(
    "Autora creada browser ficticia (autora-creada-browser-ficticia)",
  );

  const createdChooser = reopenedAuthorRow.locator(
    '[id$="-author_profile-chooser"]',
  );
  await createdChooser.getByRole("button", { name: "Acciones" }).click();
  const [editPage] = await Promise.all([
    page.waitForEvent("popup"),
    createdChooser
      .getByRole("link", { name: "Editar este Perfil público de autor" })
      .click(),
  ]);
  await editPage.locator('input[name="display_name"]').fill(
    "Autora editada browser ficticia",
  );
  await Promise.all([
    editPage.waitForNavigation({ waitUntil: "domcontentloaded" }),
    editPage.getByRole("button", { name: "Guardar", exact: true }).click(),
  ]);
  await expect(
    editPage.getByText("Autora editada browser ficticia", { exact: true }),
  ).toBeVisible();
  await editPage.close();
  expect(pageErrors).toEqual([]);
});

test("publication guards distinguish public identity and minor-author privacy", async ({
  page,
}) => {
  test.setTimeout(60_000);
  await login(page);

  for (const pageId of [
    process.env.BROWSER_TEST_AUTHOR_ONLY_PAGE_ID,
    process.env.BROWSER_TEST_CREDIT_ONLY_PAGE_ID,
  ]) {
    await openEditor(page, pageId);
    const submit = await submitForReview(page);
    await Promise.all([
      page.waitForNavigation({ waitUntil: "domcontentloaded" }),
      submit.click(),
    ]);
    await expect(
      page.getByText(
        "Añade al menos un autor o una firma pública antes de publicar la noticia.",
        { exact: true },
      ),
    ).toHaveCount(0);
  }

  await openEditor(page, process.env.BROWSER_TEST_INTERNAL_ONLY_PAGE_ID);
  await (await submitForReview(page)).click();
  await expect(
    page.getByText(
      "Añade al menos un autor o una firma pública antes de publicar la noticia.",
      { exact: true },
    ),
  ).toBeVisible();

  await openEditor(page, process.env.BROWSER_TEST_MINOR_AUTHOR_PAGE_ID);
  await (await submitForReview(page)).click();
  await expect(
    page.getByText(
      "Un autor menor es una exposición pública identificable; marca esta noticia como con menores identificables.",
      { exact: true },
    ),
  ).toBeVisible();
});

test("AuthorProfile identity choosers search and restore their results", async ({
  page,
}) => {
  test.setTimeout(60_000);
  await login(page);
  await page.goto("/admin/snippets/news/authorprofile/add/");

  const userChooser = page.locator("#id_user-chooser");
  await userChooser.locator("[data-chooser-action-choose]").click();
  const userDialog = page.locator(".modal:visible");
  const userSearch = userDialog.locator('input[name="q"]');
  await expect(
    userDialog.getByRole("link", {
      name: "Admin Director (@epic3-006-browser)",
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    userDialog.getByRole("link", {
      name: "Admin SEO (@epic5-009-seo-browser)",
      exact: true,
    }),
  ).toBeVisible();
  await userSearch.fill("director");
  await expect(
    userDialog.getByRole("link", {
      name: "Admin Director (@epic3-006-browser)",
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    userDialog.getByRole("link", {
      name: "Admin SEO (@epic5-009-seo-browser)",
      exact: true,
    }),
  ).toHaveCount(0);
  await userSearch.fill("");
  await expect(
    userDialog.getByRole("link", {
      name: "Admin SEO (@epic5-009-seo-browser)",
      exact: true,
    }),
  ).toBeVisible();
  await userDialog.locator("[data-dismiss='modal']").click();

  const minorChooser = page.locator("#id_minor_contributor-chooser");
  await minorChooser.locator("[data-chooser-action-choose]").click();
  const minorDialog = page.locator(".modal:visible");
  const minorSearch = minorDialog.locator('input[name="q"]');
  await expect(
    minorDialog.getByRole("link", {
      name: "Colaborador interno browser ficticio",
      exact: true,
    }),
  ).toBeVisible();
  await minorSearch.fill("interno");
  await expect(
    minorDialog.getByRole("link", {
      name: "Colaborador interno browser ficticio",
      exact: true,
    }),
  ).toBeVisible();
  await minorSearch.fill("");
  await expect(
    minorDialog.getByRole("link", {
      name: "Colaborador interno browser ficticio",
      exact: true,
    }),
  ).toBeVisible();
});

test("public authorship cards preserve ordered attribution and structured archive state", async ({
  page,
}) => {
  test.setTimeout(60_000);
  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("console", (message) =>
    recordAttributableConsoleError(pageErrors, message),
  );

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/nota-publica-browser-epic6-003/");
  const article = page.locator("article.article-layout");
  await expect(article.locator(".byline")).toHaveText(
    "Por Autora browser ficticia; Redacción pública ficticia; Autora mínima browser ficticia",
  );
  const authorCards = article.locator(".author-card");
  await expect(authorCards).toHaveCount(2);
  await expect(authorCards.first()).toContainText("Periodista");
  await expect(authorCards.first()).toContainText(
    "Biografía pública ficticia para la prueba browser.",
  );
  await expect(authorCards.first().getByRole("link", { name: "Correo" })).toHaveAttribute(
    "href",
    "mailto:autora.browser@example.invalid",
  );
  await expect(authorCards.first().getByRole("link", { name: "Sitio web" })).toHaveAttribute(
    "href",
    "https://example.invalid/autora-browser",
  );
  await expect(authorCards.nth(1).getByRole("link", { name: "Correo" })).toHaveCount(0);
  await expect(authorCards.nth(1).getByRole("link", { name: "Sitio web" })).toHaveCount(0);
  await expect(article).not.toContainText("Colaborador interno browser ficticio");
  await authorCards.first().getByRole("link", { name: "Ver todas sus noticias" }).focus();
  await expect(authorCards.first().getByRole("link", { name: "Ver todas sus noticias" })).toBeFocused();
  await authorCards.first().getByRole("link", { name: "Ver todas sus noticias" }).press("Enter");
  await expect(page).toHaveURL("/noticias/?autor=autora-browser-ficticia");
  await expect(
    page.getByRole("heading", { name: "Noticias de Autora browser ficticia" }),
  ).toBeVisible();
  await expect(page.getByLabel("Autor", { exact: true })).toHaveCount(0);
  await expect(page.locator('input[name="autor"]')).toHaveValue(
    "autora-browser-ficticia",
  );
  await page.locator("#news-section").selectOption("politica");
  await page.getByRole("button", { name: "Buscar", exact: true }).click();
  await expect(page).toHaveURL(/seccion=politica.*autor=autora-browser-ficticia/);
  await expect(page.getByRole("link", { name: "Quitar filtro de autor" })).toBeVisible();
  expect(pageErrors).toEqual([]);
});
