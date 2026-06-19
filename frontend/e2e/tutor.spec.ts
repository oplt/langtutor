import { test, expect } from "@playwright/test";

const MOCK_USER = {
  id: "00000000-0000-4000-8000-000000000001",
  email: "tutor-e2e@example.com",
  full_name: "Tutor E2E",
};

test.describe("tutor chat", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem("access_token", "playwright-test-token");
      localStorage.setItem("access_token_persist", "1");

      class MockWebSocket {
        static CONNECTING = 0;
        static OPEN = 1;
        static CLOSING = 2;
        static CLOSED = 3;
        static instances: MockWebSocket[] = [];
        url: string;
        protocols?: string | string[];
        readyState = 0;
        onopen: (() => void) | null = null;
        onclose: (() => void) | null = null;
        onerror: (() => void) | null = null;
        onmessage: ((event: { data: string }) => void) | null = null;

        constructor(url: string, protocols?: string | string[]) {
          this.url = url;
          this.protocols = protocols;
          MockWebSocket.instances.push(this);
          window.setTimeout(() => {
            this.readyState = 1;
            this.onopen?.();
          }, 0);
        }

        send(data: string) {
          const payload = JSON.parse(data) as { type: string };
          const emit = (body: Record<string, unknown>) => {
            this.onmessage?.({ data: JSON.stringify(body) });
          };

          if (payload.type === "ping") {
            emit({ type: "pong" });
            return;
          }

          if (payload.type === "message") {
            window.setTimeout(() => {
              emit({
                type: "turn_started",
                turn_id: "turn-e2e-1",
                session_id: "session-e2e-1",
              });
            }, 10);
            window.setTimeout(() => {
              emit({
                type: "event",
                turn_id: "turn-e2e-1",
                session_id: "session-e2e-1",
                seq: 1,
                event: { type: "content", content: "Hoi!" },
              });
            }, 30);
            window.setTimeout(() => {
              emit({
                type: "event",
                turn_id: "turn-e2e-1",
                session_id: "session-e2e-1",
                seq: 2,
                event: { type: "done" },
              });
            }, 50);
            window.setTimeout(() => {
              emit({
                type: "turn_done",
                turn_id: "turn-e2e-1",
                session_id: "session-e2e-1",
              });
            }, 70);
          }
        }

        close() {
          this.readyState = 3;
          this.onclose?.();
        }
      }

      // @ts-expect-error test shim
      window.WebSocket = MockWebSocket;
    });

    await page.route("**/auth/me", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_USER),
      });
    });

    await page.route("**/api/learning/levels", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          levels: [
            {
              level: "A1",
              rank_min: 0,
              rank_max: 100,
              word_coverage: "core",
              grammar_focus: "basics",
              input_type: "text",
              word_count: 500,
            },
          ],
        }),
      });
    });

    await page.route("**/api/learning/progress/summary", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          total_words: 0,
          mastered_words: 0,
          next_review_at: null,
          levels: [],
        }),
      });
    });
  });

  test("user can send a tutor message and receive a streamed reply", async ({ page }) => {
    await page.goto("/dashboard/coach");
    await expect(page.getByRole("heading", { name: "Dutch AI Tutor" })).toBeVisible();
    await expect(page.locator("span.MuiChip-label", { hasText: /^Connected$/ })).toBeVisible({
      timeout: 10_000,
    });

    const input = page.getByPlaceholder(/ask for a simpler version/i);
    await input.fill("Hallo tutor");
    await page.getByRole("button", { name: "Send message" }).click();

    await expect(page.getByText("Hallo tutor")).toBeVisible();
    await expect(page.getByText(/Hoi!/)).toBeVisible({ timeout: 10_000 });
  });
});
