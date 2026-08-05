const { expect, test } = require("@playwright/test");

const publicPath = "/nota-publica-browser-epic6-003/";
const canonical =
  "https://example.org/noticia-ficticia" +
  "?origen=school-newsroom&grupo=A%20%26%20B";
const socialTitle = 'Aprendizajes <ficticios> "A & B"';
const socialDescription =
  "Una comunidad ficticia comparte aprendizajes de un taller " +
  "escolar sin incluir datos reales de menores.";

const openScenario = async (page, scenario) => {
  await page.goto(`${publicPath}?shareMock=${scenario}`);
  const share = page.locator("[data-public-share]");
  return {
    share,
    nativeButton: share.getByRole("button", {
      name: "Compartir",
      exact: true,
    }),
    copyButton: share.getByRole("button", {
      name: "Copiar enlace",
      exact: true,
    }),
    notification: share.locator("[data-share-notification]"),
    status: share.locator("[data-share-status]"),
    closeButton: share.getByRole("button", { name: "Cerrar", exact: true }),
    manualFallback: share.locator("[data-share-manual-fallback]"),
    manualUrl: share.locator("[data-share-manual-url]"),
  };
};

test("public news share actions detect support and manage transient feedback", async ({
  page,
}) => {
  test.setTimeout(60_000);
  const pageErrors = [];
  const warnings = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "warning") {
      warnings.push(message.text());
    }
  });

  await page.addInitScript(() => {
    const scenario =
      new URL(window.location.href).searchParams.get("shareMock") ||
      "supported";
    const nativeMode = scenario === "supported" ? "success" : scenario;
    const originalSetTimeout = window.setTimeout.bind(window);
    const originalClearTimeout = window.clearTimeout.bind(window);
    const notificationTimers = new Map();
    let nextTimerId = 100_000;

    window.__publicShareMock = {
      nativeMode,
      clipboardMode: "success",
      payloads: [],
      copyAttempts: [],
      copied: [],
      latestNotificationTimerId: null,
      notificationTimers,
      runNotificationTimer(timerId) {
        notificationTimers.get(timerId)?.callback();
      },
      runAllNotificationTimers() {
        notificationTimers.forEach((timer) => timer.callback());
      },
    };

    window.setTimeout = (callback, delay, ...args) => {
      if (delay !== 5000) {
        return originalSetTimeout(callback, delay, ...args);
      }
      const timerId = nextTimerId;
      nextTimerId += 1;
      notificationTimers.set(timerId, {
        callback: () => callback(...args),
        cleared: false,
      });
      window.__publicShareMock.latestNotificationTimerId = timerId;
      return timerId;
    };
    window.clearTimeout = (timerId) => {
      const timer = notificationTimers.get(timerId);
      if (timer) {
        timer.cleared = true;
        return;
      }
      originalClearTimeout(timerId);
    };

    const share = async (payload) => {
      window.__publicShareMock.payloads.push({ ...payload });
      if (window.__publicShareMock.nativeMode === "abort") {
        throw new DOMException("Cancelled by browser test", "AbortError");
      }
      if (window.__publicShareMock.nativeMode === "failure") {
        throw new DOMException("Denied by browser test", "NotAllowedError");
      }
    };
    Object.defineProperty(navigator, "share", {
      configurable: true,
      value: scenario === "absent" ? undefined : share,
    });
    Object.defineProperty(navigator, "canShare", {
      configurable: true,
      value:
        scenario === "absent"
          ? undefined
          : () => {
              if (scenario === "can-share-throws") {
                throw new DOMException(
                  "canShare failed in browser test",
                  "NotAllowedError",
                );
              }
              return scenario !== "unshareable";
            },
    });
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: {
        writeText: async (value) => {
          window.__publicShareMock.copyAttempts.push(value);
          if (window.__publicShareMock.clipboardMode === "failure") {
            throw new DOMException(
              "Clipboard denied by browser test",
              "NotAllowedError",
            );
          }
          window.__publicShareMock.copied.push(value);
        },
      },
    });
  });

  let controls = await openScenario(page, "supported");

  await test.step("render supported Web Share first with unchanged link contracts", async () => {
    await expect(
      controls.share.getByRole("heading", {
        name: "Compartir esta noticia",
        level: 2,
      }),
    ).toHaveClass("public-share__heading");
    await expect(controls.nativeButton).toBeVisible();
    await expect(controls.copyButton).toBeVisible();
    await expect(controls.notification).toBeHidden();
    await expect(page.locator('meta[name="robots"]')).toHaveAttribute(
      "content",
      "noindex, follow",
    );

    const channels = await controls.share
      .locator("[data-share-channel]")
      .evaluateAll((elements) =>
        elements.map((element) => element.dataset.shareChannel),
      );
    expect(channels).toEqual([
      "native",
      "whatsapp",
      "x",
      "facebook",
      "email",
      "copy",
    ]);

    const expectedLinks = {
      whatsapp: {
        origin: "https://wa.me",
        pathname: "/",
        query: { text: `${socialTitle}\n${canonical}` },
      },
      x: {
        origin: "https://x.com",
        pathname: "/intent/tweet",
        query: { text: socialTitle, url: canonical },
      },
      facebook: {
        origin: "https://www.facebook.com",
        pathname: "/sharer/sharer.php",
        query: { u: canonical },
      },
    };
    for (const [channel, expected] of Object.entries(expectedLinks)) {
      const link = controls.share.locator(
        `[data-share-channel="${channel}"]`,
      );
      const parsed = new URL(await link.getAttribute("href"));
      expect(parsed.origin).toBe(expected.origin);
      expect(parsed.pathname).toBe(expected.pathname);
      expect(Object.fromEntries(parsed.searchParams)).toEqual(expected.query);
      await expect(link).toHaveAttribute("target", "_blank");
      expect(new Set((await link.getAttribute("rel")).split(" "))).toEqual(
        new Set(["noopener", "noreferrer"]),
      );
    }
    const email = new URL(
      await controls.share
        .locator('[data-share-channel="email"]')
        .getAttribute("href"),
    );
    expect(email.protocol).toBe("mailto:");
    expect(Object.fromEntries(email.searchParams)).toEqual({
      subject: socialTitle,
      body: `${socialDescription}\r\n\r\n${canonical}`,
    });

    await controls.nativeButton.click();
    await expect
      .poll(() =>
        page.evaluate(() => window.__publicShareMock.payloads.length),
      )
      .toBe(1);
    expect(
      await page.evaluate(() => window.__publicShareMock.payloads[0]),
    ).toEqual({
      title: socialTitle,
      text: socialDescription,
      url: canonical,
    });
    await expect(controls.notification).toBeHidden();
  });

  await test.step("remove unsupported or unshareable native controls without side effects", async () => {
    controls = await openScenario(page, "absent");
    await expect(controls.nativeButton).toHaveCount(0);
    await expect(controls.copyButton).toBeVisible();
    expect(
      await page.evaluate(() => window.__publicShareMock.copyAttempts),
    ).toEqual([]);
    await controls.copyButton.click();
    await expect(controls.status).toHaveText("Enlace copiado.");
    expect(
      await page.evaluate(() => window.__publicShareMock.copied),
    ).toEqual([canonical]);

    const warningsBeforeUnshareable = warnings.length;
    controls = await openScenario(page, "unshareable");
    await expect(controls.nativeButton).toHaveCount(0);
    await expect(controls.notification).toBeHidden();
    expect(warnings).toHaveLength(warningsBeforeUnshareable);
    expect(
      await page.evaluate(() => window.__publicShareMock.copyAttempts),
    ).toEqual([]);

    const errorsBeforeCanShareFailure = pageErrors.length;
    const warningsBeforeCanShareFailure = warnings.length;
    controls = await openScenario(page, "can-share-throws");
    await expect(controls.nativeButton).toHaveCount(0);
    await expect(controls.notification).toBeHidden();
    expect(pageErrors).toHaveLength(errorsBeforeCanShareFailure);
    expect(warnings).toHaveLength(warningsBeforeCanShareFailure);
  });

  controls = await openScenario(page, "supported");

  await test.step("keep AbortError silent", async () => {
    const warningCount = warnings.length;
    await page.evaluate(() => {
      window.__publicShareMock.nativeMode = "abort";
    });
    await controls.nativeButton.click();
    await expect
      .poll(() =>
        page.evaluate(() => window.__publicShareMock.payloads.length),
      )
      .toBe(1);
    await expect(controls.notification).toBeHidden();
    expect(warnings).toHaveLength(warningCount);
    expect(
      await page.evaluate(() => window.__publicShareMock.copyAttempts),
    ).toEqual([]);
  });

  await test.step("auto-dismiss combined native failure feedback deterministically", async () => {
    await page.evaluate(() => {
      window.__publicShareMock.nativeMode = "failure";
      window.__publicShareMock.clipboardMode = "success";
    });
    await controls.nativeButton.click();
    await expect(controls.notification).toBeVisible();
    await expect(controls.status).toHaveText(
      "No se pudo abrir el menú para compartir. Enlace copiado.",
    );
    expect(
      await page.evaluate(() => window.__publicShareMock.copied.at(-1)),
    ).toBe(canonical);
    const timerId = await page.evaluate(
      () => window.__publicShareMock.latestNotificationTimerId,
    );
    await page.evaluate(
      (id) => window.__publicShareMock.runNotificationTimer(id),
      timerId,
    );
    await expect(controls.notification).toBeHidden();
    expect(warnings.at(-1)).toBe(
      "public-share:native-failed NotAllowedError",
    );
    expect(warnings.at(-1)).not.toContain(canonical);
  });

  await test.step("support keyboard copy, visible close, and notification replacement", async () => {
    await page.evaluate(() => {
      window.__publicShareMock.clipboardMode = "success";
    });
    await controls.copyButton.focus();
    await controls.copyButton.press("Enter");
    await expect(controls.copyButton).toBeFocused();
    await expect(controls.notification).toBeVisible();
    await expect(controls.status).toHaveText("Enlace copiado.");
    await expect(controls.closeButton).toBeVisible();
    const earlierTimerId = await page.evaluate(
      () => window.__publicShareMock.latestNotificationTimerId,
    );

    await page.evaluate(() => {
      window.__publicShareMock.nativeMode = "failure";
    });
    await controls.nativeButton.click();
    await expect(controls.status).toHaveText(
      "No se pudo abrir el menú para compartir. Enlace copiado.",
    );
    await page.evaluate(
      (id) => window.__publicShareMock.runNotificationTimer(id),
      earlierTimerId,
    );
    await expect(controls.notification).toBeVisible();
    await expect(controls.status).toHaveText(
      "No se pudo abrir el menú para compartir. Enlace copiado.",
    );

    await controls.closeButton.focus();
    await expect(controls.closeButton).toBeFocused();
    await controls.closeButton.press("Enter");
    await expect(controls.notification).toBeHidden();
  });

  await test.step("keep direct manual-copy failure visible until closed", async () => {
    await page.evaluate(() => {
      window.__publicShareMock.clipboardMode = "failure";
    });
    await controls.copyButton.click();
    await expect(controls.notification).toBeVisible();
    await expect(controls.status).toHaveText(
      "No se pudo copiar automáticamente. Selecciona y copia este enlace.",
    );
    await expect(controls.manualFallback).toBeVisible();
    await expect(controls.manualUrl).toHaveAttribute("readonly", "");
    await expect(controls.manualUrl).toHaveValue(canonical);
    await expect(controls.manualUrl).toBeFocused();
    expect(
      await controls.manualUrl.evaluate(
        (input) =>
          input.selectionStart === 0 &&
          input.selectionEnd === input.value.length,
      ),
    ).toBe(true);
    await page.evaluate(() =>
      window.__publicShareMock.runAllNotificationTimers(),
    );
    await expect(controls.notification).toBeVisible();

    await page.setViewportSize({ width: 320, height: 720 });
    expect(
      await page.evaluate(
        () =>
          document.documentElement.scrollWidth <=
          document.documentElement.clientWidth,
      ),
    ).toBe(true);
    await page.keyboard.press("Shift+Tab");
    await expect(controls.closeButton).toBeFocused();
    expect(
      await controls.closeButton.evaluate((button) => {
        const style = window.getComputedStyle(button);
        return style.outlineStyle !== "none" && style.outlineWidth !== "0px";
      }),
    ).toBe(true);
    await controls.closeButton.press("Enter");
    await expect(controls.notification).toBeHidden();
    await expect(controls.manualFallback).toBeHidden();
    await expect(controls.status).toBeEmpty();
    expect(
      await controls.manualUrl.evaluate(
        (input) => input.selectionStart === 0 && input.selectionEnd === 0,
      ),
    ).toBe(true);
  });

  await test.step("combine native and Clipboard failures without auto-dismiss", async () => {
    await page.setViewportSize({ width: 1280, height: 720 });
    await page.evaluate(() => {
      window.__publicShareMock.nativeMode = "failure";
      window.__publicShareMock.clipboardMode = "failure";
    });
    await controls.nativeButton.click();
    await expect(controls.notification).toBeVisible();
    await expect(controls.status).toHaveText(
      "No se pudo abrir el menú para compartir. Selecciona y copia este enlace.",
    );
    await expect(controls.manualUrl).toBeFocused();
    await page.evaluate(() =>
      window.__publicShareMock.runAllNotificationTimers(),
    );
    await expect(controls.notification).toBeVisible();
    await controls.closeButton.click();
    await expect(controls.notification).toBeHidden();
  });

  expect(pageErrors).toEqual([]);
  expect(
    warnings.every(
      (warning) =>
        !warning.includes(canonical) &&
        !warning.includes(socialTitle) &&
        !warning.includes(socialDescription),
    ),
  ).toBe(true);
});
