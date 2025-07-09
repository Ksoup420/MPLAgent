import { test, expect } from '@playwright/test';

test.describe('Prompt Refinement Workflow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should complete full refinement cycle with structured input', async ({ page }) => {
    // Step 1: Fill out structured prompt form
    await page.getByPlaceholder('What background information should the AI know?')
      .fill('I am developing a web application using React and TypeScript');
    
    await page.getByPlaceholder('What specific task or goal should be achieved?')
      .fill('Create a reusable button component with multiple variants');
    
    await page.getByPlaceholder('Any specific requirements, format, or limitations?')
      .fill('Must be accessible, support dark mode, and include loading states');

    // Step 2: Verify prompt preview updates
    await expect(page.getByText('Prompt Preview')).toBeVisible();
    const preview = page.locator('[data-testid="prompt-preview"]');
    await expect(preview).toContainText('React');
    await expect(preview).toContainText('button component');
    await expect(preview).toContainText('accessible');

    // Step 3: Submit for refinement
    await page.getByRole('button', { name: 'Refine Prompt' }).click();

    // Step 4: Wait for processing to complete
    await expect(page.getByText('Processing...')).toBeVisible();
    
    // Wait for refinement to finish (up to 60 seconds for AI processing)
    await page.waitForSelector('[data-testid="refinement-results"]', { timeout: 60000 });

    // Step 5: Verify refinement results are displayed
    await expect(page.getByText('Refinement Results')).toBeVisible();
    await expect(page.getByText('Original Prompt')).toBeVisible();
    await expect(page.getByText('Refined Prompt')).toBeVisible();
    
    // Step 6: Verify evaluation scores are shown
    await expect(page.getByText('Evaluation Score')).toBeVisible();
    
    // Step 7: Check that iteration information is displayed
    await expect(page.locator('[data-testid="iteration-info"]')).toBeVisible();
  });

  test('should handle refinement with unified input mode', async ({ page }) => {
    // Switch to unified mode
    await page.getByRole('button', { name: 'Unified' }).click();
    
    // Fill unified prompt
    const unifiedPrompt = 'Write a Python function that calculates the factorial of a number using recursion, with proper error handling for negative inputs.';
    await page.getByPlaceholder('Enter your prompt...').fill(unifiedPrompt);
    
    // Submit for refinement
    await page.getByRole('button', { name: 'Refine Prompt' }).click();
    
    // Wait for processing
    await expect(page.getByText('Processing...')).toBeVisible();
    
    // Wait for results
    await page.waitForSelector('[data-testid="refinement-results"]', { timeout: 60000 });
    
    // Verify results
    await expect(page.getByText('Refinement Results')).toBeVisible();
    await expect(page.locator('[data-testid="original-prompt"]')).toContainText('factorial');
  });

  test('should update Knowledge Base after successful refinement', async ({ page }) => {
    // Complete a refinement
    await page.getByPlaceholder('What specific task or goal should be achieved?')
      .fill('Explain the concept of machine learning in simple terms');
    
    await page.getByRole('button', { name: 'Refine Prompt' }).click();
    await page.waitForSelector('[data-testid="refinement-results"]', { timeout: 60000 });
    
    // Check Knowledge Base Explorer for the new session
    await page.getByRole('button', { name: /Knowledge Base Explorer/i }).click();
    await page.waitForTimeout(500);
    
    // Check that sessions list updates
    await page.waitForLoadState('networkidle');
    
    // Look for recent session
    const sessionsList = page.locator('[data-testid="sessions-list"]');
    const hasNewSession = await page.locator('[data-testid="session-item"]').count() > 0;
    
    expect(hasNewSession).toBeTruthy();
  });

  test('should update analytics after refinement', async ({ page }) => {
    // Complete a refinement
    await page.getByPlaceholder('What specific task or goal should be achieved?')
      .fill('Generate a creative story about time travel');
    
    await page.getByRole('button', { name: 'Refine Prompt' }).click();
    await page.waitForSelector('[data-testid="refinement-results"]', { timeout: 60000 });
    
    // Check Advanced Analytics for updated metrics
    await page.getByRole('button', { name: /Advanced Analytics/i }).click();
    await page.waitForTimeout(500);
    
    // Wait for analytics to load new data
    await page.waitForLoadState('networkidle');
    
    // Verify metrics are displayed (numbers should be greater than 0)
    await expect(page.getByText('Total Sessions')).toBeVisible();
    
    // Check that session count is at least 1
    const totalSessionsCard = page.locator('[data-testid="total-sessions-card"]');
    if (await totalSessionsCard.count() > 0) {
      const sessionText = await totalSessionsCard.textContent();
      expect(sessionText).not.toContain('0 Sessions');
    }
  });

  test('should handle refinement errors gracefully', async ({ page }) => {
    // Submit an empty prompt to trigger validation
    await page.getByRole('button', { name: 'Refine Prompt' }).click();
    
    // Should focus on the required field or show validation message
    const objectiveField = page.getByPlaceholder('What specific task or goal should be achieved?');
    await expect(objectiveField).toBeFocused();
    
    // Fill with minimal content and try again
    await objectiveField.fill('test');
    await page.getByRole('button', { name: 'Refine Prompt' }).click();
    
    // Should either process successfully or show appropriate error handling
    const hasProcessing = await page.getByText('Processing...').isVisible();
    const hasError = await page.getByText('Error').isVisible();
    
    // One of these should be true - either it processes or shows error
    expect(hasProcessing || hasError).toBeTruthy();
  });

  test('should preserve session state during navigation', async ({ page }) => {
    // Complete a refinement
    await page.getByPlaceholder('What specific task or goal should be achieved?')
      .fill('Create CSS animations for loading spinners');
    
    await page.getByRole('button', { name: 'Refine Prompt' }).click();
    await page.waitForSelector('[data-testid="refinement-results"]', { timeout: 60000 });
    
    // Navigate to Knowledge Base
    await page.getByRole('button', { name: /Knowledge Base Explorer/i }).click();
    await page.waitForTimeout(500);
    
    // Navigate back to main prompt area
    await page.getByRole('button', { name: /Knowledge Base Explorer/i }).click();
    await page.waitForTimeout(500);
    
    // Check that refinement results are still visible
    await expect(page.getByText('Refinement Results')).toBeVisible();
  });

  test('should support multiple refinement iterations', async ({ page }) => {
    // First refinement
    await page.getByPlaceholder('What specific task or goal should be achieved?')
      .fill('Write documentation for an API endpoint');
    
    await page.getByRole('button', { name: 'Refine Prompt' }).click();
    await page.waitForSelector('[data-testid="refinement-results"]', { timeout: 60000 });
    
    // Get the refined prompt for second iteration
    const refinedPromptElement = page.locator('[data-testid="refined-prompt"]');
    const refinedText = await refinedPromptElement.textContent();
    
    if (refinedText) {
      // Clear and use refined prompt for another iteration
      await page.getByRole('button', { name: 'Unified' }).click();
      await page.getByPlaceholder('Enter your prompt...').clear();
      await page.getByPlaceholder('Enter your prompt...').fill(refinedText);
      
      // Second refinement
      await page.getByRole('button', { name: 'Refine Prompt' }).click();
      await page.waitForSelector('[data-testid="refinement-results"]', { timeout: 60000 });
      
      // Check that second iteration results are shown
      await expect(page.getByText('Refinement Results')).toBeVisible();
    }
  });

  test('should handle concurrent users and sessions', async ({ page, context }) => {
    // Open a second page to simulate another user
    const page2 = await context.newPage();
    await page2.goto('/');
    
    // Start refinement on both pages simultaneously
    const prompt1 = 'Design a database schema for an e-commerce platform';
    const prompt2 = 'Create unit tests for a user authentication system';
    
    // Page 1 refinement
    await page.getByPlaceholder('What specific task or goal should be achieved?').fill(prompt1);
    await page.getByRole('button', { name: 'Refine Prompt' }).click();
    
    // Page 2 refinement
    await page2.getByPlaceholder('What specific task or goal should be achieved?').fill(prompt2);
    await page2.getByRole('button', { name: 'Refine Prompt' }).click();
    
    // Both should complete successfully
    await page.waitForSelector('[data-testid="refinement-results"]', { timeout: 60000 });
    await page2.waitForSelector('[data-testid="refinement-results"]', { timeout: 60000 });
    
    // Verify both sessions have their own results
    await expect(page.locator('[data-testid="original-prompt"]')).toContainText('database schema');
    await expect(page2.locator('[data-testid="original-prompt"]')).toContainText('unit tests');
    
    await page2.close();
  });

  test('should provide accessible user experience', async ({ page }) => {
    // Test keyboard navigation
    await page.keyboard.press('Tab'); // Should focus first interactive element
    
    // Fill form using keyboard
    await page.getByPlaceholder('What specific task or goal should be achieved?').focus();
    await page.keyboard.type('Create accessible web components using ARIA labels');
    
    // Submit using Enter key
    await page.keyboard.press('Enter');
    
    // Check that submission works via keyboard
    await expect(page.getByText('Processing...')).toBeVisible();
    
    // Wait for results
    await page.waitForSelector('[data-testid="refinement-results"]', { timeout: 60000 });
    
    // Verify results are accessible
    await expect(page.getByText('Refinement Results')).toBeVisible();
  });
}); 