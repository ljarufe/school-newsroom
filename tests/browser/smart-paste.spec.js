const { expect, test } = require("@playwright/test");

const visibleBlocks = (writingMode) =>
  writingMode.locator("[data-streamfield-child]:visible");

const blockTypes = async (writingMode) =>
  visibleBlocks(writingMode)
    .locator(':scope input[type="hidden"][name$="-type"]')
    .evaluateAll((inputs) => inputs.map((input) => input.value));

const blockValue = async (block) =>
  JSON.parse(
    await block.locator('input[type="hidden"][name$="-value"]').inputValue(),
  );

const dispatchPaste = async (
  target,
  { html = "", text = "", observeNativeBoundary = false },
) =>
  target.evaluate(
    (element, clipboardSource) => {
      let preventedBeforeNative = null;
      if (clipboardSource.observeNativeBoundary) {
        element.addEventListener(
          "paste",
          (event) => {
            preventedBeforeNative = event.defaultPrevented;
          },
          { capture: true, once: true },
        );
      }
      const clipboard = new DataTransfer();
      if (clipboardSource.html) {
        clipboard.setData("text/html", clipboardSource.html);
      }
      if (clipboardSource.text) {
        clipboard.setData("text/plain", clipboardSource.text);
      }
      const event = new ClipboardEvent("paste", {
        bubbles: true,
        cancelable: true,
        clipboardData: clipboard,
      });
      element.dispatchEvent(event);
      return {
        defaultPrevented: event.defaultPrevented,
        preventedBeforeNative,
      };
    },
    { html, text, observeNativeBoundary },
  );

const setCaretAtEnd = (editor) =>
  editor.evaluate((element) => {
    element.focus();
    const range = document.createRange();
    range.selectNodeContents(element);
    range.collapse(false);
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
  });

const persistentBodyState = (writingMode) =>
  writingMode.evaluate((root) =>
    Array.from(root.querySelectorAll("[data-streamfield-child]:not([hidden])"))
      .map((block) => {
        const value = block.querySelector(
          'input[type="hidden"][name$="-value"]',
        )?.value;
        let normalizedValue = value;
        try {
          const parsed = JSON.parse(value);
          if (Array.isArray(parsed.blocks)) {
            normalizedValue = {
              blocks: parsed.blocks.map((draftBlock) => ({
                data: draftBlock.data || {},
                depth: draftBlock.depth,
                entityRanges: draftBlock.entityRanges,
                inlineStyleRanges: draftBlock.inlineStyleRanges,
                text: draftBlock.text,
                type: draftBlock.type,
              })),
              entityMap: parsed.entityMap,
            };
          } else {
            normalizedValue = parsed;
          }
        } catch (error) {
          // Non-JSON values remain comparable as their exact strings.
        }
        return {
          type: block.querySelector(
            'input[type="hidden"][name$="-type"]',
          )?.value,
          value: normalizedValue,
        };
      }),
  );

const tableBlocks = (writingMode) =>
  writingMode.locator(
    '[data-streamfield-child][data-news-block-type="table"]:visible',
  );

const firstTableCell = (tableBlock) =>
  tableBlock.locator(".ht_master tbody tr").first().locator("td").first();

