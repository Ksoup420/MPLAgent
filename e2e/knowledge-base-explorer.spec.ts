import { test, expect } from '@playwright/test';

test.describe('Knowledge Base Explorer', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    
    // Expand the Knowledge Base Explorer section
    await page.getByRole('button', { name: /Knowledge Base Explorer/i }).click();
    await page.waitForTimeout(500); // Wait for expansion animation
  });

  test('should display all tabs in the explorer', async ({ page }) => {
    // Check all tab buttons are visible
    await expect(page.getByRole('button', { name: 'Sessions' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Prompts' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Evaluations' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Performance' })).toBeVisible();
  });

  test('should switch between different tabs', async ({ page }) => {
    // Start with Sessions tab (default)
    await expect(page.getByText('Recent Sessions')).toBeVisible();
    
    // Switch to Prompts tab
    await page.getByRole('button', { name: 'Prompts' }).click();
    await expect(page.getByText('Prompt History')).toBeVisible();
    
    // Switch to Evaluations tab
    await page.getByRole('button', { name: 'Evaluations' }).click();
    await expect(page.getByText('Evaluation Results')).toBeVisible();
    
    // Switch to Performance tab
    await page.getByRole('button', { name: 'Performance' }).click();
    await expect(page.getByText('Performance Overview')).toBeVisible();
  });

  test('should display search functionality', async ({ page }) => {
    // Check search input is visible
    await expect(page.getByPlaceholder('Search sessions...')).toBeVisible();
    
    // Test search functionality
    await page.getByPlaceholder('Search sessions...').fill('test query');
    await page.waitForTimeout(500); // Wait for debounce
    
    // Search should filter results (or show "no results" message)
    // The exact behavior depends on available data
  });

  test('should display time-based filters', async ({ page }) => {
    // Check filter buttons are visible
    await expect(page.getByRole('button', { name: 'Today' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Week' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Month' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'All Time' })).toBeVisible();
  });

  test('should apply time filters', async ({ page }) => {
    // Click on different time filters
    await page.getByRole('button', { name: 'Today' }).click();
    await page.waitForLoadState('networkidle');
    
    await page.getByRole('button', { name: 'Week' }).click();
    await page.waitForLoadState('networkidle');
    
    await page.getByRole('button', { name: 'Month' }).click();
    await page.waitForLoadState('networkidle');
    
    // Check that filter buttons show active state
    await expect(page.getByRole('button', { name: 'Month' })).toHaveClass(/bg-blue-600/);
  });

  test('should handle session details modal', async ({ page }) => {
    // Wait for sessions to load
    await page.waitForLoadState('networkidle');
    
    // Look for session items and click on one
    const sessionItem = page.locator('[data-testid="session-item"]').first();
    
    if (await sessionItem.count() > 0) {
      await sessionItem.click();
      
      // Check modal opens
      await expect(page.getByText('Session Details')).toBeVisible();
      
      // Check modal content
      await expect(page.getByText('Session ID:')).toBeVisible();
      await expect(page.getByText('Timestamp:')).toBeVisible();
      
      // Close modal
      const closeButton = page.getByRole('button', { name: 'Close' });
      if (await closeButton.count() > 0) {
        await closeButton.click();
      }
    }
  });

  test('should display performance metrics in Performance tab', async ({ page }) => {
    // Switch to Performance tab
    await page.getByRole('button', { name: 'Performance' }).click();
    
    // Check for performance cards
    await expect(page.getByText('Total Sessions')).toBeVisible();
    await expect(page.getByText('Success Rate')).toBeVisible();
    await expect(page.getByText('Average Score')).toBeVisible();
    await expect(page.getByText('Average Iterations')).toBeVisible();
  });

  test('should load data from API endpoints', async ({ page }) => {
    // Wait for API calls to complete
    await page.waitForLoadState('networkidle');
    
    // Check that loading states are not visible (data has loaded)
    await expect(page.getByText('Loading sessions...')).not.toBeVisible();
    
    // Check for either data or "no data" messages
    const hasData = await page.locator('[data-testid="session-item"]').count() > 0;
    const hasNoDataMessage = await page.getByText('No sessions found').isVisible();
    
    expect(hasData || hasNoDataMessage).toBeTruthy();
  });

  test('should handle empty states gracefully', async ({ page }) => {
    // Switch through tabs and check for appropriate empty states
    const tabs = ['Sessions', 'Prompts', 'Evaluations', 'Performance'];
    
    for (const tabName of tabs) {
      await page.getByRole('button', { name: tabName }).click();
      await page.waitForLoadState('networkidle');
      
      // Should either have data or show appropriate empty state
      const hasError = await page.getByText('Error loading').isVisible();
      expect(hasError).toBeFalsy();
    }
  });

  test('should be responsive on mobile', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    
    // Check tabs are still accessible
    await expect(page.getByRole('button', { name: 'Sessions' })).toBeVisible();
    
    // Check search is still functional
    await expect(page.getByPlaceholder('Search sessions...')).toBeVisible();
    
    // Check filter buttons adapt to mobile layout
    await expect(page.getByRole('button', { name: 'Today' })).toBeVisible();
  });

  test('should maintain state when collapsing and expanding', async ({ page }) => {
    // Switch to a non-default tab
    await page.getByRole('button', { name: 'Prompts' }).click();
    await expect(page.getByText('Prompt History')).toBeVisible();
    
    // Collapse the section
    await page.getByRole('button', { name: /Knowledge Base Explorer/i }).click();
    await page.waitForTimeout(500);
    
    // Expand again
    await page.getByRole('button', { name: /Knowledge Base Explorer/i }).click();
    await page.waitForTimeout(500);
    
    // Check that the Prompts tab is still active
    await expect(page.getByText('Prompt History')).toBeVisible();
  });
}); 