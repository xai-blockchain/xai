# Contributing to XAI Mobile Wallet

Thank you for your interest in contributing to the XAI Mobile Wallet.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/xai.git`
3. Navigate to mobile: `cd xai/mobile`
4. Install dependencies: `npm install`
5. Create a branch: `git checkout -b feature/your-feature`

## Development Setup

### Prerequisites

- Node.js 20+
- npm 10+
- Expo CLI: `npm install -g expo-cli`
- EAS CLI: `npm install -g eas-cli`
- iOS: Xcode 15+ (Mac only)
- Android: Android Studio with SDK 34+

### Running Locally

```bash
npm install
npm start
```

Press `i` for iOS, `a` for Android, or `w` for web.

## Code Standards

### TypeScript

- Use TypeScript for all new files
- Define types in `src/types/`
- Avoid `any` - use proper types or `unknown`

### Style Guide

- Follow existing code patterns
- Use functional components with hooks
- Keep components under 200 lines
- Extract reusable logic to custom hooks

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Components | PascalCase | `WalletCard.tsx` |
| Hooks | camelCase with `use` | `useWallet.ts` |
| Utils | camelCase | `formatBalance.ts` |
| Types | PascalCase | `Transaction` |
| Constants | SCREAMING_SNAKE | `MAX_RETRIES` |

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add biometric authentication
fix: resolve balance display bug
docs: update README setup instructions
style: format code with prettier
refactor: extract wallet logic to hook
test: add transaction validation tests
chore: update dependencies
```

## Pull Request Process

1. Update tests for your changes
2. Run linting: `npm run lint`
3. Run type check: `npm run typecheck`
4. Run tests: `npm test`
5. Update documentation if needed
6. Create PR with clear description

### PR Title Format

```
feat(wallet): add export functionality
fix(send): correct amount validation
```

### PR Description Template

```markdown
## Summary
Brief description of changes.

## Changes
- Change 1
- Change 2

## Testing
How to test these changes.

## Screenshots
If UI changes, include before/after.
```

## Testing

```bash
# Run tests
npm test

# Watch mode
npm test -- --watch

# Coverage
npm run test:cov
```

### Test Requirements

- Unit tests for utilities
- Component tests for UI
- Integration tests for flows
- Aim for >80% coverage on new code

## Project Structure

```
src/
├── components/     # Reusable UI
├── context/        # React Context providers
├── screens/        # Screen components
├── services/       # API and external services
├── types/          # TypeScript definitions
├── utils/          # Helper functions
└── hooks/          # Custom React hooks (create as needed)
```

## Security Considerations

When working on wallet features:

- Never log private keys or sensitive data
- Use SecureStore for sensitive storage
- Validate all user inputs
- Test with testnet before mainnet
- Review crypto operations carefully

## Questions?

- Open an issue for bugs or features
- Discussions for general questions
- Check existing issues before creating new ones

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
