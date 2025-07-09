import { test, expect } from '@playwright/test';

test.describe('Structured Prompt Input', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should display structured input form by default', async ({ page }) => {
    // Check that structured input fields are visible
    await expect(page.getByPlaceholder('What background information should the AI know?')).toBeVisible();
    await expect(page.getByPlaceholder('What specific task or goal should be achieved?')).toBeVisible();
    await expect(page.getByPlaceholder('Any specific requirements, format, or limitations?')).toBeVisible();
  });

  test('should allow switching between Structured and Unified modes', async ({ page }) => {
    // Switch to Unified mode
    await page.getByRole('button', { name: 'Unified' }).click();
    
    // Check unified textarea is visible
    await expect(page.getByPlaceholder('Enter your prompt...')).toBeVisible();
    
    // Switch back to Structured mode
    await page.getByRole('button', { name: 'Structured' }).click();
    
    // Check structured fields are visible again
    await expect(page.getByPlaceholder('What background information should the AI know?')).toBeVisible();
  });

  test('should validate required objective field', async ({ page }) => {
    // Try to submit without filling objective (required field)
    await page.getByRole('button', { name: 'Refine Prompt' }).click();
    
    // Should see validation message or field highlight
    const objectiveField = page.getByPlaceholder('What specific task or goal should be achieved?');
    await expect(objectiveField).toBeFocused();
  });

  test('should generate smart prompts from structured inputs', async ({ page }) => {
    // Fill out the structured form
    await page.getByPlaceholder('What background information should the AI know?')
      .fill('I am working on a React application');
    
    await page.getByPlaceholder('What specific task or goal should be achieved?')
      .fill('Create a responsive navigation component');
    
    await page.getByPlaceholder('Any specific requirements, format, or limitations?')
      .fill('Must be accessible and mobile-friendly');
    
    // Check that prompt preview updates
    await expect(page.getByText('Prompt Preview')).toBeVisible();
    
    // Verify combined prompt contains our inputs
    const preview = page.locator('[data-testid="prompt-preview"]');
    await expect(preview).toContainText('React application');
    await expect(preview).toContainText('navigation component');
    await expect(preview).toContainText('accessible');
  });

  test('should work with quick templates', async ({ page }) => {
    // Click on a template button
    await page.getByRole('button', { name: 'Analysis' }).click();
    
    // Check that template content is loaded into fields
    const objectiveField = page.getByPlaceholder('What specific task or goal should be achieved?');
    const objectiveValue = await objectiveField.inputValue();
    expect(objectiveValue.length).toBeGreaterThan(0);
  });

  test('should handle style options', async ({ page }) => {
    // Fill basic objective
    await page.getByPlaceholder('What specific task or goal should be achieved?')
      .fill('Explain quantum computing');
    
    // Change style to Technical
    await page.getByText('Professional').click();
    await page.getByText('Technical').click();
    
    // Change length to Comprehensive
    await page.getByText('Medium').click();
    await page.getByText('Comprehensive').click();
    
    // Check prompt preview reflects style changes
    const preview = page.locator('[data-testid="prompt-preview"]');
    await expect(preview).toContainText('detailed');
  });

  test('should submit prompt for refinement', async ({ page }) => {
    // Fill out a valid prompt
    await page.getByPlaceholder('What specific task or goal should be achieved?')
      .fill('Write a Python function to calculate fibonacci numbers');
    
    // Click refine button
    await page.getByRole('button', { name: 'Refine Prompt' }).click();
    
    // Check for loading state or success indication
    await expect(page.getByText('Processing...')).toBeVisible({ timeout: 5000 });
  });

  test('should handle prompt refinement workflow', async ({ page }) => {
    // Fill and submit a prompt
    await page.getByPlaceholder('What specific task or goal should be achieved?')
      .fill('Create a simple todo app');
    
    await page.getByRole('button', { name: 'Refine Prompt' }).click();
    
    // Wait for refinement to complete
    await page.waitForSelector('[data-testid="refinement-results"]', { timeout: 30000 });
    
    // Check that results are displayed
    await expect(page.getByText('Refinement Results')).toBeVisible();
    await expect(page.getByText('Original Prompt')).toBeVisible();
    await expect(page.getByText('Refined Prompt')).toBeVisible();
  });

  test('should preserve form data during mode switching', async ({ page }) => {
    // Fill structured form
    await page.getByPlaceholder('What background information should the AI know?')
      .fill('Testing context');
    await page.getByPlaceholder('What specific task or goal should be achieved?')
      .fill('Testing objective');
    
    // Switch to unified mode and back
    await page.getByRole('button', { name: 'Unified' }).click();
    await page.getByRole('button', { name: 'Structured' }).click();
    
    // Check data is preserved
    await expect(page.getByPlaceholder('What background information should the AI know?'))
      .toHaveValue('Testing context');
    await expect(page.getByPlaceholder('What specific task or goal should be achieved?'))
      .toHaveValue('Testing objective');
  });
}); 