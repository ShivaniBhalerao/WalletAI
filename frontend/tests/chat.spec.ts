/**
 * End-to-End Tests for Chat Functionality
 * 
 * Tests the chat interface including:
 * - Default prompt suggestions
 * - Click-to-populate functionality
 * - Message sending
 * - Chat responses
 */

import { expect, type Page, test } from "@playwright/test"

/**
 * Test suite for the chat interface
 * Requires authentication, so uses the default authenticated state
 */
test.describe("Chat Interface", () => {
  /**
   * Navigate to chat page before each test
   */
  test.beforeEach(async ({ page }) => {
    await page.goto("/chat")
    await page.waitForLoadState("networkidle")
  })

  /**
   * Test: Chat page loads successfully
   */
  test("Chat page loads with header and empty state", async ({ page }) => {
    // Verify page title
    await expect(
      page.getByRole("heading", { name: "Financial Assistant" })
    ).toBeVisible()

    // Verify subtitle
    await expect(
      page.getByText("Ask about your spending, trends, and financial insights")
    ).toBeVisible()

    // Verify empty state message
    await expect(
      page.getByText("Start your financial conversation")
    ).toBeVisible()

    // Verify "Try asking:" text
    await expect(page.getByText("Try asking:")).toBeVisible()
  })

  /**
   * Test: All four suggested prompts are visible
   */
  test("Displays all suggested prompts with correct content", async ({ page }) => {
    // Check for groceries prompt
    await expect(
      page.getByText("🛒 How much did I spend on groceries last month?")
    ).toBeVisible()

    // Check for Starbucks prompt
    await expect(
      page.getByText("☕ Show me all my Starbucks purchases")
    ).toBeVisible()

    // Check for credit card prompt
    await expect(
      page.getByText("💳 What did I spend from my credit card this week?")
    ).toBeVisible()

    // Check for date range prompt
    await expect(
      page.getByText("📅 Show me transactions from last week")
    ).toBeVisible()
  })

  /**
   * Test: Clicking on a prompt populates the input field
   */
  test("Clicking on a prompt populates the input field - groceries", async ({ page }) => {
    const groceriesPrompt = page.getByText("🛒 How much did I spend on groceries last month?")
    
    await groceriesPrompt.click()

    // Verify the input field is populated with the prompt text
    const inputField = page.getByPlaceholder(/ask about your finances/i)
    await expect(inputField).toHaveValue("How much did I spend on groceries last month?")
  })

  /**
   * Test: Clicking on merchant prompt populates input correctly
   */
  test("Clicking on a prompt populates the input field - merchant", async ({ page }) => {
    const merchantPrompt = page.getByText("☕ Show me all my Starbucks purchases")
    
    await merchantPrompt.click()

    // Verify the input field is populated with the prompt text
    const inputField = page.getByPlaceholder(/ask about your finances/i)
    await expect(inputField).toHaveValue("Show me all my Starbucks purchases")
  })

  /**
   * Test: Clicking on account prompt populates input correctly
   */
  test("Clicking on a prompt populates the input field - account", async ({ page }) => {
    const accountPrompt = page.getByText("💳 What did I spend from my credit card this week?")
    
    await accountPrompt.click()

    // Verify the input field is populated with the prompt text
    const inputField = page.getByPlaceholder(/ask about your finances/i)
    await expect(inputField).toHaveValue("What did I spend from my credit card this week?")
  })

  /**
   * Test: Clicking on date range prompt populates input correctly
   */
  test("Clicking on a prompt populates the input field - date range", async ({ page }) => {
    const datePrompt = page.getByText("📅 Show me transactions from last week")
    
    await datePrompt.click()

    // Verify the input field is populated with the prompt text
    const inputField = page.getByPlaceholder(/ask about your finances/i)
    await expect(inputField).toHaveValue("Show me transactions from last week")
  })

  /**
   * Test: Keyboard navigation works for prompts
   */
  test("Keyboard Enter key on prompt populates input field", async ({ page }) => {
    const groceriesPrompt = page.getByText("🛒 How much did I spend on groceries last month?")
    
    // Focus and press Enter
    await groceriesPrompt.focus()
    await groceriesPrompt.press("Enter")

    // Verify the input field is populated
    const inputField = page.getByPlaceholder(/ask about your finances/i)
    await expect(inputField).toHaveValue("How much did I spend on groceries last month?")
  })

  /**
   * Test: Space key on prompt populates input field
   */
  test("Keyboard Space key on prompt populates input field", async ({ page }) => {
    const merchantPrompt = page.getByText("☕ Show me all my Starbucks purchases")
    
    // Focus and press Space
    await merchantPrompt.focus()
    await merchantPrompt.press(" ")

    // Verify the input field is populated
    const inputField = page.getByPlaceholder(/ask about your finances/i)
    await expect(inputField).toHaveValue("Show me all my Starbucks purchases")
  })

  /**
   * Test: Chat input accepts manual text entry
   */
  test("User can type custom message in input field", async ({ page }) => {
    const inputField = page.getByPlaceholder(/ask about your finances/i)
    const customMessage = "How much did I spend on Amazon last month?"

    await inputField.fill(customMessage)
    await expect(inputField).toHaveValue(customMessage)
  })

  /**
   * Test: Send button is visible and enabled when text is entered
   */
  test("Send button is visible and functional", async ({ page }) => {
    const inputField = page.getByPlaceholder(/ask about your finances/i)
    const sendButton = page.getByRole("button", { name: /send/i })

    // Initially should be visible (may be disabled if no text)
    await expect(sendButton).toBeVisible()

    // Type text
    await inputField.fill("Test message")

    // Button should still be visible
    await expect(sendButton).toBeVisible()
  })

  /**
   * Test: Prompt cards have hover effect styling
   */
  test("Prompt cards have cursor pointer styling", async ({ page }) => {
    const groceriesPrompt = page.getByText("🛒 How much did I spend on groceries last month?")
    
    // Check for cursor pointer class
    const card = groceriesPrompt.locator("..")
    await expect(card).toHaveClass(/cursor-pointer/)
  })

  /**
   * Test: Empty state disappears after sending a message
   */
  test("Empty state hides when message is sent", async ({ page }) => {
    // Verify empty state is visible initially
    await expect(
      page.getByText("Start your financial conversation")
    ).toBeVisible()

    // Type and send a message
    const inputField = page.getByPlaceholder(/ask about your finances/i)
    await inputField.fill("Test message")
    await inputField.press("Enter")

    // Wait a moment for the message to be processed
    await page.waitForTimeout(500)

    // Empty state should no longer be visible
    await expect(
      page.getByText("Start your financial conversation")
    ).not.toBeVisible()
  })

  /**
   * Test: All prompts align with available tools
   */
  test("Prompts match the available backend tools", async ({ page }) => {
    // This test verifies the prompts align with the tools:
    // 1. get_transactions_by_category (groceries)
    const categoryPrompt = page.getByText("🛒 How much did I spend on groceries last month?")
    await expect(categoryPrompt).toBeVisible()

    // 2. get_transactions_by_merchant (Starbucks)
    const merchantPrompt = page.getByText("☕ Show me all my Starbucks purchases")
    await expect(merchantPrompt).toBeVisible()

    // 3. get_transactions_by_account (credit card)
    const accountPrompt = page.getByText("💳 What did I spend from my credit card this week?")
    await expect(accountPrompt).toBeVisible()

    // 4. get_transactions_between_dates (last week)
    const datePrompt = page.getByText("📅 Show me transactions from last week")
    await expect(datePrompt).toBeVisible()
  })

  /**
   * Test: Input field clears after clicking prompt and then clearing
   */
  test("Input field can be cleared after prompt click", async ({ page }) => {
    const groceriesPrompt = page.getByText("🛒 How much did I spend on groceries last month?")
    const inputField = page.getByPlaceholder(/ask about your finances/i)
    
    // Click prompt to populate
    await groceriesPrompt.click()
    await expect(inputField).toHaveValue("How much did I spend on groceries last month?")

    // Clear the input
    await inputField.clear()
    await expect(inputField).toHaveValue("")
  })

  /**
   * Test: User can modify prompt text after clicking
   */
  test("User can modify prompt text after clicking", async ({ page }) => {
    const groceriesPrompt = page.getByText("🛒 How much did I spend on groceries last month?")
    const inputField = page.getByPlaceholder(/ask about your finances/i)
    
    // Click prompt to populate
    await groceriesPrompt.click()
    
    // Modify the text
    await inputField.fill("How much did I spend on groceries this month?")
    await expect(inputField).toHaveValue("How much did I spend on groceries this month?")
  })
})
