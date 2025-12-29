/**
 * Production-Ready Input Validation for XAI Wallet
 *
 * Implements:
 * - Address validation with checksum verification
 * - Amount validation with overflow protection
 * - Input sanitization against XSS and injection
 * - Clipboard content validation
 * - Transaction data validation
 * - Mnemonic phrase validation
 *
 * SECURITY: All user inputs must be validated before processing.
 */

import * as Crypto from 'expo-crypto';

// ============== Constants ==============

const XAI_ADDRESS_PREFIX = 'XAI';
const XAI_ADDRESS_LENGTH = 43; // PREFIX (3) + BODY (32) + CHECKSUM (8)
const MAX_AMOUNT = 1_000_000_000_000; // 1 trillion max
const MIN_AMOUNT = 0.00000001; // 8 decimal places
const MAX_DECIMALS = 8;
const MAX_MEMO_LENGTH = 256;
const MAX_NAME_LENGTH = 64;
const MAX_INPUT_LENGTH = 1024;

// Dangerous patterns for input sanitization
const DANGEROUS_PATTERNS = [
  /<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi,
  /<iframe\b[^<]*(?:(?!<\/iframe>)<[^<]*)*<\/iframe>/gi,
  /javascript:/gi,
  /on\w+\s*=/gi,
  /data:/gi,
  /vbscript:/gi,
  /expression\s*\(/gi,
  /<\s*img[^>]*src\s*=/gi,
];

// Valid BIP39 word list (first few for validation pattern)
const BIP39_WORD_PATTERN = /^[a-z]+$/;

// ============== Types ==============

export interface ValidationResult {
  valid: boolean;
  error?: string;
  sanitized?: string;
}

export interface AddressValidationResult extends ValidationResult {
  checksumValid?: boolean;
  prefix?: string;
}

export interface AmountValidationResult extends ValidationResult {
  parsedAmount?: number;
  formattedAmount?: string;
}

export interface TransactionValidationResult extends ValidationResult {
  errors?: Record<string, string>;
}

// ============== Address Validation ==============

/**
 * Validate XAI address format
 */
export function validateAddressFormat(address: string): AddressValidationResult {
  if (!address || typeof address !== 'string') {
    return { valid: false, error: 'Address is required' };
  }

  const trimmed = address.trim();

  if (trimmed.length === 0) {
    return { valid: false, error: 'Address is required' };
  }

  // Check prefix
  if (!trimmed.startsWith(XAI_ADDRESS_PREFIX)) {
    return {
      valid: false,
      error: `Address must start with ${XAI_ADDRESS_PREFIX}`,
      prefix: trimmed.substring(0, 3),
    };
  }

  // Check length
  if (trimmed.length !== XAI_ADDRESS_LENGTH) {
    return {
      valid: false,
      error: `Invalid address length (expected ${XAI_ADDRESS_LENGTH} characters)`,
    };
  }

  // Check if remaining characters are valid hex
  const addressBody = trimmed.substring(XAI_ADDRESS_PREFIX.length);
  if (!/^[0-9a-fA-F]+$/.test(addressBody)) {
    return {
      valid: false,
      error: 'Address contains invalid characters',
    };
  }

  return {
    valid: true,
    sanitized: trimmed,
    prefix: XAI_ADDRESS_PREFIX,
  };
}

/**
 * Verify XAI address checksum
 */
export async function verifyAddressChecksum(address: string): Promise<AddressValidationResult> {
  const formatResult = validateAddressFormat(address);
  if (!formatResult.valid) {
    return formatResult;
  }

  const trimmed = address.trim();
  const body = trimmed.substring(XAI_ADDRESS_PREFIX.length, XAI_ADDRESS_PREFIX.length + 32);
  const checksum = trimmed.substring(XAI_ADDRESS_PREFIX.length + 32);

  // Recalculate checksum
  const checksumHash = await Crypto.digestStringAsync(
    Crypto.CryptoDigestAlgorithm.SHA256,
    body
  );
  const expectedChecksum = checksumHash.substring(0, 8);

  const checksumValid = checksum.toLowerCase() === expectedChecksum.toLowerCase();

  if (!checksumValid) {
    return {
      valid: false,
      error: 'Address checksum verification failed - address may be corrupted',
      checksumValid: false,
    };
  }

  return {
    valid: true,
    sanitized: trimmed,
    checksumValid: true,
    prefix: XAI_ADDRESS_PREFIX,
  };
}

/**
 * Check if address is the same as sender (self-send prevention)
 */
export function validateNotSelfSend(
  recipientAddress: string,
  senderAddress: string
): ValidationResult {
  if (!recipientAddress || !senderAddress) {
    return { valid: true }; // Can't compare, let other validation handle
  }

  const recipient = recipientAddress.trim().toLowerCase();
  const sender = senderAddress.trim().toLowerCase();

  if (recipient === sender) {
    return {
      valid: false,
      error: 'Cannot send to your own address',
    };
  }

  return { valid: true };
}

// ============== Amount Validation ==============

/**
 * Parse and validate amount string
 */
export function parseAmount(input: string): AmountValidationResult {
  if (!input || typeof input !== 'string') {
    return { valid: false, error: 'Amount is required' };
  }

  const trimmed = input.trim();

  if (trimmed.length === 0) {
    return { valid: false, error: 'Amount is required' };
  }

  // Remove any currency symbols and commas
  const cleaned = trimmed.replace(/[,$\s]/g, '');

  // Check for valid number format
  if (!/^-?\d*\.?\d+$/.test(cleaned)) {
    return { valid: false, error: 'Invalid amount format' };
  }

  // Check for multiple decimal points
  if ((cleaned.match(/\./g) || []).length > 1) {
    return { valid: false, error: 'Invalid amount format' };
  }

  const parsed = parseFloat(cleaned);

  // Check for NaN or Infinity
  if (!Number.isFinite(parsed)) {
    return { valid: false, error: 'Invalid amount' };
  }

  // Check for negative amounts
  if (parsed < 0) {
    return { valid: false, error: 'Amount cannot be negative' };
  }

  // Check for zero
  if (parsed === 0) {
    return { valid: false, error: 'Amount must be greater than zero' };
  }

  // Check minimum amount
  if (parsed < MIN_AMOUNT) {
    return {
      valid: false,
      error: `Minimum amount is ${MIN_AMOUNT} XAI`,
    };
  }

  // Check maximum amount (overflow protection)
  if (parsed > MAX_AMOUNT) {
    return {
      valid: false,
      error: `Maximum amount is ${MAX_AMOUNT.toLocaleString()} XAI`,
    };
  }

  // Check decimal places
  const decimalPart = cleaned.split('.')[1];
  if (decimalPart && decimalPart.length > MAX_DECIMALS) {
    return {
      valid: false,
      error: `Maximum ${MAX_DECIMALS} decimal places allowed`,
    };
  }

  return {
    valid: true,
    parsedAmount: parsed,
    formattedAmount: parsed.toFixed(Math.min(decimalPart?.length || 4, MAX_DECIMALS)),
    sanitized: cleaned,
  };
}

/**
 * Validate amount against balance
 */
export function validateAmountAgainstBalance(
  amount: number,
  balance: number,
  fee: number = 0
): ValidationResult {
  if (amount <= 0) {
    return { valid: false, error: 'Amount must be greater than zero' };
  }

  const total = amount + fee;

  if (total > balance) {
    if (fee > 0) {
      return {
        valid: false,
        error: `Insufficient balance (amount + fee = ${total.toFixed(4)} XAI)`,
      };
    }
    return { valid: false, error: 'Insufficient balance' };
  }

  return { valid: true };
}

/**
 * Validate fee amount
 */
export function validateFee(fee: number | string): AmountValidationResult {
  const feeNum = typeof fee === 'string' ? parseFloat(fee) : fee;

  if (!Number.isFinite(feeNum)) {
    return { valid: false, error: 'Invalid fee' };
  }

  if (feeNum < 0) {
    return { valid: false, error: 'Fee cannot be negative' };
  }

  // Warn about unusually high fees
  if (feeNum > 1) {
    return {
      valid: true,
      parsedAmount: feeNum,
      error: 'Warning: Fee is unusually high',
    };
  }

  return {
    valid: true,
    parsedAmount: feeNum,
  };
}

// ============== Input Sanitization ==============

/**
 * Sanitize string input
 * Removes dangerous patterns and limits length
 */
export function sanitizeInput(
  input: string,
  maxLength: number = MAX_INPUT_LENGTH
): string {
  if (!input || typeof input !== 'string') {
    return '';
  }

  let sanitized = input;

  // Remove dangerous patterns
  for (const pattern of DANGEROUS_PATTERNS) {
    sanitized = sanitized.replace(pattern, '');
  }

  // Remove null bytes
  sanitized = sanitized.replace(/\0/g, '');

  // Trim and limit length
  sanitized = sanitized.trim().substring(0, maxLength);

  return sanitized;
}

/**
 * Sanitize memo/note input
 */
export function sanitizeMemo(input: string): ValidationResult {
  const sanitized = sanitizeInput(input, MAX_MEMO_LENGTH);

  if (sanitized !== input.trim()) {
    return {
      valid: true,
      sanitized,
      error: 'Some characters were removed for security',
    };
  }

  return { valid: true, sanitized };
}

/**
 * Sanitize name input (wallet name, contact name)
 */
export function sanitizeName(input: string): ValidationResult {
  if (!input || input.trim().length === 0) {
    return { valid: false, error: 'Name is required' };
  }

  const sanitized = sanitizeInput(input, MAX_NAME_LENGTH);

  // Only allow alphanumeric, spaces, and basic punctuation
  const cleaned = sanitized.replace(/[^a-zA-Z0-9\s\-_.]/g, '');

  if (cleaned.length === 0) {
    return { valid: false, error: 'Name contains invalid characters' };
  }

  if (cleaned.length < 1) {
    return { valid: false, error: 'Name is too short' };
  }

  return { valid: true, sanitized: cleaned };
}

// ============== Clipboard Validation ==============

/**
 * Validate clipboard content for address pasting
 */
export function validateClipboardAddress(clipboardContent: string): AddressValidationResult {
  if (!clipboardContent || typeof clipboardContent !== 'string') {
    return { valid: false, error: 'No address found in clipboard' };
  }

  // Trim whitespace and newlines
  const trimmed = clipboardContent.trim().replace(/[\r\n]/g, '');

  // Check for suspicious content (possible clipboard hijacking)
  if (trimmed.length > 100) {
    return {
      valid: false,
      error: 'Clipboard content too long - possible security issue',
    };
  }

  // Check for multiple addresses (hijacking attempt)
  const addressMatches = trimmed.match(/XAI[0-9a-fA-F]{40}/g);
  if (addressMatches && addressMatches.length > 1) {
    return {
      valid: false,
      error: 'Multiple addresses detected - possible security issue',
    };
  }

  // Validate the address
  return validateAddressFormat(trimmed);
}

/**
 * Validate clipboard content for amount pasting
 */
export function validateClipboardAmount(clipboardContent: string): AmountValidationResult {
  if (!clipboardContent || typeof clipboardContent !== 'string') {
    return { valid: false, error: 'No amount found in clipboard' };
  }

  const trimmed = clipboardContent.trim();

  // Check for suspicious content
  if (trimmed.length > 50) {
    return { valid: false, error: 'Invalid clipboard content' };
  }

  return parseAmount(trimmed);
}

// ============== Mnemonic Validation ==============

/**
 * Validate mnemonic phrase format
 */
export function validateMnemonicFormat(mnemonic: string): ValidationResult {
  if (!mnemonic || typeof mnemonic !== 'string') {
    return { valid: false, error: 'Recovery phrase is required' };
  }

  const normalized = mnemonic.trim().toLowerCase();
  const words = normalized.split(/\s+/);

  // Check word count (12, 15, 18, 21, or 24 words)
  const validCounts = [12, 15, 18, 21, 24];
  if (!validCounts.includes(words.length)) {
    return {
      valid: false,
      error: `Invalid word count (${words.length}). Expected 12, 15, 18, 21, or 24 words`,
    };
  }

  // Check each word format (lowercase letters only)
  for (let i = 0; i < words.length; i++) {
    if (!BIP39_WORD_PATTERN.test(words[i])) {
      return {
        valid: false,
        error: `Invalid word at position ${i + 1}: "${words[i]}"`,
      };
    }

    // Check word length (BIP39 words are 3-8 characters)
    if (words[i].length < 3 || words[i].length > 8) {
      return {
        valid: false,
        error: `Invalid word at position ${i + 1}: "${words[i]}"`,
      };
    }
  }

  return {
    valid: true,
    sanitized: words.join(' '),
  };
}

// ============== Transaction Validation ==============

/**
 * Validate complete transaction data
 */
export async function validateTransaction(tx: {
  sender: string;
  recipient: string;
  amount: number | string;
  fee: number | string;
  balance: number;
  memo?: string;
}): Promise<TransactionValidationResult> {
  const errors: Record<string, string> = {};

  // Validate sender address
  const senderResult = validateAddressFormat(tx.sender);
  if (!senderResult.valid) {
    errors.sender = senderResult.error || 'Invalid sender address';
  }

  // Validate recipient address with checksum
  const recipientResult = await verifyAddressChecksum(tx.recipient);
  if (!recipientResult.valid) {
    errors.recipient = recipientResult.error || 'Invalid recipient address';
  }

  // Validate not self-send
  const selfSendResult = validateNotSelfSend(tx.recipient, tx.sender);
  if (!selfSendResult.valid) {
    errors.recipient = selfSendResult.error || 'Cannot send to yourself';
  }

  // Validate amount
  const amountNum = typeof tx.amount === 'string'
    ? parseAmount(tx.amount).parsedAmount
    : tx.amount;

  if (!amountNum || amountNum <= 0) {
    errors.amount = 'Invalid amount';
  }

  // Validate fee
  const feeNum = typeof tx.fee === 'string' ? parseFloat(tx.fee) : tx.fee;
  const feeResult = validateFee(feeNum);
  if (!feeResult.valid) {
    errors.fee = feeResult.error || 'Invalid fee';
  }

  // Validate balance
  if (amountNum && feeNum !== undefined) {
    const balanceResult = validateAmountAgainstBalance(amountNum, tx.balance, feeNum);
    if (!balanceResult.valid) {
      errors.amount = balanceResult.error || 'Insufficient balance';
    }
  }

  // Validate memo if present
  if (tx.memo) {
    const memoResult = sanitizeMemo(tx.memo);
    if (!memoResult.valid) {
      errors.memo = memoResult.error || 'Invalid memo';
    }
  }

  const hasErrors = Object.keys(errors).length > 0;

  return {
    valid: !hasErrors,
    errors: hasErrors ? errors : undefined,
    error: hasErrors ? Object.values(errors)[0] : undefined,
  };
}

// ============== URL Validation ==============

/**
 * Validate node URL
 */
export function validateNodeUrl(url: string): ValidationResult {
  if (!url || typeof url !== 'string') {
    return { valid: false, error: 'URL is required' };
  }

  const trimmed = url.trim();

  // Check for valid URL format
  try {
    const parsed = new URL(trimmed);

    // Only allow http and https
    if (!['http:', 'https:'].includes(parsed.protocol)) {
      return {
        valid: false,
        error: 'Only HTTP and HTTPS protocols are allowed',
      };
    }

    // Warn about HTTP (not HTTPS)
    if (parsed.protocol === 'http:') {
      return {
        valid: true,
        sanitized: trimmed,
        error: 'Warning: HTTP is not secure. Consider using HTTPS.',
      };
    }

    return {
      valid: true,
      sanitized: trimmed,
    };
  } catch {
    return { valid: false, error: 'Invalid URL format' };
  }
}

// ============== Private Key Validation ==============

/**
 * Validate private key format
 */
export function validatePrivateKeyFormat(privateKey: string): ValidationResult {
  if (!privateKey || typeof privateKey !== 'string') {
    return { valid: false, error: 'Private key is required' };
  }

  // Remove 0x prefix if present
  const cleaned = privateKey.trim().replace(/^0x/i, '');

  // Check length (32 bytes = 64 hex characters)
  if (cleaned.length !== 64) {
    return {
      valid: false,
      error: 'Invalid private key length',
    };
  }

  // Check for valid hex
  if (!/^[0-9a-fA-F]+$/.test(cleaned)) {
    return {
      valid: false,
      error: 'Private key contains invalid characters',
    };
  }

  // Check for all zeros (invalid key)
  if (/^0+$/.test(cleaned)) {
    return {
      valid: false,
      error: 'Invalid private key',
    };
  }

  return {
    valid: true,
    sanitized: cleaned.toLowerCase(),
  };
}

// ============== Nonce Validation ==============

/**
 * Validate transaction nonce
 */
export function validateNonce(
  nonce: number,
  expectedNonce: number
): ValidationResult {
  if (!Number.isInteger(nonce) || nonce < 0) {
    return { valid: false, error: 'Invalid nonce' };
  }

  if (nonce < expectedNonce) {
    return {
      valid: false,
      error: `Nonce too low (expected ${expectedNonce}, got ${nonce})`,
    };
  }

  if (nonce > expectedNonce + 100) {
    return {
      valid: false,
      error: 'Nonce gap too large',
    };
  }

  return { valid: true };
}

// ============== Batch Validation ==============

/**
 * Validate batch transaction recipients
 */
export async function validateBatchRecipients(
  recipients: Array<{ address: string; amount: number | string }>,
  senderAddress: string,
  balance: number,
  fee: number
): Promise<{
  valid: boolean;
  errors: Array<{ index: number; field: string; error: string }>;
  totalAmount: number;
}> {
  const errors: Array<{ index: number; field: string; error: string }> = [];
  let totalAmount = 0;

  // Check batch size
  if (recipients.length === 0) {
    errors.push({ index: -1, field: 'batch', error: 'No recipients provided' });
  }

  if (recipients.length > 100) {
    errors.push({ index: -1, field: 'batch', error: 'Maximum 100 recipients per batch' });
  }

  // Validate each recipient
  for (let i = 0; i < recipients.length; i++) {
    const recipient = recipients[i];

    // Validate address
    const addressResult = await verifyAddressChecksum(recipient.address);
    if (!addressResult.valid) {
      errors.push({
        index: i,
        field: 'address',
        error: addressResult.error || 'Invalid address',
      });
    }

    // Check self-send
    const selfSendResult = validateNotSelfSend(recipient.address, senderAddress);
    if (!selfSendResult.valid) {
      errors.push({
        index: i,
        field: 'address',
        error: selfSendResult.error || 'Cannot send to yourself',
      });
    }

    // Validate amount
    const amountResult = typeof recipient.amount === 'string'
      ? parseAmount(recipient.amount)
      : { valid: recipient.amount > 0, parsedAmount: recipient.amount };

    if (!amountResult.valid || !amountResult.parsedAmount) {
      errors.push({
        index: i,
        field: 'amount',
        error: amountResult.error || 'Invalid amount',
      });
    } else {
      totalAmount += amountResult.parsedAmount;
    }
  }

  // Check total against balance
  const totalWithFees = totalAmount + fee * recipients.length;
  if (totalWithFees > balance) {
    errors.push({
      index: -1,
      field: 'balance',
      error: `Insufficient balance for batch (total: ${totalWithFees.toFixed(4)} XAI)`,
    });
  }

  return {
    valid: errors.length === 0,
    errors,
    totalAmount,
  };
}
