const { expect, test } = require("@playwright/test");

const login = async (page) => {
  await page.goto("/admin/login/");
  await page.locator("#id_username").fill(process.env.BROWSER_TEST_USERNAME);
  await page.locator("#id_password").fill(process.env.BROWSER_TEST_PASSWORD);
  await page.locator('button[type="submit"]').click();
  await page.waitForURL((url) => !url.pathname.endsWith("/login/"));
};

const chooseDistrict = async (page, search, name) => {
  const district = page.getByRole("combobox", { name: "Distrito", exact: true });
  await district.fill(search);
  await expect(
    page
      .locator("[data-district-results]")
      .getByRole("option", { name, exact: true }),
  ).toBeVisible();
  await district.press("ArrowDown");
  await district.press("Enter");
  return district;
};

test("School and News coverage use the same dependent district interaction", async ({
  page,
}) => {
  test.setTimeout(90_000);
  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  await login(page);

  await page.getByRole("button", { name: "Editorial", exact: true }).click();
  await page.getByRole("link", { name: "Colegios", exact: true }).click();
  await page
    .getByRole("link", {
      name: "Colegio browser distrital ficticio",
      exact: true,
    })
    .click();
  const schoolDepartment = page.locator('select[name="department"]');
  const schoolDistrict = page.getByRole("combobox", {
    name: "Distrito",
    exact: true,
  });
  await expect(schoolDepartment).toHaveValue("04");
  await expect(schoolDistrict).toHaveValue("Cayma");
  await schoolDepartment.selectOption("15");
  await expect(schoolDistrict).toHaveValue("");
  await expect(page.locator('input[name="district"]')).toHaveValue("");
  await chooseDistrict(page, "lim", "Lima");
  await expect(page.locator('input[name="district"]')).toHaveValue("150101");
  await Promise.all([
    page.waitForNavigation({ waitUntil: "domcontentloaded" }),
    page.getByRole("button", { name: "Guardar", exact: true }).click(),
  ]);
  await page
    .getByRole("link", {
      name: "Colegio browser distrital ficticio",
      exact: true,
    })
    .click();
  await expect(page.locator('select[name="department"]')).toHaveValue("15");
  await expect(
    page.getByRole("combobox", { name: "Distrito", exact: true }),
  ).toHaveValue("Lima");

  await page.goto(`/admin/pages/${process.env.BROWSER_TEST_PAGE_ID}/edit/`);
  const coverageDepartment = page.locator(
    'select[name="coverage_department"]',
  );
  const coverageDistrict = page.getByRole("combobox", {
    name: "Distrito",
    exact: true,
  });
  await expect(coverageDepartment).toHaveValue("04");
  await expect(coverageDistrict).toHaveValue("Arequipa");
  await coverageDepartment.selectOption("15");
  await expect(coverageDistrict).toHaveValue("");
  await chooseDistrict(page, "lim", "Lima");
  await Promise.all([
    page.waitForNavigation({ waitUntil: "domcontentloaded" }),
    page.getByRole("button", { name: "Guardar borrador", exact: true }).click(),
  ]);
  await expect(
    page.locator('select[name="coverage_department"]'),
  ).toHaveValue("15");
  await expect(
    page.getByRole("combobox", { name: "Distrito", exact: true }),
  ).toHaveValue("Lima");

  await page.setViewportSize({ width: 390, height: 844 });
  await expect(
    page.getByRole("combobox", { name: "Distrito", exact: true }),
  ).toBeVisible();
  expect(pageErrors).toEqual([]);
});
