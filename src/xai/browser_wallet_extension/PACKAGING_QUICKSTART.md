# Packaging Quick Start - XAI Browser Wallet

Fast reference guide for packaging and submitting the extension.

## Prerequisites

- Extension tested and working
- Privacy policy hosted publicly
- Screenshots captured (3-5 recommended)
- Icons verified (already included)

## Build and Package

### All Platforms

```bash
cd /home/hudson/blockchain-projects/xai/src/xai/browser_wallet_extension

# Build extension
./build.sh

# Package for Chrome
./package-chrome.sh

# Package for Firefox
./package-firefox.sh
```

### Output Files

- `xai-wallet-chrome-v0.2.0.zip` - Upload to Chrome Web Store
- `xai-wallet-firefox-v0.2.0.zip` - Upload to Firefox Add-ons

## Submission URLs

- **Chrome**: https://chrome.google.com/webstore/devconsole
- **Firefox**: https://addons.mozilla.org/developers/

## Required Information

### Chrome Web Store

1. **Extension Package**: xai-wallet-chrome-v0.2.0.zip
2. **Description**: See `store/CHROME_STORE_LISTING.md`
3. **Screenshots**: 1280x800, at least 1 required
4. **Privacy Policy URL**: Must be publicly hosted
5. **Support Email**: Your email address
6. **Category**: Productivity

### Firefox Add-ons

1. **Extension Package**: xai-wallet-firefox-v0.2.0.zip
2. **Description**: See `store/FIREFOX_LISTING.md`
3. **Screenshots**: 1280x800, at least 1 required
4. **Privacy Policy URL**: Must be publicly hosted
5. **Support Email**: Your email address
6. **Source Code URL**: Optional but recommended (GitHub)
7. **Categories**: Other, Web Development

## Permission Justifications

Copy these into the submission forms:

**storage**: Required to save wallet addresses, encrypted keys, and user preferences locally in the browser.

**alarms**: Enables periodic background updates for wallet balance and mining status without persistent connections.

**usb**: Essential for communicating with Ledger hardware wallets via USB protocol for secure transaction signing.

**hid** (optional): Alternative communication method for Trezor hardware wallets and some Ledger models.

**localhost host permissions**: Allows connection to local XAI blockchain nodes for development, testing, and users running their own nodes.

## Review Timeline

- **Chrome**: 1-3 days (typically 1-2 days)
- **Firefox**: 1-7 days (manual review, more thorough)

## Pre-Submission Checklist

- [ ] Version number updated in manifest.json
- [ ] Build completed successfully
- [ ] Package files created
- [ ] Tested as unpacked extension in Chrome
- [ ] Tested as temporary add-on in Firefox
- [ ] Screenshots captured (no sensitive data)
- [ ] Privacy policy hosted and accessible
- [ ] Store listing descriptions prepared
- [ ] Permission justifications written
- [ ] Support contact information ready

## Testing Before Submission

### Chrome

```bash
# Open Chrome
chrome://extensions

# Enable Developer Mode (top right toggle)
# Click "Load unpacked"
# Select: /home/hudson/blockchain-projects/xai/src/xai/browser_wallet_extension/build/
```

### Firefox

```bash
# Open Firefox
about:debugging#/runtime/this-firefox

# Click "Load Temporary Add-on..."
# Select: /home/hudson/blockchain-projects/xai/src/xai/browser_wallet_extension/build/manifest.json
```

## Common Issues

### Build Fails

**Problem**: Script errors or missing files
**Solution**: Check build.sh output, ensure all source files present

### Package Too Large

**Problem**: ZIP file > 5MB (Chrome) or 200MB (Firefox)
**Solution**: Remove unnecessary files, check build output

### Manifest Invalid

**Problem**: Validator rejects manifest
**Solution**: Use `json.tool` to verify JSON syntax, check manifest version

### Icons Missing

**Problem**: Store shows no icon or wrong icon
**Solution**: Verify icons/ directory in package, check manifest.json icon paths

## After Submission

1. Monitor email for review status
2. Respond to reviewer questions promptly
3. Address any rejection reasons
4. Once approved, share store links
5. Monitor user reviews and ratings

## Store Links (After Publication)

- **Chrome**: `chrome://extensions` -> Details -> View in Chrome Web Store
- **Firefox**: `about:addons` -> Extension -> More Information

## Update Process

To release an update:

1. Update version in manifest.json (e.g., 0.2.0 → 0.2.1)
2. Run build.sh and package scripts
3. Upload new package to respective stores
4. Provide release notes
5. Updates typically review faster than initial submission

## Getting Help

- Review PUBLISHING.md for detailed guide
- Check store/CHROME_STORE_LISTING.md for listing details
- Check store/FIREFOX_LISTING.md for AMO details
- Review SECURITY_REVIEW.md for security verification

## Resources

- Chrome: https://developer.chrome.com/docs/webstore/
- Firefox: https://extensionworkshop.com/
- Privacy Policy Template: `store/privacy-policy.md`

---

**Ready to submit? Run the build and package scripts, then upload to the stores!**
