const { expect, test } = require("@playwright/test");

test("public news archive search, filters, ordering, and pagination", async ({
  page,
}) => {
  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));

  await page.goto("/");
  const navigationSearch = page.getByRole("link", { name: "Buscar noticias" });
  await expect(navigationSearch).toBeVisible();
  await navigationSearch.focus();
  await expect(navigationSearch).toBeFocused();
  await navigationSearch.press("Enter");
  await expect(page).toHaveURL("/noticias/#buscar-noticias");
  await expect(page.locator("#buscar-noticias")).toBeVisible();

  let districtLookupRequests = 0;
  page.on("request", (request) => {
    if (request.url().includes("/geografia/distritos/")) {
      districtLookupRequests += 1;
    }
  });
  const departmentSelect = page.getByLabel("Departamento", { exact: true });
  const districtSearch = page.getByRole("combobox", {
    name: "Distrito",
    exact: true,
  });
  await expect(districtSearch).toBeDisabled();
  await departmentSelect.selectOption("04");
  await expect(districtSearch).toBeEnabled();
  await districtSearch.fill("ar");
  expect(districtLookupRequests).toBe(0);
  await districtSearch.fill("are");
  const arequipaOption = page
    .locator("[data-district-results]")
    .getByRole("option", {
      name: "Arequipa",
      exact: true,
    });
  await expect(arequipaOption).toBeVisible();
  await districtSearch.press("ArrowDown");
  await districtSearch.press("Enter");
  await expect(page.locator('input[name="distrito"]')).toHaveValue("040101");
  await page.getByRole("button", { name: "Buscar", exact: true }).click();
  await expect(page).toHaveURL(/departamento=04.*distrito=040101/);
  await expect(page.locator(".news-card")).toHaveCount(9);
  await page.goto("/noticias/?departamento=04");
  await expect(page.locator(".news-card")).toHaveCount(10);
  await expect(page.getByText("Archivo browser 0", { exact: true })).toBeVisible();
  await expect(page.getByText("Archivo browser 1", { exact: true })).toHaveCount(0);

  await page.goto("/noticias/");

  const sectionSelect = page.locator("#news-section");
  const subsectionSelect = page.locator("#news-subsection");
  const musicOption = subsectionSelect.locator('option[value="musica"]');
  const localPoliticsOption = subsectionSelect.locator(
    'option[value="politica-local"]',
  );
  await sectionSelect.selectOption("cultura");
  await expect(musicOption).toHaveText("Música");
  await expect(musicOption).toHaveJSProperty("hidden", false);
  await expect(localPoliticsOption).toHaveJSProperty("hidden", true);
  await subsectionSelect.selectOption("musica");
  await sectionSelect.selectOption("politica");
  await expect(subsectionSelect).toHaveValue("");
  await sectionSelect.selectOption("");
  await subsectionSelect.selectOption("musica");
  await page.getByRole("button", { name: "Buscar", exact: true }).click();
  await expect(page).toHaveURL(/subseccion=musica/);
  await expect(page.locator(".news-card")).toHaveCount(1);

  await page.goto("/nota-publica-browser-epic6-003/");
  await expect(page.locator('a[href="/noticias/?departamento=15"]')).toHaveText(
    "Lima",
  );
  await expect(
    page.locator(
      'a[href="/noticias/?departamento=15&distrito=150101"]',
    ),
  ).toHaveText("Lima");
  const article = page.locator("article");
  await expect(
    article.locator('a[href="/noticias/?seccion=politica"]'),
  ).toHaveText("Política");
  await expect(
    article.locator(
      'a[href="/noticias/?seccion=politica&subseccion=politica-local"]',
    ),
  ).toHaveText("Política local");
  await page.getByRole("link", { name: "#browser-share", exact: true }).click();
  await expect(page).toHaveURL("/noticias/?etiqueta=browser-share");

  await page.goto("/noticias/?etiqueta=archivo-browser");
  await expect(page.getByRole("heading", { name: "Noticias", exact: true })).toBeVisible();
  await expect(page.locator(".news-card")).toHaveCount(10);
  await expect(page.getByRole("link", { name: "Siguiente", exact: true })).toHaveAttribute(
    "href",
    /etiqueta=archivo-browser/,
  );

  await page.goto("/noticias/?seccion=cultura");
  await expect(page.getByText("11 resultados", { exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Siguiente", exact: true })).toHaveAttribute(
    "href",
    /seccion=cultura/,
  );

  await page.goto("/noticias/?subseccion=musica");
  await expect(page.locator(".news-card")).toHaveCount(1);
  await expect(page.locator(".news-card").first()).toContainText("Archivo browser 0");

  await page.goto(
    "/noticias/?seccion=cultura&subseccion=musica&etiqueta=archivo-browser",
  );
  await expect(page.locator(".news-card")).toHaveCount(1);
  await expect(page.getByRole("link", { name: "Cambiar el orden cronológico" })).toHaveAttribute(
    "href",
    /seccion=cultura.*subseccion=musica.*etiqueta=archivo-browser.*orden=asc/,
  );

  await page.goto("/noticias/?seccion=cultura&etiqueta=browser-share");
  await expect(
    page.getByRole("heading", {
      name: "Aún no hay noticias publicadas en esta sección.",
    }),
  ).toBeVisible();

  await page.goto("/noticias/?seccion=no-existe");
  await expect(
    page.getByRole("heading", { name: "La sección solicitada no existe." }),
  ).toBeVisible();

  await page.goto("/noticias/?seccion=cultura&subseccion=politica-local");
  await expect(
    page.getByRole("heading", { name: "Los filtros solicitados no son compatibles." }),
  ).toBeVisible();

  await page.goto("/noticias/?etiqueta=archivo-browser");
  await page.getByRole("searchbox", { name: "Buscar" }).fill("Archivo browser");
  await page.getByRole("button", { name: "Buscar", exact: true }).click();
  await expect(page).toHaveURL(/buscar=Archivo\+browser/);
  await expect(page.locator(".news-card")).toHaveCount(10);
  await expect(page.getByRole("link", { name: "Siguiente", exact: true })).toHaveAttribute(
    "href",
    /buscar=Archivo\+browser/,
  );

  await page.getByRole("link", { name: "Cambiar el orden cronológico" }).click();
  await expect(page).toHaveURL(/orden=asc/);
  await expect(page.locator(".news-card").first()).toContainText("Archivo browser 0");
  const nextPage = page.getByRole("link", { name: "Siguiente", exact: true });
  await nextPage.focus();
  await expect(nextPage).toBeFocused();
  await nextPage.press("Enter");
  await expect(page.locator(".news-card")).toHaveCount(1);

  await page.getByRole("link", { name: "Anterior", exact: true }).click();
  await expect(page.getByText("11 resultados", { exact: true })).toBeVisible();
  await expect(page.locator(".news-card")).toHaveCount(10);
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByRole("link", { name: "Siguiente", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Abrir navegación" }).click();
  await expect(page.getByRole("link", { name: "Buscar noticias" })).toBeVisible();
  expect(pageErrors).toEqual([]);
});
