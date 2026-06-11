import { expect, test } from "@playwright/test";

async function expectNoHorizontalOverflow(page) {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow).toBeLessThanOrEqual(1);
}

test("mobile home navigation and tools remain in the viewport", async ({ page }) => {
  await page.goto("./");
  await expect(page.getByText("ATC 7110.65", { exact: true })).toBeVisible();
  await expectNoHorizontalOverflow(page);

  await page.getByRole("button", { name: /Tools/ }).click();
  await expect(page.getByRole("button", { name: "Export Progress" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Import Progress" })).toBeVisible();
  await expectNoHorizontalOverflow(page);
});

test("learner progress can be exported and imported", async ({ page }) => {
  await page.goto("./");
  await page.getByRole("button", { name: /Tools/ }).click();
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export Progress" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/^atc-study-progress-\d{4}-\d{2}-\d{2}\.json$/);

  await page.getByRole("button", { name: /Tools/ }).click();
  const chooserPromise = page.waitForEvent("filechooser");
  await page.getByRole("button", { name: "Import Progress" }).click();
  const chooser = await chooserPromise;
  page.once("dialog", (dialog) => dialog.accept());
  await chooser.setFiles({
    name: "progress.json",
    mimeType: "application/json",
    buffer: Buffer.from(JSON.stringify({
      type: "atc-7110-study-progress",
      version: 1,
      data: {},
    })),
  });
  await expect(page.getByText("ATC 7110.65", { exact: true })).toBeVisible();
});

test("aircraft controls use the mobile container", async ({ page }) => {
  await page.goto("./");
  await page.getByRole("button", { name: /Aircraft Recognition/ }).click();
  await expect(page.getByText("Build focused decks", { exact: false })).toBeVisible();
  await expectNoHorizontalOverflow(page);

  const selects = page.locator(".map-aircraft-filter-grid select");
  await expect(selects.first()).toBeVisible();
  const widths = await selects.evaluateAll((items) => items.map((item) => ({
    control: item.getBoundingClientRect().width,
    parent: item.parentElement.getBoundingClientRect().width,
  })));
  for (const width of widths) {
    expect(width.control).toBeGreaterThan(width.parent * 0.8);
  }
});

test("chapter sections expose distinct drill, card, and section actions", async ({ page }) => {
  await page.goto("./");
  await page.getByText(/Chapter 1 — General/).first().click();
  await expect(page.getByRole("button", { name: "Drill" }).first()).toBeVisible();
  await expect(page.getByRole("button", { name: "Cards" }).first()).toBeVisible();
  await expect(page.getByRole("button", { name: "Open" }).first()).toBeVisible();
  await expectNoHorizontalOverflow(page);
});

test("installed shell reloads offline after the first controlled visit", async ({ page, context }) => {
  await page.goto("./");
  await page.evaluate(() => navigator.serviceWorker.ready);
  await page.waitForFunction(() => Boolean(navigator.serviceWorker.controller));
  await expect(page.getByText("ATC 7110.65", { exact: true })).toBeVisible();

  await context.setOffline(true);
  await page.reload();
  await expect(page.getByText("ATC 7110.65", { exact: true })).toBeVisible();
});
