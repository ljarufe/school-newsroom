const { expect, test } = require("@playwright/test");

const branch = (page, name) =>
  page.locator(`[data-news-taxonomy-branch][data-root-name="${name}"]`);

const rootCheckbox = (page, name) =>
  branch(page, name).locator(":scope > .news-taxonomy-tree__row--root input");

const subsectionCheckbox = (page, rootName, subsectionName) =>
  branch(page, rootName)
    .locator(".news-taxonomy-tree__row--child", { hasText: subsectionName })
    .locator("input");

const disclosure = (page, name) =>
  branch(page, name).locator("[data-news-taxonomy-disclosure]");

const saveDraft = async (page) => {
  await Promise.all([
    page.waitForNavigation({ waitUntil: "domcontentloaded" }),
    page.getByRole("button", { name: "Guardar borrador", exact: true }).click(),
  ]);
};

test("taxonomy tree keeps explicit selections independent and revision-aware", async ({
  page,
}) => {
  test.setTimeout(60_000);
  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));

  await page.goto("/admin/login/");
  await page.locator("#id_username").fill(process.env.BROWSER_TEST_USERNAME);
  await page.locator("#id_password").fill(process.env.BROWSER_TEST_PASSWORD);
  await page.locator('button[type="submit"]').click();
  await page.goto(`/admin/pages/${process.env.BROWSER_TEST_PAGE_ID}/edit/`);

  const tree = page.locator("[data-news-taxonomy-tree]");
  const cultureDisclosure = disclosure(page, "Cultura");
  const politicsDisclosure = disclosure(page, "Política");
  const privacyCheckbox = page.getByRole("checkbox", {
    name: "Contiene menores identificables",
  });

  await expect(tree).toBeVisible();
  await expect(tree.locator("[data-news-taxonomy-branch]")).toHaveCount(6);
  await expect(cultureDisclosure).toHaveAttribute("aria-expanded", "false");
  await expect(cultureDisclosure).toHaveAttribute(
    "aria-label",
    "Mostrar subsecciones de Cultura",
  );
  await expect(politicsDisclosure).toHaveAttribute("aria-expanded", "false");
  await expect(branch(page, "Cultura").locator(".news-taxonomy-tree__children")).toBeHidden();
  await expect(privacyCheckbox).not.toBeChecked();

  await cultureDisclosure.click();
  await expect(cultureDisclosure).toHaveAttribute("aria-expanded", "true");
  await expect(rootCheckbox(page, "Cultura")).not.toBeChecked();
  const music = subsectionCheckbox(page, "Cultura", "Música");
  await music.check();
  await expect(music).toBeChecked();
  await expect(rootCheckbox(page, "Cultura")).not.toBeChecked();

  const interviewsDisclosure = disclosure(page, "Entrevistas");
  await interviewsDisclosure.click();
  await rootCheckbox(page, "Entrevistas").check();
  const community = subsectionCheckbox(page, "Entrevistas", "Comunidad");
  await community.check();
  await expect(rootCheckbox(page, "Entrevistas")).toBeChecked();
  await expect(community).toBeChecked();

  await interviewsDisclosure.focus();
  await interviewsDisclosure.press("Space");
  await expect(interviewsDisclosure).toHaveAttribute("aria-expanded", "false");
  await interviewsDisclosure.press("Enter");
  await expect(interviewsDisclosure).toHaveAttribute("aria-expanded", "true");
  await page.keyboard.press("Tab");
  await expect(rootCheckbox(page, "Entrevistas")).toBeFocused();
  await expect(privacyCheckbox).not.toBeChecked();

  await saveDraft(page);
  await expect(cultureDisclosure).toHaveAttribute("aria-expanded", "true");
  await expect(cultureDisclosure).toHaveAttribute(
    "aria-label",
    "Ocultar subsecciones de Cultura",
  );
  await expect(interviewsDisclosure).toHaveAttribute("aria-expanded", "true");
  await expect(music).toBeChecked();
  await expect(rootCheckbox(page, "Cultura")).not.toBeChecked();
  await expect(rootCheckbox(page, "Entrevistas")).toBeChecked();
  await expect(community).toBeChecked();

  await community.uncheck();
  await saveDraft(page);
  await expect(community).not.toBeChecked();
  await expect(music).toBeChecked();
  await expect(rootCheckbox(page, "Entrevistas")).toBeChecked();

  await music.uncheck();
  await rootCheckbox(page, "Entrevistas").uncheck();
  await saveDraft(page);
  await expect(music).not.toBeChecked();
  await expect(rootCheckbox(page, "Entrevistas")).not.toBeChecked();
  await expect(community).not.toBeChecked();

  const invalidControls = await page
    .locator("[data-edit-form] :invalid")
    .evaluateAll((controls) =>
      controls.map((control) => ({
        name: control.getAttribute("name"),
        type: control.getAttribute("type"),
      })),
    );
  expect(invalidControls).toEqual([]);

  const publishButton = page.locator('[name="action-publish"]');
  const actionsToggle = page.locator(
    ".w-dropdown-button:has([name='action-publish']) [data-w-dropdown-target='toggle']",
  );
  await expect(publishButton).toHaveAttribute("type", "submit");
  await expect(publishButton).toBeHidden();
  await actionsToggle.click();
  await expect(publishButton).toBeVisible();
  await Promise.all([
    page.waitForNavigation({ waitUntil: "domcontentloaded" }),
    publishButton.click(),
  ]);
  await expect(
    page
      .getByText(
        "Selecciona al menos una sección o subsección antes de publicar la noticia.",
        { exact: true },
      )
      .first(),
  ).toBeVisible();
  await expect(page.locator("[data-news-taxonomy-error='true']")).toBeVisible();
  await expect(politicsDisclosure).toHaveAttribute("aria-expanded", "true");
  await expect(privacyCheckbox).not.toBeChecked();
  expect(pageErrors).toEqual([]);
});

