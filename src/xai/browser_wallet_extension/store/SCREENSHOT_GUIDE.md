# Screenshot Guide - XAI Browser Wallet

Guide for capturing professional screenshots for Chrome Web Store and Firefox Add-ons.

## Requirements

### Chrome Web Store
- Minimum: 1 screenshot
- Recommended: 3-5 screenshots
- Size: 1280x800 or 640x400
- Format: PNG or JPEG
- Max file size: 5 MB each

### Firefox Add-ons
- Minimum: 1 screenshot
- Maximum: 10 screenshots
- Recommended size: 1280x800
- Format: PNG or JPEG
- Captions required for each

## Recommended Screenshots

### 1. Main Wallet Dashboard (Required)
**Shows**: Primary wallet interface
**Elements**:
- Wallet balance prominently displayed
- XAI address (use example address)
- Account name/label
- Quick action buttons (Send, Receive, etc.)
- Recent transaction list (3-5 items)
- Navigation tabs/menu

**Caption**: "Secure wallet dashboard with balance tracking and transaction history"

**Tips**:
- Use realistic but fake data
- Example balance: 1,234.56 XAI
- Example address: xai1abc...xyz (truncated)
- Show 3-5 example transactions
- Clean, uncluttered interface

### 2. Hardware Wallet Connection (Required)
**Shows**: Hardware wallet integration
**Elements**:
- Hardware wallet selection screen (Ledger/Trezor options)
- Connection status/instructions
- Device detection interface
- Permission request flow

**Caption**: "Connect Ledger or Trezor hardware wallet for maximum security"

**Tips**:
- Show device selection screen or connection wizard
- If showing connected state, display device name
- Highlight security benefits
- Show clear call-to-action buttons

### 3. Send Transaction (Recommended)
**Shows**: Transaction creation interface
**Elements**:
- Recipient address field
- Amount input
- Gas fee selector
- Transaction summary
- Confirmation button
- Hardware wallet confirmation prompt (if applicable)

**Caption**: "Create and sign transactions with hardware wallet security"

**Tips**:
- Use example recipient address
- Show reasonable gas fee
- Display transaction summary clearly
- Include security indicators

### 4. Mining Dashboard (Optional)
**Shows**: Mining controls and status
**Elements**:
- Mining status (active/inactive)
- Hashrate display
- Earnings/rewards counter
- Start/stop mining controls
- Mining pool information (if applicable)
- Performance metrics

**Caption**: "Monitor and control XAI mining operations"

**Tips**:
- Show active mining state for visual interest
- Display realistic hashrate numbers
- Include earnings information
- Show clear control buttons

### 5. DEX Trading Interface (Optional)
**Shows**: Decentralized exchange features
**Elements**:
- Trading pair selector
- Order book or price chart
- Buy/sell interface
- Balance information
- Recent trades

**Caption**: "Trade on decentralized exchange without intermediaries"

**Tips**:
- Show active market data
- Display clear buy/sell options
- Include balance information
- Demonstrate trading features

## Capturing Screenshots

### Method 1: Browser Screenshot (Recommended)

**Chrome**:
1. Load extension from `chrome://extensions/`
2. Click extension icon to open popup
3. Press F12 to open DevTools
4. Click three-dot menu > More tools > Capture screenshot
5. Or use Device Toolbar (Ctrl+Shift+M) to set exact dimensions

**Firefox**:
1. Load extension from `about:debugging`
2. Click extension icon to open popup
3. Right-click > Take a Screenshot
4. Or use screenshot tool in address bar

### Method 2: External Tools

**Linux (Screenshot tool)**:
```bash
# Capture area (click and drag)
gnome-screenshot -a

# Or use scrot
scrot -s screenshot.png
```

**ImageMagick (resize if needed)**:
```bash
convert screenshot.png -resize 1280x800 screenshot-resized.png
```

### Method 3: Browser DevTools

1. Open extension popup
2. Press F12 to open DevTools
3. Click Device Toolbar icon (Ctrl+Shift+M)
4. Set dimensions to 1280x800
5. Use DevTools screenshot capture

## Screenshot Best Practices

### Content
- Use example data, not real user information
- Show clean, error-free states
- Include enough data to look realistic
- Demonstrate key features visually
- Avoid empty or placeholder states

