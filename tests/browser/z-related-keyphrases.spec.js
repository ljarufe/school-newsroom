const { expect, test } = require("@playwright/test");

const saveDraft = async (page) => {
  await Promise.all([
    page.waitForNavigation({ waitUntil: "domcontentloaded" }),
    page.getByRole("button", { name: "Guardar borrador", exact: true }).click(),
  ]);
};

test("SEO curator manages related keyphrases without other editorial access", async ({
  page,
}) => {
  test.setTimeout(60_000);
  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));

  await page.goto("/admin/login/");
  await page.locator("#id_username").fill(process.env.BROWSER_TEST_SEO_USERNAME);
  await page.locator("#id_password").fill(process.env.BROWSER_TEST_SEO_PASSWORD);
  await page.locator('button[type="submit"]').click();
  await page.goto(`/admin/pages/${process.env.BROWSER_TEST_SEO_PAGE_ID}/edit/`);

  await expect(
    page.getByRole("tab", { name: "Asistente SEO", exact: true }),
  ).toBeVisible();
  const visibleTabPanel = page.locator('[role="tabpanel"]:visible');
  await expect(
    visibleTabPanel.getByRole("heading", { level: 2 }).first(),
  ).toHaveText("Configuración SEO");
  await expect(
    page.getByText("Contexto de la noticia — solo lectura", { exact: true }),
  ).toHaveCount(0);
  await expect(page.locator('[data-side-panel-toggle="preview"]')).toBeVisible();
  await expect(page.locator('[name="body"]')).toHaveCount(0);
  await expect(page.locator('[name="taxonomy_sections"]')).toHaveCount(0);

  const addButton = page.getByRole("button", {
    name: "Añadir Frase clave relacionada",
    exact: true,
  });
  const relatedInputs = page.locator(
    'input[name^="related_keyphrases-"][name$="-phrase"]:visible',
  );
  const phrases = [
    "investigación escolar",
    "noticia escolar",
    "jóvenes reporteros",
    "redacción periodística",
  ];

  for (const phrase of phrases) {
    await addButton.click();
    await relatedInputs.last().fill(phrase);
  }
  await expect(relatedInputs).toHaveCount(4);
  await expect(addButton).toBeDisabled();

  const children = page.locator("[data-inline-panel-child]");
  await children
    .nth(3)
    .locator("[data-inline-panel-child-move-up]")
    .click();
  await children.nth(3).locator('button[title="Eliminar"]').click();
  await expect(relatedInputs).toHaveCount(3);

  await saveDraft(page);
  await expect(relatedInputs).toHaveCount(3);
  await expect(relatedInputs.nth(0)).toHaveValue("investigación escolar");
  await expect(relatedInputs.nth(1)).toHaveValue("noticia escolar");
  await expect(relatedInputs.nth(2)).toHaveValue("redacción periodística");

  await expect(
    page.getByRole("heading", {
      name: "Análisis de frases relacionadas",
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "investigación escolar", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "noticia escolar", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Análisis lingüístico no disponible", { exact: true }),
  ).toHaveCount(0);
  await expect(
    page.locator('[data-linguistic-finding="related-0-presence"]'),
  ).toContainText("Coincidencia exacta");
  await expect(
    page.locator('[data-linguistic-finding="related-1-presence"]'),
  ).toContainText("Variante flexiva");
  await expect(
    page.getByRole("heading", { name: "Legibilidad avanzada", exact: true }),
  ).toBeVisible();
  const connectorFinding = page.locator(
    '[data-advanced-readability-finding="connectors"]',
  );
  await expect(connectorFinding).toContainText("Uso de conectores — Correcto");
  await expect(connectorFinding).toContainText("1 de 5 oraciones (20 %)");
  await expect(connectorFinding).toContainText("Párrafo 1 (body:0:0)");
  await expect(connectorFinding).toContainText("Además, el borrador ficticio");
  await expect(page.locator('[name="body"]')).toHaveCount(0);
  await expect(page.locator('[name="taxonomy_sections"]')).toHaveCount(0);
  expect(pageErrors).toEqual([]);

  await page.goto("/admin/");
});
