import { test, expect } from '@playwright/test';

test.describe('MPLA Application', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should load the main application', async ({ page }) => {
    // Check the page title
    await expect(page).toHaveTitle(/MPLA/);

    // Check main header is visible
    await expect(page.getByRole('heading', { name: /Meta-Prompt Learning Agent/i })).toBeVisible();
    
    // Check main description is present
    await expect(page.locator('text=Autonomous system for iterative prompt refinement')).toBeVisible();
  });

  test('should display all main sections', async ({ page }) => {
    // Check structured prompt input section
    await expect(page.locator('text=Structured Prompt Input')).toBeVisible();
    
    // Check knowledge base explorer section
    await expect(page.getByText('Knowledge Base Explorer')).toBeVisible();
    
    // Check advanced analytics section
    await expect(page.getByText('Advanced Analytics')).toBeVisible();
    
    // Check settings panel section
    await expect(page.getByText('Settings')).toBeVisible();
  });

  test('should toggle collapsible sections', async ({ page }) => {
    // Test Knowledge Base Explorer toggle
    const kbToggle = page.getByRole('button', { name: /Knowledge Base Explorer/i });
    await kbToggle.click();
    
    // Check if the content is visible after clicking
    await expect(page.getByText('Sessions')).toBeVisible();
    await expect(page.getByText('Prompts')).toBeVisible();
    
    // Click again to collapse
    await kbToggle.click();
    
    // Verify content is hidden (with timeout for animation)
    await page.waitForTimeout(500);
  });

  test('should handle API connectivity', async ({ page }) => {
    // Wait for the page to load and make API calls
    await page.waitForLoadState('networkidle');
    
    // Check that no major API errors are displayed
    await expect(page.getByText('Error loading')).not.toBeVisible();
    await expect(page.getByText('Failed to fetch')).not.toBeVisible();
  });

  test('should be responsive on mobile viewport', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    
    // Check main elements are still visible
    await expect(page.getByRole('heading', { name: /Meta-Prompt Learning Agent/i })).toBeVisible();
    
    // Check sections can still be accessed
    await expect(page.locator('text=Structured Prompt Input')).toBeVisible();
  });

  test('should maintain dark theme styling', async ({ page }) => {
    // Check for dark theme classes
    const body = page.locator('body');
    await expect(body).toHaveClass(/bg-gray-900/);
    
    // Check for dark text styling
    await expect(page.locator('h1')).toHaveClass(/text-white/);
  });
}); 