test("taxonomy management surfaces and public detail keep their distinct contracts", async ({
  page,
}) => {
  test.setTimeout(60_000);
  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));

  await page.goto("/admin/login/");
  await page.locator("#id_username").fill(process.env.BROWSER_TEST_USERNAME);
  await page.locator("#id_password").fill(process.env.BROWSER_TEST_PASSWORD);
  await page.locator('button[type="submit"]').click();
  await page.waitForURL((url) => !url.pathname.endsWith("/login/"));

  const editorialMenu = page.getByRole("button", {
    name: "Editorial",
    exact: true,
  });
  const sectionsLink = page.getByRole("link", {
    name: "Secciones",
    exact: true,
  });
  const subsectionsLink = page.getByRole("link", {
    name: "Subsecciones",
    exact: true,
  });

  await expect(editorialMenu).toHaveAttribute("aria-expanded", "false");
  await expect(sectionsLink).toBeHidden();
  await expect(subsectionsLink).toBeHidden();
  await editorialMenu.click();
  await expect(editorialMenu).toHaveAttribute("aria-expanded", "true");
  await expect(sectionsLink).toBeVisible();
  await expect(subsectionsLink).toBeVisible();
  await expect(sectionsLink).toHaveAttribute(
    "href",
    "/admin/snippets/news/newssection/",
  );
  await expect(subsectionsLink).toHaveAttribute(
    "href",
    "/admin/news/subsections/",
  );

  await sectionsLink.click();
  const addSectionLink = page.getByRole("link", {
    name: "Añadir sección",
    exact: true,
  });
  await expect(addSectionLink).toBeVisible();
  await expect(
    page.getByRole("link", {
      name: "Añadir Sección editorial",
      exact: true,
    }),
  ).toHaveCount(0);
  await addSectionLink.click();
  await expect(page).toHaveURL("/admin/snippets/news/newssection/add/");
  await expect(
    page.getByRole("heading", { name: "Sección", exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("textbox", { name: /^Nombre/ })).toBeVisible();
  await expect(page.getByRole("textbox", { name: /^Slug/ })).toBeVisible();
  await expect(page.getByRole("spinbutton", { name: /^Orden/ })).toBeVisible();
  await expect(
    page.getByRole("combobox", { name: "Sección principal" }),
  ).toHaveCount(0);

  await page.goto("/admin/");
  await editorialMenu.click();
  await subsectionsLink.click();
  const addSubsectionLink = page.getByRole("link", {
    name: "Añadir subsección",
    exact: true,
  });
  await expect(addSubsectionLink).toBeVisible();
  await expect(
    page.getByRole("link", {
      name: "Añadir Sección editorial",
      exact: true,
    }),
  ).toHaveCount(0);
  await addSubsectionLink.click();
  await expect(page).toHaveURL("/admin/news/subsections/new/");
  await expect(
    page.getByRole("heading", { name: "Subsección", exact: true }),
  ).toBeVisible();
  const parentSelector = page.getByRole("combobox", {
    name: "Sección principal",
  });
  await expect(parentSelector).toBeVisible();
  await expect(
    parentSelector.getByRole("option", { name: "Política", exact: true }),
  ).toHaveCount(1);
  await expect(
    parentSelector.getByRole("option", { name: "Cultura", exact: true }),
  ).toHaveCount(1);
  await expect(
    parentSelector.getByRole("option", { name: "Música", exact: true }),
  ).toHaveCount(0);
  await expect(
    parentSelector.getByRole("option", {
      name: "Arte y literatura",
      exact: true,
    }),
  ).toHaveCount(0);

  await page.goto(`/admin/pages/${process.env.BROWSER_TEST_PAGE_ID}/edit/`);
  const cultureDisclosure = disclosure(page, "Cultura");
  await expect(cultureDisclosure).toHaveAttribute("aria-expanded", "false");
  await cultureDisclosure.click();
  await subsectionCheckbox(page, "Cultura", "Música").check();

  const publishButton = page.locator('[name="action-publish"]');
  const actionsToggle = page.locator(
    ".w-dropdown-button:has([name='action-publish']) [data-w-dropdown-target='toggle']",
  );
  await actionsToggle.click();
  await expect(publishButton).toBeVisible();
  await Promise.all([
    page.waitForNavigation({ waitUntil: "domcontentloaded" }),
    publishButton.click(),
  ]);

  await page.goto("/nota-browser-epic3-006/");
  await expect(page.locator(".article-header .eyebrow")).toHaveText(
    "Cultura › Música",
  );
  await expect(
    page.getByText("Secciones y subsecciones", { exact: true }),
  ).toHaveCount(0);
  expect(pageErrors).toEqual([]);
});
