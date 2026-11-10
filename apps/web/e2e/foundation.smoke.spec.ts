import { expect, test } from "@playwright/test";

test("renders NEXTRADE AI foundation baseline and connectivity panel", async ({ page }) => {
  await page.goto("/");

  await expect(page).toHaveTitle(/NEXTRADE AI/);
  await expect(
    page.getByRole("heading", { name: /Infrastructure and Connectivity Verified/i }),
  ).toBeVisible();
  await expect(
    page.getByText(/Research & decision-support architecture only/i),
  ).toBeVisible();
  await expect(page.getByText(/FastAPI Gateway/i)).toBeVisible();
  await expect(page.getByText("PostgreSQL", { exact: true })).toBeVisible();
  await expect(page.getByText("Redis", { exact: true })).toBeVisible();

  const statusText = await page.getByRole("status").textContent();
  expect(statusText?.trim().length ?? 0).toBeGreaterThan(0);

  if (process.env.EXPECT_HEALTHY_STACK === "true") {
    await expect(page.getByText("Operational")).toBeVisible();
  }
});

