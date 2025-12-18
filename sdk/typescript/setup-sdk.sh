#!/bin/bash
# XAI TypeScript SDK Setup Script
# This script creates all necessary SDK files

set -e

SDK_DIR="/home/hudson/blockchain-projects/xai/sdk/typescript"
cd "$SDK_DIR"

echo "Setting up XAI TypeScript SDK..."

# Create tsconfig.json
cat > tsconfig.json << 'EOF'
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "lib": ["ES2020"],
    "moduleResolution": "node",
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true,
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "allowSyntheticDefaultImports": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist", "**/*.test.ts"]
}
EOF

# Create .eslintrc.json
cat > .eslintrc.json << 'EOF'
{
  "parser": "@typescript-eslint/parser",
  "extends": [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended"
  ],
  "parserOptions": {
    "ecmaVersion": 2020,
    "sourceType": "module"
  },
  "rules": {
    "@typescript-eslint/explicit-function-return-type": "warn",
    "@typescript-eslint/no-explicit-any": "warn",
    "@typescript-eslint/no-unused-vars": ["error", { "argsIgnorePattern": "^_" }],
    "no-console": ["warn", { "allow": ["warn", "error"] }]
  }
}
EOF

# Create .prettierrc.json
cat > .prettierrc.json << 'EOF'
{
  "semi": true,
  "trailingComma": "es5",
  "singleQuote": true,
  "printWidth": 100,
  "tabWidth": 2,
  "arrowParens": "always"
}
EOF

# Create jest.config.js
cat > jest.config.js << 'EOF'
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  roots: ['<rootDir>/src'],
  testMatch: ['**/__tests__/**/*.ts', '**/?(*.)+(spec|test).ts'],
  collectCoverageFrom: [
    'src/**/*.ts',
    '!src/**/*.d.ts',
    '!src/**/*.test.ts',
    '!src/**/__tests__/**',
  ],
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80,
    },
  },
};
EOF

# Create README.md
cat > README.md << 'EOF'
# XAI TypeScript/JavaScript SDK

Production-ready TypeScript/JavaScript SDK for the XAI blockchain.

## Installation

\`\`\`bash
npm install @xai/sdk
\`\`\`

## Quick Start

\`\`\`typescript
import { XAIClient } from '@xai/sdk';

const client = new XAIClient({
  baseUrl: 'http://localhost:5000'
});

const wallet = await client.wallet.create();
console.log('Wallet created:', wallet.address);
\`\`\`

See the [examples](./examples) directory for more usage examples.

## Features

- Full TypeScript support
- Async/await patterns
- Automatic retries with exponential backoff
- Connection pooling
- WebSocket support for real-time events
- Comprehensive error handling
- Browser and Node.js compatible

## Documentation

See [README.md](./README.md) for full documentation.

## License

MIT
EOF

echo "✓ Configuration files created"
echo "✓ SDK setup complete!"
echo ""
echo "Next steps:"
echo "  1. npm install"
echo "  2. npm run build"
echo "  3. See examples/ directory for usage"