test("direct smart paste preserves content and contextual table editing", async ({
  page,
}) => {
  test.setTimeout(90_000);
  const pageErrors = [];
  let normalizeRequests = 0;
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("request", (request) => {
    if (request.url().includes("/admin/news/smart-paste/normalize/")) {
      normalizeRequests += 1;
    }
  });

  await page.goto("/admin/login/");
  await page.locator("#id_username").fill(process.env.BROWSER_TEST_USERNAME);
  await page.locator("#id_password").fill(process.env.BROWSER_TEST_PASSWORD);
  await page.locator('button[type="submit"]').click();
  await page.goto(`/admin/pages/${process.env.BROWSER_TEST_PAGE_ID}/edit/`);

  await expect(
    page.getByRole("button", { name: "Pegar nota como bloques" }),
  ).toHaveCount(0);
  await expect(page.locator("[data-news-smart-paste-panel]")).toHaveCount(0);

  await page.getByRole("button", { name: "Abrir modo redacción" }).click();
  const writingMode = page.locator("[data-news-writing-mode]");
  const writingDocument = writingMode.locator(".news-writing-mode__document");
  const notice = writingMode.locator("[data-news-smart-paste-notice]");
  await expect(writingMode).toBeVisible();
  await expect(visibleBlocks(writingMode)).toHaveCount(4);

  // An actually empty StreamField receives structured content at index zero.
  await writingMode.evaluate((root) => {
    const container = root.querySelector(
      "[data-streamfield-stream-container]",
    );
    window.__epic3006OriginalState = container.parentElement.rootBlock.getState();
    container.parentElement.rootBlock.setState([]);
  });
  await expect(visibleBlocks(writingMode)).toHaveCount(0);
  const emptyBodyPaste = await dispatchPaste(writingDocument, {
    text: "Inicio vacío uno.\nInicio vacío dos.",
  });
  expect(emptyBodyPaste.defaultPrevented).toBe(true);
  await expect(visibleBlocks(writingMode)).toHaveCount(2);
  expect(await blockTypes(writingMode)).toEqual(["paragraph", "paragraph"]);
  await writingMode.evaluate((root) => {
    const container = root.querySelector(
      "[data-streamfield-stream-container]",
    );
    container.parentElement.rootBlock.setState(
      window.__epic3006OriginalState,
    );
    delete window.__epic3006OriginalState;
  });
  await expect(visibleBlocks(writingMode)).toHaveCount(4);

  const selectedBlock = visibleBlocks(writingMode).nth(1);
  const selectedEditor = selectedBlock.locator('[contenteditable="true"]');
  await selectedEditor.click();
  await expect(selectedBlock).toHaveAttribute(
    "data-news-block-selected",
    "true",
  );

  // A response from a closed writing-mode session must not survive a reopen.
  const stateBeforeStalePaste = await persistentBodyState(writingMode);
  let releaseStaleResponse;
  let markStaleRequestSeen;
  const staleResponseRelease = new Promise((resolve) => {
    releaseStaleResponse = resolve;
  });
  const staleRequestSeen = new Promise((resolve) => {
    markStaleRequestSeen = resolve;
  });
  await page.route(
    "**/admin/news/smart-paste/normalize/",
    async (route) => {
      markStaleRequestSeen();
      await staleResponseRelease;
      await route.continue();
    },
    { times: 1 },
  );
  await setCaretAtEnd(selectedEditor);
  const stalePaste = await dispatchPaste(selectedEditor, {
    text: "Solicitud antigua uno.\nSolicitud antigua dos.",
  });
  expect(stalePaste.defaultPrevented).toBe(true);
  await staleRequestSeen;
  await writingMode.locator("[data-news-writing-exit]").click();
  await expect(page.locator(".news-writing-dialog")).toBeHidden();
  await page.getByRole("button", { name: "Abrir modo redacción" }).click();
  await expect(writingMode).toBeVisible();
  await expect(page.locator("[data-news-writing-open]")).toHaveAttribute(
    "aria-expanded",
    "true",
  );
  const staleNetworkResponse = page.waitForResponse(
    (response) =>
      response.url().includes("/admin/news/smart-paste/normalize/") &&
      response.status() === 200,
  );
  releaseStaleResponse();
  await staleNetworkResponse;
  await page.evaluate(
    () =>
      new Promise((resolve) => {
        window.requestAnimationFrame(resolve);
      }),
  );
  await expect
    .poll(() => persistentBodyState(writingMode))
    .toEqual(stateBeforeStalePaste);
  await expect(notice).toBeHidden();

  const structuredHtml = [
    "<span><b style='font-weight: normal'>",
    "<h2>Primer título importado</h2>",
    "<h3>Segundo título importado</h3>",
    "<p>Primer párrafo con <strong>negrita real</strong>.</p>",
    "<p>Segundo párrafo con <em>cursiva real</em>.</p>",
    "<ul><li>Primera viñeta</li><li>Segunda viñeta</li></ul>",
    "<table>",
    "<tr><th>Valle / variedad</th><th>Quebranta</th>",
    "<th>Italia</th><th>Moscatel</th></tr>",
    "<tr><td>Vítor</td><td>120 000 L</td><td>42 000 L</td>",
    "<td>18 000 L</td></tr>",
    "<tr><td>Majes</td><td>95 000 L</td><td>51 000 L</td>",
    "<td>22 000 L</td></tr>",
    "<tr><td>Caravelí</td><td>70 000 L</td><td>33 000 L</td>",
    "<td>27 000 L</td></tr>",
    "</table>",
    "<table>",
    "<tr><th colspan='3'>Resumen de campaña 2026</th></tr>",
    "<tr><th>Valle</th><th>Mes</th><th>Producción</th></tr>",
    "<tr><td rowspan='2'>Vítor</td><td>Enero</td>",
    "<td>120 000 L</td></tr>",
    "<tr><td>Febrero</td><td>130 000 L</td></tr>",
    "</table>",
    "<table><tr><th>Dato</th><th>Detalle</th></tr>",
    "<tr><td>Control de calidad</td><td>",
    "<table><tr><td>Aroma</td><td>Aprobado</td></tr>",
    "<tr><td>Sabor</td><td>Aprobado</td></tr></table>",
    "</td></tr></table>",
    "</b></span>",
  ].join("");
  await setCaretAtEnd(selectedEditor);
  const requestsBeforeStructuredPaste = normalizeRequests;
  const structuredPaste = await dispatchPaste(selectedEditor, {
    html: structuredHtml,
    text: [
      "Primer título importado",
      "Segundo título importado",
      "Primer párrafo con negrita real.",
      "Segundo párrafo con cursiva real.",
      "Primera viñeta",
      "Segunda viñeta",
      "Valle / variedad Quebranta Italia Moscatel",
    ].join("\n"),
  });
  expect(structuredPaste.defaultPrevented).toBe(true);
  await expect(visibleBlocks(writingMode)).toHaveCount(12);
  expect(normalizeRequests - requestsBeforeStructuredPaste).toBe(1);
  await expect(notice).toContainText("Se pegaron 8 bloques.");
  await expect(notice).toContainText("Una tabla fue simplificada.");
  expect(await blockTypes(writingMode)).toEqual([
    "paragraph",
    "paragraph",
    "paragraph",
    "paragraph",
    "paragraph",
    "paragraph",
    "paragraph",
    "table",
    "table",
    "table",
    "paragraph",
    "paragraph",
  ]);

  const insertedH2 = visibleBlocks(writingMode).nth(2);
  const insertedH3 = visibleBlocks(writingMode).nth(3);
  const firstInsertedParagraph = visibleBlocks(writingMode).nth(4);
  const secondInsertedParagraph = visibleBlocks(writingMode).nth(5);
  const insertedList = visibleBlocks(writingMode).nth(6);
  const h2State = await blockValue(insertedH2);
  const h3State = await blockValue(insertedH3);
  const firstParagraphState = await blockValue(firstInsertedParagraph);
  const secondParagraphState = await blockValue(secondInsertedParagraph);
  const listState = await blockValue(insertedList);
  expect(h2State.blocks).toHaveLength(1);
  expect(h2State.blocks[0]).toMatchObject({
    type: "header-two",
    text: "Primer título importado",
  });
  expect(h3State.blocks).toHaveLength(1);
  expect(h3State.blocks[0]).toMatchObject({
    type: "header-three",
    text: "Segundo título importado",
  });
  expect(firstParagraphState.blocks).toHaveLength(1);
  expect(firstParagraphState.blocks[0]).toMatchObject({
    text: "Primer párrafo con negrita real.",
  });
  expect(firstParagraphState.blocks[0].inlineStyleRanges).toEqual(
    expect.arrayContaining([expect.objectContaining({ style: "BOLD" })]),
  );
  expect(secondParagraphState.blocks).toHaveLength(1);
  expect(secondParagraphState.blocks[0]).toMatchObject({
    text: "Segundo párrafo con cursiva real.",
  });
  expect(secondParagraphState.blocks[0].inlineStyleRanges).toEqual(
    expect.arrayContaining([expect.objectContaining({ style: "ITALIC" })]),
  );
  expect(listState.blocks).toMatchObject([
    { type: "unordered-list-item", text: "Primera viñeta" },
    { type: "unordered-list-item", text: "Segunda viñeta" },
  ]);

  await expect(tableBlocks(writingMode)).toHaveCount(3);
  for (const table of await tableBlocks(writingMode).all()) {
    await expect(table.locator(".handsontable").first()).toBeVisible();
    await expect(
      table.locator('label[for$="-table-header-choice"]'),
    ).toBeHidden();
    await expect(table.locator(".w-panel__heading")).toBeHidden();
  }

  const firstTable = tableBlocks(writingMode).nth(0);
  const secondTable = tableBlocks(writingMode).nth(1);
  const thirdTable = tableBlocks(writingMode).nth(2);
  await firstTableCell(firstTable).focus();
  await expect(firstTable).toHaveAttribute("data-news-table-expanded", "true");
  await insertedH2.locator('[contenteditable="true"]').click();
  await expect(firstTable).toHaveAttribute(
    "data-news-table-expanded",
    "false",
  );
  await firstTableCell(firstTable).click();
  await expect(firstTable).toHaveAttribute("data-news-table-expanded", "true");
  await expect(firstTable.locator(".w-panel__heading")).toBeVisible();
  await expect(
    firstTable.locator('label[for$="-table-header-choice"]'),
  ).toHaveText("Encabezados de tabla");
  await expect(
    firstTable.locator('label[for$="-handsontable-col-caption"]'),
  ).toHaveText("Descripción de la tabla");
  const headerOptions = await firstTable
    .locator('select[id$="-table-header-choice"] option')
    .allTextContents();
  expect(headerOptions.map((option) => option.trim())).toEqual([
    "Selecciona una opción de encabezado",
    "Mostrar la primera fila como encabezado",
    "Mostrar la primera columna como encabezado",
    "Mostrar la primera fila y la primera columna como encabezados",
    "Sin encabezados",
  ]);
  await expect(firstTable.locator(".ht_master td.current")).toBeVisible();

  await firstTableCell(secondTable).click();
  await expect(secondTable).toHaveAttribute(
    "data-news-table-expanded",
    "true",
  );
  await expect(firstTable).toHaveAttribute(
    "data-news-table-expanded",
    "false",
  );
  await expect(
    firstTable.locator('label[for$="-table-header-choice"]'),
  ).toBeHidden();

  const tablePanelBorders = await secondTable
    .locator(":scope > .w-panel")
    .evaluate((panel) => {
      const style = getComputedStyle(panel);
      return {
        top: style.borderTopWidth,
        right: style.borderRightWidth,
        bottom: style.borderBottomWidth,
        left: style.borderLeftWidth,
        background: style.backgroundColor,
      };
    });
  expect(tablePanelBorders).toMatchObject({
    top: "0px",
    right: "0px",
    bottom: "0px",
    left: "2px",
  });
  expect(tablePanelBorders.background).toBe("rgba(0, 0, 0, 0)");

  await page.setViewportSize({ width: 640, height: 900 });
  const narrowTableLayout = await secondTable.evaluate((block) => {
    const contentRect = block
      .querySelector(":scope > .w-panel > .w-panel__content")
      .getBoundingClientRect();
    return Array.from(
      block.querySelectorAll(
        "select[id$='-table-header-choice'], " +
          "input[id$='-handsontable-col-caption']",
      ),
    ).map((control) => {
      const rect = control.getBoundingClientRect();
      return {
        left: rect.left,
        right: rect.right,
        width: rect.width,
        contentLeft: contentRect.left,
        contentRight: contentRect.right,
        contentWidth: contentRect.width,
      };
    });
  });
  expect(narrowTableLayout).toHaveLength(2);
  narrowTableLayout.forEach((control) => {
    expect(control.left).toBeGreaterThanOrEqual(control.contentLeft - 1);
    expect(control.right).toBeLessThanOrEqual(control.contentRight + 1);
    expect(control.width).toBeGreaterThan(control.contentWidth - 16);
  });
  await page.setViewportSize({ width: 1280, height: 720 });

  await insertedH2.locator('[contenteditable="true"]').click();
  const headingPanelBorders = await insertedH2
    .locator(":scope > .w-panel")
    .evaluate((panel) => {
      const style = getComputedStyle(panel);
      return [
        style.borderTopWidth,
        style.borderRightWidth,
        style.borderBottomWidth,
        style.borderLeftWidth,
      ];
    });
  expect(headingPanelBorders).toEqual(["0px", "0px", "0px", "2px"]);

  const lastTextBlock = visibleBlocks(writingMode).last();
  await lastTextBlock.locator('[contenteditable="true"]').click();
  const selectedTextPresentation = await lastTextBlock.evaluate((block) => {
    const panel = block.querySelector(":scope > .w-panel");
    const panelContent = panel.querySelector(":scope > .w-panel__content");
    const editor = block.querySelector(".Draftail-Editor");
    const editorContainer = block.querySelector(".DraftEditor-editorContainer");
    const publicContent = block.querySelector(".public-DraftEditor-content");
    const panelStyle = getComputedStyle(panel);
    return {
      panelBorders: [
        panelStyle.borderTopWidth,
        panelStyle.borderRightWidth,
        panelStyle.borderBottomWidth,
        panelStyle.borderLeftWidth,
      ],
      panelHeight: panel.getBoundingClientRect().height,
      editorHeight: editor.getBoundingClientRect().height,
      editorSlack:
        editorContainer.getBoundingClientRect().height -
        publicContent.getBoundingClientRect().height,
      trailingDecoration: getComputedStyle(panelContent, "::after").content,
    };
  });
  expect(selectedTextPresentation.panelBorders).toEqual([
    "0px",
    "0px",
    "0px",
    "2px",
  ]);
  expect(
    selectedTextPresentation.panelHeight -
      selectedTextPresentation.editorHeight,
  ).toBeLessThanOrEqual(1);
  expect(selectedTextPresentation.editorSlack).toBeLessThan(4);
  expect(selectedTextPresentation.trailingDecoration).toBe("none");

  const paragraphPanelExcess = await writingMode
    .locator('[data-news-block-type="paragraph"]:visible')
    .evaluateAll((blocks) =>
      blocks.map((block) => {
        const panel = block.querySelector(":scope > .w-panel");
        const editor = block.querySelector(".Draftail-Editor");
        return (
          panel.getBoundingClientRect().height -
          editor.getBoundingClientRect().height
        );
      }),
    );
  paragraphPanelExcess.forEach((excess) => {
    expect(excess).toBeLessThanOrEqual(1);
  });

  // One ordinary inline fragment reaches Draftail without smart-paste
  // interception. Draftail handles this synthetic event and persists it.
  const nativeEditor = visibleBlocks(writingMode)
    .nth(0)
    .locator('[contenteditable="true"]');
  await setCaretAtEnd(nativeEditor);
  const requestsBeforeNativePaste = normalizeRequests;
  const nativeInline = await dispatchPaste(nativeEditor, {
    html: "<strong> frase breve nativa</strong>",
    text: " frase breve nativa",
    observeNativeBoundary: true,
  });
  expect(nativeInline.preventedBeforeNative).toBe(false);
  expect(normalizeRequests).toBe(requestsBeforeNativePaste);
  await expect
    .poll(async () => {
      const state = await blockValue(visibleBlocks(writingMode).nth(0));
      return state.blocks.map((block) => block.text).join("");
    })
    .toContain("frase breve nativa");

  // Smart paste also leaves a Handsontable cell untouched. The untrusted
  // synthetic event proves the interception boundary, not browser-native paste.
  const nativeTableCell = await dispatchPaste(firstTableCell(thirdTable), {
    text: "Dato",
    observeNativeBoundary: true,
  });
  expect(nativeTableCell.preventedBeforeNative).toBe(false);

  // Image metadata inputs cross the same non-interception boundary. The
  // temporary invalid block is removed before the fixture is saved.
  await writingMode.evaluate((root) => {
    const container = root.querySelector(
      "[data-streamfield-stream-container]",
    );
    const streamBlock = container.parentElement.rootBlock;
    streamBlock.insert(
      {
        type: "article_image",
        value: {
          image: null,
          caption: "",
          alt_text: "",
          credit: "",
        },
      },
      streamBlock.children.length,
      { animate: false, focus: false },
    );
  });
  const imageBlock = writingMode.locator(
    '[data-streamfield-child][data-news-block-type="article_image"]:visible',
  );
  await expect(imageBlock).toHaveCount(1);
  imageBlock.evaluate((block) => {
    block.dataset.newsBlockSelected = "true";
  });
  const nativeImageInput = await dispatchPaste(
    imageBlock.locator('input[name$="-caption"]'),
    {
      text: "Pie uno\nPie dos",
      observeNativeBoundary: true,
    },
  );
  expect(nativeImageInput.preventedBeforeNative).toBe(false);
  await imageBlock.evaluate((block) => {
    const streamBlock = block
      .closest("[data-streamfield-stream-container]")
      .parentElement.rootBlock;
    streamBlock.children
      .find((child) => child.element === block)
      .delete({ animate: false });
  });
  await expect(imageBlock).toHaveCount(0);
  await expect(visibleBlocks(writingMode)).toHaveCount(12);

  // A completely empty paragraph is replaced rather than retained.
  const emptyParagraph = visibleBlocks(writingMode).nth(10);
  await expect(emptyParagraph.locator('[contenteditable="true"]')).toHaveText(
    "",
  );
  await emptyParagraph.locator('[contenteditable="true"]').click();
  const replacementPaste = await dispatchPaste(
    emptyParagraph.locator('[contenteditable="true"]'),
    {
      text: "Reemplazo uno.\nReemplazo dos.",
    },
  );
  expect(replacementPaste.defaultPrevented).toBe(true);
  await expect(visibleBlocks(writingMode)).toHaveCount(13);
  const bodyTextAfterReplacement = await visibleBlocks(
    writingMode,
  ).allTextContents();
  expect(bodyTextAfterReplacement[10]).toContain("Reemplazo uno.");
  expect(bodyTextAfterReplacement[11]).toContain("Reemplazo dos.");
  expect(bodyTextAfterReplacement[12]).toContain("Bloque posterior.");

  // With no target or selected block, structured content is appended.
  await writingMode.evaluate((root) => {
    root
      .querySelectorAll('[data-news-block-selected="true"]')
      .forEach((block) => {
        block.dataset.newsBlockSelected = "false";
      });
  });
  const fallbackPaste = await dispatchPaste(writingDocument, {
    text: "Final uno.\nFinal dos.",
  });
  expect(fallbackPaste.defaultPrevented).toBe(true);
  await expect(visibleBlocks(writingMode)).toHaveCount(15);
  const bodyTextAfterFallback = await visibleBlocks(
    writingMode,
  ).allTextContents();
  expect(bodyTextAfterFallback.at(-2)).toContain("Final uno.");
  expect(bodyTextAfterFallback.at(-1)).toContain("Final dos.");

  // An endpoint failure does not mutate any existing StreamField state.
  const stateBeforeFailure = await persistentBodyState(writingMode);
  await page.route("**/admin/news/smart-paste/normalize/", (route) =>
    route.fulfill({
      status: 500,
      contentType: "application/json",
      body: JSON.stringify({ error: "Fallo simulado." }),
    }),
  );
  const failurePaste = await dispatchPaste(
    visibleBlocks(writingMode)
      .nth(0)
      .locator('[contenteditable="true"]'),
    {
      text: "No debe entrar uno.\nNo debe entrar dos.",
    },
  );
  expect(failurePaste.defaultPrevented).toBe(true);
  await expect(notice).toContainText(
    "No se pudo procesar el contenido pegado.",
  );
  const stateAfterFailure = await persistentBodyState(writingMode);
  expect(stateAfterFailure).toEqual(stateBeforeFailure);
  await page.unroute("**/admin/news/smart-paste/normalize/");

  const exactTableValue = await blockValue(tableBlocks(writingMode).nth(0));
  expect(exactTableValue).toMatchObject({
    data: [
      ["Valle / variedad", "Quebranta", "Italia", "Moscatel"],
      ["Vítor", "120 000 L", "42 000 L", "18 000 L"],
      ["Majes", "95 000 L", "51 000 L", "22 000 L"],
      ["Caravelí", "70 000 L", "33 000 L", "27 000 L"],
    ],
    table_caption: "",
    table_header_choice: "row",
  });
  const mergedTableValue = await blockValue(tableBlocks(writingMode).nth(1));
  expect(mergedTableValue.data).toEqual([
    ["Resumen de campaña 2026", "", ""],
    ["Valle", "Mes", "Producción"],
    ["Vítor", "Enero", "120 000 L"],
    ["", "Febrero", "130 000 L"],
  ]);

  await writingMode.locator("[data-news-writing-exit]").click();
  await expect(page.locator(".news-writing-dialog")).toBeHidden();
  await Promise.all([
    page.waitForNavigation({ waitUntil: "domcontentloaded" }),
    page.getByRole("button", { name: "Guardar borrador", exact: true }).click(),
  ]);

  await page.getByRole("button", { name: "Abrir modo redacción" }).click();
  await expect(writingMode).toBeVisible();
  await expect(visibleBlocks(writingMode)).toHaveCount(15);
  await expect(tableBlocks(writingMode)).toHaveCount(3);
  expect(await blockTypes(writingMode)).toEqual([
    "paragraph",
    "paragraph",
    "paragraph",
    "paragraph",
    "paragraph",
    "paragraph",
    "paragraph",
    "table",
    "table",
    "table",
    "paragraph",
    "paragraph",
    "paragraph",
    "paragraph",
    "paragraph",
  ]);
  const reopenedText = await visibleBlocks(writingMode).allTextContents();
  expect(reopenedText[0]).toContain("Bloque anterior.");
  expect(reopenedText[0]).toContain("frase breve nativa");
  expect(reopenedText[1]).toContain("Bloque seleccionado.");
  expect(reopenedText[2]).toContain("Primer título importado");
  expect(reopenedText[3]).toContain("Segundo título importado");
  expect(reopenedText[4]).toContain("Primer párrafo con negrita real.");
  expect(reopenedText[5]).toContain("Segundo párrafo con cursiva real.");
  expect(reopenedText[10]).toContain("Reemplazo uno.");
  expect(reopenedText[12]).toContain("Bloque posterior.");
  expect(reopenedText.at(-1)).toContain("Final dos.");

  const reopenedH2 = await blockValue(visibleBlocks(writingMode).nth(2));
  const reopenedH3 = await blockValue(visibleBlocks(writingMode).nth(3));
  const reopenedFirstParagraph = await blockValue(
    visibleBlocks(writingMode).nth(4),
  );
  const reopenedSecondParagraph = await blockValue(
    visibleBlocks(writingMode).nth(5),
  );
  const reopenedList = await blockValue(visibleBlocks(writingMode).nth(6));
  expect(reopenedH2.blocks).toMatchObject([
    { type: "header-two", text: "Primer título importado" },
  ]);
  expect(reopenedH3.blocks).toMatchObject([
    { type: "header-three", text: "Segundo título importado" },
  ]);
  expect(reopenedFirstParagraph.blocks).toHaveLength(1);
  expect(reopenedFirstParagraph.blocks[0]).toMatchObject({
    type: "unstyled",
    text: "Primer párrafo con negrita real.",
  });
  expect(reopenedFirstParagraph.blocks[0].inlineStyleRanges).toEqual(
    expect.arrayContaining([expect.objectContaining({ style: "BOLD" })]),
  );
  expect(reopenedSecondParagraph.blocks).toHaveLength(1);
  expect(reopenedSecondParagraph.blocks[0]).toMatchObject({
    type: "unstyled",
    text: "Segundo párrafo con cursiva real.",
  });
  expect(reopenedSecondParagraph.blocks[0].inlineStyleRanges).toEqual(
    expect.arrayContaining([expect.objectContaining({ style: "ITALIC" })]),
  );
  expect(reopenedList.blocks).toMatchObject([
    { type: "unordered-list-item", text: "Primera viñeta" },
    { type: "unordered-list-item", text: "Segunda viñeta" },
  ]);

  const reopenedExactTable = await blockValue(tableBlocks(writingMode).nth(0));
  expect(reopenedExactTable.data).toEqual(exactTableValue.data);
  expect(reopenedExactTable.table_caption).toBe("");
  for (const table of await tableBlocks(writingMode).all()) {
    await expect(table.locator(".handsontable").first()).toBeVisible();
    await expect(
      table.locator('label[for$="-table-header-choice"]'),
    ).toBeHidden();
  }
  expect(pageErrors).toEqual([]);
});
