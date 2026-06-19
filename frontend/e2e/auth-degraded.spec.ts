import { test, expect } from "@playwright/test";

test("dashboard tutor route requires authentication", async ({ page }) => {
  await page.goto("/dashboard/coach");
  await expect(page).toHaveURL(/#auth/);
  await expect(page.getByRole("textbox", { name: "Email", exact: true })).toBeVisible();
});

test("session degraded banner appears when profile refresh fails", async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("access_token", "playwright-test-token");
    localStorage.setItem("access_token_persist", "1");
  });

  await page.route("**/auth/me", async (route) => {
    await route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ detail: "upstream unavailable" }),
    });
  });

  await page.goto("/dashboard");
  await expect(
    page.getByText(/could not refresh your profile/i),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Retry" })).toBeVisible();
});
