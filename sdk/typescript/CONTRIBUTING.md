# Contributing to XAI TypeScript SDK

Thank you for your interest in contributing to the XAI TypeScript SDK! This document provides guidelines for contributing to the project.

## Code of Conduct

Please be respectful and constructive in all interactions with the project and community.

## Getting Started

### Prerequisites

- Node.js 16.x or higher
- npm or yarn
- Git

### Setup Development Environment

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/your-username/xai.git
   cd xai/sdk/typescript
   ```

3. Install dependencies:
   ```bash
   npm install
   ```

4. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Workflow

### Running Tests

```bash
npm test
```

Run tests in watch mode:
```bash
npm run test:watch
```

Generate coverage report:
```bash
npm run test:coverage
```

### Linting

```bash
npm run lint
```

Fix linting issues automatically:
```bash
npm run lint:fix
```

### Formatting

```bash
npm run format
```

### Building

```bash
npm run build
```

### Type Checking

```bash
npm run typecheck
```

## Code Style

- Use TypeScript for all code
- Follow existing code conventions
- Use meaningful variable and function names
- Add JSDoc comments for public APIs
- Keep functions small and focused
- Prefer async/await over callbacks
- Use const/let instead of var
- Add proper error handling

## Testing Guidelines

- Write tests for all new features
- Maintain or improve code coverage
- Use descriptive test names
- Test both success and error cases
- Mock external dependencies
- Keep tests isolated and independent

## Commit Messages

Follow conventional commit format:

```
type(scope): subject

body

footer
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Build process or auxiliary tool changes

Examples:
```
feat(wallet): add hardware wallet support
fix(transaction): correct fee estimation for contract calls
docs(readme): add WebSocket examples
```

## Pull Request Process

1. Update documentation for any changed functionality
2. Add tests for new features or bug fixes
3. Ensure all tests pass
4. Update CHANGELOG.md
5. Ensure code is properly formatted and linted
6. Create a pull request with a clear description

### Pull Request Checklist

- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Code formatted (`npm run format`)
- [ ] Linter passes (`npm run lint`)
- [ ] All tests pass (`npm test`)
- [ ] Type checking passes (`npm run typecheck`)
- [ ] Build succeeds (`npm run build`)

## Adding New Features

When adding new features:

1. Check if similar functionality exists
2. Design the API to be consistent with existing code
3. Add comprehensive type definitions
4. Include examples in the examples/ directory
5. Update README.md with usage instructions
6. Add tests with good coverage

## Reporting Bugs

When reporting bugs, include:

- SDK version
- Node.js version
- Operating system
- Minimal code to reproduce the issue
- Expected behavior
- Actual behavior
- Error messages and stack traces

## Feature Requests

For feature requests:

- Explain the use case
- Describe the proposed solution
- Provide examples of how it would be used
- Discuss alternatives considered

## Questions

For questions:

- Check existing documentation
- Search existing issues
- Create a new issue with the "question" label

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
