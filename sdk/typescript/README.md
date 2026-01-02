# TypeScript SDK

Client SDK for the XAI node API.

## Install (local)

```bash
cd sdk/typescript
npm install
npm run build
```

## Usage

```ts
import { XAIClient } from '@xai/sdk';

const client = new XAIClient({ baseUrl: 'http://localhost:12001' });
const stats = await client.blockchain.getStats();
```
