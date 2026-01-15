# CI/CD Pipeline Migration

This directory contains the GitHub Actions workflow that could not be automatically pushed due to GitHub App permissions restrictions.

## Contents

- `ci.yml` - The main CI/CD workflow for the Circuit Schematic Viewer

## Migration Instructions

To enable CI/CD for this repository, follow these steps:

### 1. Create the workflow directory

```bash
mkdir -p .github/workflows
```

### 2. Copy the workflow file

```bash
cp ci-migration/ci.yml .github/workflows/ci.yml
```

### 3. Commit and push

```bash
git add .github/workflows/ci.yml
git commit -m "feat: Add CI/CD pipeline for circuit schematic viewer"
git push
```

### 4. Verify

After pushing, check the Actions tab in your GitHub repository to ensure the workflow is running.

## Workflow Overview

The CI pipeline has two jobs:

### `lint-and-test`
- Runs on every push to `main` and `claude/**` branches
- Runs on all pull requests to `main`
- Steps:
  1. Checkout code
  2. Setup Node.js 22
  3. Install pnpm 10
  4. Cache pnpm store
  5. Install dependencies
  6. Run ESLint (`pnpm lint`)
  7. Check Prettier formatting (`pnpm format:check`)
  8. Run TypeScript type check (`pnpm typecheck`)
  9. Run unit tests (`pnpm test`)
  10. Build production bundle (`pnpm build`)

### `e2e`
- Runs after `lint-and-test` passes
- Steps:
  1. Setup environment (same as above)
  2. Install Playwright browsers (Chromium only for speed)
  3. Run E2E tests (`pnpm test:e2e`)
  4. Upload Playwright report as artifact (retained 30 days)

## Troubleshooting

### Workflow not running?
- Ensure you have write access to the repository
- Check that the workflow file is valid YAML
- Verify the branch patterns match your workflow

### Tests failing?
- Check the Actions logs for detailed error messages
- Run tests locally first: `cd viewer && pnpm test && pnpm test:e2e`

### E2E tests timing out?
- Playwright tests have a 30-second timeout by default
- Increase timeout in `playwright.config.ts` if needed
