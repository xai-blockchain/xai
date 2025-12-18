# XAI Browser Wallet - Quick Start

One-page guide to get from code to published extension.

## 60-Second Overview

1. Build packages: `./build-all.sh`
2. Host privacy policy publicly
3. Capture 3-5 screenshots
4. Submit to Chrome ($5) and Firefox (free)
5. Wait 1-7 days for approval

## Build Commands

```bash
cd /home/hudson/blockchain-projects/xai/src/xai/browser_wallet_extension

# Build and package everything
./build-all.sh

# Creates:
# - xai-wallet-chrome-v0.2.0.zip (for Chrome Web Store)
# - xai-wallet-firefox-v0.2.0.zip (for Firefox Add-ons)
```

## Before Submitting

### Required
- [ ] Privacy policy hosted at public URL
- [ ] 1-5 screenshots (1280x800)
- [ ] Developer accounts created

### Optional
- [ ] Promotional images (Chrome only)
- [ ] Source code repository (recommended for Firefox)

## Chrome Web Store

**URL**: https://chrome.google.com/webstore/devconsole
**Cost**: $5 one-time fee
**Review**: 1-3 days

**Steps**:
1. Upload `xai-wallet-chrome-v0.2.0.zip`
2. Copy listing text from `store/CHROME_STORE_LISTING.md`
3. Justify permissions (see guide)
4. Upload screenshots
5. Add privacy policy URL
6. Submit

**Full Guide**: `store/CHROME_SUBMISSION_GUIDE.md`

## Firefox Add-ons

**URL**: https://addons.mozilla.org/developers/
**Cost**: Free
**Review**: 1-7 days

**Steps**:
1. Upload `xai-wallet-firefox-v0.2.0.zip`
2. Copy listing text from `store/FIREFOX_LISTING.md`
3. Justify permissions (more detail required)
4. Upload screenshots with captions
5. Add privacy policy URL
6. Provide source code URL (optional)
7. Submit

**Full Guide**: `store/FIREFOX_SUBMISSION_GUIDE.md`

## Screenshots

Capture 3-5 screenshots at 1280x800:

1. Main wallet dashboard
2. Hardware wallet connection
3. Send transaction
4. Mining controls (optional)
5. Trading interface (optional)

**Guide**: `store/SCREENSHOT_GUIDE.md`

## Privacy Policy

Host `store/privacy-policy.md` at a public URL:
- Your website
- GitHub Pages
- Google Docs (public)
- Any accessible URL

## Permissions to Justify

Both stores require explanation for:

- **storage**: Wallet data, encrypted keys
- **alarms**: Background balance updates
- **usb**: Ledger hardware wallet
- **hid**: Trezor hardware wallet
- **localhost**: Local blockchain nodes

Copy justifications from submission guides.

## Common Rejection Reasons

1. Missing/inadequate privacy policy
2. Insufficient permission justification
3. Poor screenshots
4. Unclear description

All covered in the submission guides.

## After Approval

- Chrome: Auto-published, appears in store
- Firefox: Auto-published, appears on AMO

Share your links:
- Chrome: `chrome.google.com/webstore/detail/[id]`
- Firefox: `addons.mozilla.org/firefox/addon/xai-browser-wallet/`

## Testing Before Submission

**Chrome**:
```
1. Go to chrome://extensions
2. Enable Developer Mode
3. Click "Load unpacked"
4. Select build/ directory
```

**Firefox**:
```
1. Go to about:debugging
2. Click "This Firefox"
3. Click "Load Temporary Add-on"
4. Select build/manifest.json
```

## All Documentation

Start with these:
1. `README_PACKAGING.md` - Overview
2. `SUBMISSION_CHECKLIST.md` - Complete checklist
3. `store/CHROME_SUBMISSION_GUIDE.md` - Chrome step-by-step
4. `store/FIREFOX_SUBMISSION_GUIDE.md` - Firefox step-by-step

Then reference:
- `PUBLISHING.md` - Comprehensive guide
- `store/SCREENSHOT_GUIDE.md` - Screenshot creation
- `store/PROMOTIONAL_IMAGES.md` - Promo images
- `SECURITY_REVIEW.md` - Security verification

## Need Help?

Review the guides in this order:
1. This file (QUICKSTART.md)
2. Submission checklist
3. Platform-specific submission guide
4. Comprehensive PUBLISHING.md guide

## Time Estimates

| Task | Time |
|------|------|
| Build packages | 2 minutes |
| Host privacy policy | 5-10 minutes |
| Capture screenshots | 15-30 minutes |
| Create developer accounts | 10-15 minutes |
| Fill Chrome form | 15-30 minutes |
| Fill Firefox form | 20-40 minutes |
| **Total prep** | **1-2 hours** |
| Chrome review | 1-3 days |
| Firefox review | 1-7 days |
| **Total to live** | **2-8 days** |

## Ready to Submit?

Run final check:
```bash
./verify-packaging.sh
```

Should show: ✓ READY FOR SUBMISSION

Then follow submission guides!
