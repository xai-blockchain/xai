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
  baseUrl: 'http://localhost:12080'
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
