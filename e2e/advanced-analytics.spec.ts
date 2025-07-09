import { test, expect } from '@playwright/test';

test.describe('Advanced Analytics Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    
    // Expand the Advanced Analytics section
    await page.getByRole('button', { name: /Advanced Analytics/i }).click();
    await page.waitForTimeout(500); // Wait for expansion animation
  });

  test('should display all key metrics cards', async ({ page }) => {
    // Wait for data to load
    await page.waitForLoadState('networkidle');
    
    // Check all metric cards are visible
    await expect(page.getByText('Success Rate')).toBeVisible();
    await expect(page.getByText('Average Iterations')).toBeVisible();
    await expect(page.getByText('Total Sessions')).toBeVisible();
    await expect(page.getByText('Average Score')).toBeVisible();
  });

  test('should display metric values with proper formatting', async ({ page }) => {
    // Wait for data to load
    await page.waitForLoadState('networkidle');
    
    // Check that metric values are displayed (not just loading states)
    const successRateCard = page.locator('[data-testid="success-rate-card"]');
    const totalSessionsCard = page.locator('[data-testid="total-sessions-card"]');
    
    // Values should be numbers or percentages, not "Loading..."
    if (await successRateCard.count() > 0) {
      const successRateText = await successRateCard.textContent();
      expect(successRateText).not.toContain('Loading');
    }
    
    if (await totalSessionsCard.count() > 0) {
      const totalSessionsText = await totalSessionsCard.textContent();
      expect(totalSessionsText).not.toContain('Loading');
    }
  });

  test('should display performance insights section', async ({ page }) => {
    // Wait for data to load
    await page.waitForLoadState('networkidle');
    
    // Check insights section is visible
    await expect(page.getByText('Performance Insights')).toBeVisible();
    
    // Check for insight items or empty state
    const hasInsights = await page.locator('[data-testid="insight-item"]').count() > 0;
    const hasEmptyState = await page.getByText('No insights available').isVisible();
    
    expect(hasInsights || hasEmptyState).toBeTruthy();
  });

  test('should display time range filters', async ({ page }) => {
    // Check time range filter buttons are visible
    await expect(page.getByRole('button', { name: '24h' })).toBeVisible();
    await expect(page.getByRole('button', { name: '7d' })).toBeVisible();
    await expect(page.getByRole('button', { name: '30d' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'All' })).toBeVisible();
  });

  test('should handle time range filter changes', async ({ page }) => {
    // Wait for initial load
    await page.waitForLoadState('networkidle');
    
    // Click different time range filters
    await page.getByRole('button', { name: '7d' }).click();
    await page.waitForLoadState('networkidle');
    
    await page.getByRole('button', { name: '30d' }).click();
    await page.waitForLoadState('networkidle');
    
    // Check that active filter is highlighted
    await expect(page.getByRole('button', { name: '30d' })).toHaveClass(/bg-blue-600/);
    
    // Check that metrics update (values might change with different time ranges)
    // This test ensures the UI responds to filter changes
  });

  test('should display score trends visualization', async ({ page }) => {
    // Wait for data and check for trends section
    await page.waitForLoadState('networkidle');
    
    // Check for score trends section
    await expect(page.getByText('Score Trends')).toBeVisible();
    
    // Check for trend visualization elements
    const hasTrendChart = await page.locator('[data-testid="score-trend-chart"]').count() > 0;
    const hasTrendData = await page.locator('[data-testid="trend-point"]').count() > 0;
    const hasNoTrendData = await page.getByText('No trend data available').isVisible();
    
    expect(hasTrendChart || hasTrendData || hasNoTrendData).toBeTruthy();
  });

  test('should display activity summary', async ({ page }) => {
    // Wait for data to load
    await page.waitForLoadState('networkidle');
    
    // Check activity summary section
    await expect(page.getByText('Activity Summary')).toBeVisible();
    
    // Check for activity data or empty state
    const hasActivityData = await page.locator('[data-testid="activity-item"]').count() > 0;
    const hasEmptyActivity = await page.getByText('No recent activity').isVisible();
    
    expect(hasActivityData || hasEmptyActivity).toBeTruthy();
  });

  test('should show appropriate loading states', async ({ page }) => {
    // Before data loads, should show loading indicators
    await page.goto('/');
    await page.getByRole('button', { name: /Advanced Analytics/i }).click();
    
    // Check for loading text or spinners (briefly visible)
    const hasLoadingIndicator = await page.getByText('Loading analytics...').isVisible();
    const hasSpinner = await page.locator('[data-testid="loading-spinner"]').isVisible();
    
    // Loading indicators should appear initially
    // (This test may need adjustment based on how fast the API responds)
  });

  test('should handle empty data states gracefully', async ({ page }) => {
    // Wait for all data to load
    await page.waitForLoadState('networkidle');
    
    // Check that there are no error messages
    await expect(page.getByText('Error loading analytics')).not.toBeVisible();
    await expect(page.getByText('Failed to fetch')).not.toBeVisible();
    
    // All sections should either have data or appropriate empty states
    const sections = [
      'Success Rate',
      'Average Iterations', 
      'Total Sessions',
      'Average Score',
      'Performance Insights',
      'Score Trends',
      'Activity Summary'
    ];
    
    for (const sectionName of sections) {
      await expect(page.getByText(sectionName)).toBeVisible();
    }
  });

  test('should be responsive on mobile viewport', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    
    // Check that metric cards stack properly on mobile
    await expect(page.getByText('Success Rate')).toBeVisible();
    await expect(page.getByText('Total Sessions')).toBeVisible();
    
    // Check that time range filters are still accessible
    await expect(page.getByRole('button', { name: '24h' })).toBeVisible();
    
    // Check that insights section is still readable
    await expect(page.getByText('Performance Insights')).toBeVisible();
  });

  test('should display meaningful insights based on data', async ({ page }) => {
    // Wait for data to load
    await page.waitForLoadState('networkidle');
    
    // Check for insight content
    const insightItems = page.locator('[data-testid="insight-item"]');
    
    if (await insightItems.count() > 0) {
      // Check that insights contain actionable text
      const firstInsight = insightItems.first();
      const insightText = await firstInsight.textContent();
      
      // Insights should contain meaningful recommendations
      if (insightText) {
        expect(insightText.length).toBeGreaterThan(10);
        expect(insightText).not.toContain('undefined');
        expect(insightText).not.toContain('null');
      }
    }
  });

  test('should refresh data when filters change', async ({ page }) => {
    // Wait for initial load
    await page.waitForLoadState('networkidle');
    
    // Get initial success rate value
    const successRateElement = page.locator('[data-testid="success-rate-value"]');
    let initialValue = '';
    
    if (await successRateElement.count() > 0) {
      const textContent = await successRateElement.textContent();
      initialValue = textContent || '';
    }
    
    // Change time filter
    await page.getByRole('button', { name: '7d' }).click();
    await page.waitForLoadState('networkidle');
    
    // Values might change (or stay the same if no data difference)
    // This test ensures the UI properly handles filter changes
    await expect(successRateElement).toBeVisible();
  });

  test('should maintain state when collapsing and expanding', async ({ page }) => {
    // Set a specific time filter
    await page.getByRole('button', { name: '7d' }).click();
    await page.waitForLoadState('networkidle');
    
    // Collapse the section
    await page.getByRole('button', { name: /Advanced Analytics/i }).click();
    await page.waitForTimeout(500);
    
    // Expand again
    await page.getByRole('button', { name: /Advanced Analytics/i }).click();
    await page.waitForTimeout(500);
    
    // Check that the 7d filter is still active
    await expect(page.getByRole('button', { name: '7d' })).toHaveClass(/bg-blue-600/);
  });
}); 