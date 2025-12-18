/**
 * Build Validation Test
 * Tests the built SDK to ensure it exports correctly
 */

const fs = require('fs');
const path = require('path');

describe('Build Validation', () => {
  const distPath = path.join(__dirname, '..', 'dist');

  it('should have dist directory', () => {
    expect(fs.existsSync(distPath)).toBe(true);
  });

  it('should have CommonJS build', () => {
    const cjsPath = path.join(distPath, 'index.js');
    expect(fs.existsSync(cjsPath)).toBe(true);
  });

  it('should have ESM build', () => {
    const esmPath = path.join(distPath, 'index.mjs');
    expect(fs.existsSync(esmPath)).toBe(true);
  });

  it('should have TypeScript declarations', () => {
    const dtsPath = path.join(distPath, 'index.d.ts');
    expect(fs.existsSync(dtsPath)).toBe(true);
  });

  it('CommonJS build should be valid JavaScript', () => {
    const cjsPath = path.join(distPath, 'index.js');
    const content = fs.readFileSync(cjsPath, 'utf-8');
    expect(content).toContain('exports');
    expect(content.length).toBeGreaterThan(1000);
  });

  it('Type definitions should export main classes', () => {
    const dtsPath = path.join(distPath, 'index.d.ts');
    const content = fs.readFileSync(dtsPath, 'utf-8');
    expect(content).toContain('XAIClient');
    expect(content).toContain('Wallet');
    expect(content).toContain('Transaction');
  });
});