### Example Addresses
```
Wallet Address: xai1qxy8example7h9rl4dp73h8j3qtsvxk9hd9xmpd
Recipient: xai1abc8exampledef2g9h3j5k7m9n2p4qrstuvwxyz
```

### Example Balances
```
Main Balance: 1,234.56 XAI
USD Value: $4,567.89
Gas Fee: 0.001 XAI
```

### Example Transactions
```
1. Sent 50 XAI to xai1abc...xyz - 2 hours ago
2. Received 125 XAI from xai1def...uvw - 1 day ago
3. Mining Reward 5.5 XAI - 2 days ago
```

### Visual Quality
- High resolution (1280x800 minimum)
- Clear, crisp text
- Good contrast
- No pixelation or blur
- Professional appearance

### Privacy
- No real addresses or private keys
- No real transaction hashes
- No personal information
- No sensitive balances

## Screenshot Order

List screenshots in order of importance:

1. **Main Dashboard** - Most important, shows primary value
2. **Hardware Wallet** - Key differentiator
3. **Send Transaction** - Core functionality
4. **Mining** - Unique feature
5. **Trading** - Advanced feature

First screenshot is featured most prominently in stores.

## Editing Screenshots

### Recommended Tools

**GIMP** (free):
```bash
sudo apt install gimp
gimp screenshot.png
```

**ImageMagick** (command-line):
```bash
# Resize
convert input.png -resize 1280x800 output.png

# Add border
convert input.png -border 2x2 -bordercolor "#cccccc" output.png

# Optimize file size
convert input.png -quality 85 output.jpg
```

**Online Tools**:
- Photopea (photopea.com) - Free Photoshop alternative
- Pixlr (pixlr.com) - Online photo editor
- Canva (canva.com) - Design tool with templates

### Enhancements
- Slight brightness/contrast adjustment
- Crop to exact dimensions
- Add subtle drop shadow (optional)
- Remove window decorations
- Ensure consistent styling across all screenshots

## Testing Screenshots

Before uploading:

- [ ] All screenshots are 1280x800 (or 640x400)
- [ ] File size under 5 MB each
- [ ] PNG or JPEG format
- [ ] Clear and readable text
- [ ] No personal/sensitive data
- [ ] Demonstrates key features
- [ ] Professional appearance
- [ ] Consistent styling
- [ ] Good lighting/contrast
- [ ] No obvious errors or glitches

## Screenshot Naming

Use descriptive filenames:

```
xai-wallet-screenshot-1-dashboard.png
xai-wallet-screenshot-2-hardware-wallet.png
xai-wallet-screenshot-3-send-transaction.png
xai-wallet-screenshot-4-mining.png
xai-wallet-screenshot-5-trading.png
```

## Screenshot Storage

Organize screenshots in this directory:

```
store/
├── screenshots/
│   ├── chrome/
│   │   ├── 1-dashboard.png
│   │   ├── 2-hardware-wallet.png
│   │   ├── 3-send-transaction.png
│   │   ├── 4-mining.png
│   │   └── 5-trading.png
│   └── firefox/
│       └── (same as chrome, or Firefox-specific)
```

## Captions for Each Screenshot

### Dashboard
```
Secure wallet dashboard with balance tracking, transaction history, and quick actions
```

### Hardware Wallet
```
Connect Ledger or Trezor hardware wallet for maximum security and cold storage
```

### Send Transaction
```
Create and sign transactions securely with hardware wallet confirmation
```

### Mining
```
Monitor mining status, hashrate, and earnings with easy start/stop controls
```

### Trading
```
Access decentralized exchange for trustless trading without intermediaries
```

## Common Mistakes to Avoid

❌ Using real user data or addresses
❌ Empty or placeholder screens
❌ Low resolution or blurry images
❌ Inconsistent sizing across screenshots
❌ Error messages or broken UI
❌ Personal information visible
❌ Wrong aspect ratio
❌ File size too large
❌ Missing key features
❌ Unprofessional appearance

## Quick Checklist

Before submitting screenshots:

- [ ] All required screenshots captured
- [ ] Correct dimensions (1280x800)
- [ ] Example data only (no real info)
- [ ] Professional quality
- [ ] Key features highlighted
- [ ] Captions written (Firefox)
- [ ] Files organized and named
- [ ] No errors or broken UI visible
- [ ] Consistent styling
- [ ] Under file size limit
