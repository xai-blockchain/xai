# XAI SDK Examples

This directory contains example code demonstrating various features of the XAI TypeScript SDK.

## Prerequisites

Before running the examples, make sure you have:

1. Node.js 16.x or higher installed
2. A running XAI blockchain node (default: http://localhost:5000)
3. The SDK installed:
   ```bash
   npm install @xai/sdk
   ```

## Running Examples

### Basic Usage
Demonstrates fundamental SDK operations including wallet creation, balance checking, and blockchain stats.

```bash
npx ts-node examples/basic-usage.ts
```

### Transactions
Shows how to send transactions, estimate fees, and wait for confirmations.

```bash
npx ts-node examples/transactions.ts
```

### WebSocket Events
Demonstrates real-time event streaming using WebSocket connections.

```bash
npx ts-node examples/websocket-events.ts
```

Press Ctrl+C to stop listening.

### Mining
Shows mining operations including starting/stopping mining and monitoring status.

```bash
npx ts-node examples/mining.ts
```

### Governance
Demonstrates governance features including creating proposals and voting.

```bash
npx ts-node examples/governance.ts
```

## Configuring Node URL

All examples connect to `http://localhost:5000` by default. To use a different node:

```typescript
const client = new XAIClient({
  baseUrl: 'https://testnet-api.xai-blockchain.io', // Your node URL
  apiKey: 'your-api-key', // Optional
});
```

## Example Modifications

Feel free to modify these examples to explore additional features:

- Change transaction amounts
- Adjust mining thread counts
- Create multiple proposals
- Test different vote choices
- Monitor different event types

## Troubleshooting

### Connection Errors
If you see connection errors, ensure:
- The XAI node is running
- The node URL is correct
- No firewall is blocking the connection

### WebSocket Issues
For WebSocket examples:
- Make sure the node supports WebSocket connections
- Check that the WebSocket URL matches your node configuration
- Verify no proxy is interfering with WebSocket connections

### Authentication Errors
If using an API key:
- Verify the API key is correct
- Ensure the key has necessary permissions
- Check if the key has expired

## Additional Resources

- [Main README](../README.md) - Complete SDK documentation
- [API Reference](../docs/api.md) - Detailed API documentation
- [XAI Documentation](https://xai-blockchain.io/docs) - Blockchain documentation
