# Submission Checklist - XAI Browser Wallet

Quick checklist for submitting to Chrome Web Store and Firefox Add-ons.

## Pre-Submission Tasks

### Required Before Submission

- [ ] **Host Privacy Policy**
  - Upload `store/privacy-policy.md` to public URL
  - Note the URL for submission forms
  - Must be accessible without login

- [ ] **Capture Screenshots**
  - Take 3-5 screenshots at 1280x800 resolution
  - Show: wallet dashboard, hardware wallet, transactions, mining, trading
  - No personal/sensitive data visible
  - See `store/ICON_REQUIREMENTS.md` for guidelines

- [ ] **Create Developer Accounts**
  - Chrome: https://chrome.google.com/webstore/devconsole ($5 one-time fee)
  - Firefox: https://addons.mozilla.org/developers/ (free)

- [ ] **Update Firefox Gecko ID** (if needed)
  - Edit `package-firefox.sh` line with gecko ID
  - Change `{xai-wallet@example.com}` to your actual ID
  - Format: `{name@yourdomain.com}`

- [ ] **Test Extension**
  - Chrome: Load unpacked extension from build/ directory
  - Firefox: Load temporary add-on from build/manifest.json
  - Test all features work correctly
  - Test hardware wallet connection (if available)

### Build and Package

- [ ] **Run build script**
  ```bash
  ./build.sh
  ```

- [ ] **Package for Chrome**
  ```bash
  ./package-chrome.sh
  ```
  Creates: `xai-wallet-chrome-v0.2.0.zip`

- [ ] **Package for Firefox**
  ```bash
  ./package-firefox.sh
  ```
  Creates: `xai-wallet-firefox-v0.2.0.zip`

- [ ] **Verify packages**
  ```bash
  ./verify-packaging.sh
  ```
  Should show "READY FOR SUBMISSION"

## Chrome Web Store Submission

### 1. Developer Console Setup

- [ ] Sign in at https://chrome.google.com/webstore/devconsole
- [ ] Pay $5 registration fee (one-time)
- [ ] Complete developer profile

### 2. Upload Extension

- [ ] Click "New Item"
- [ ] Upload `xai-wallet-chrome-v0.2.0.zip`
- [ ] Wait for automated validation
- [ ] Fix any errors reported

### 3. Store Listing - Product Details

Copy content from `store/CHROME_STORE_LISTING.md`:

- [ ] **Name**: XAI Browser Wallet
- [ ] **Short description**: (132 chars from listing doc)
- [ ] **Detailed description**: (Full description from listing doc)
- [ ] **Category**: Productivity
- [ ] **Language**: English

### 4. Store Listing - Privacy

- [ ] **Privacy policy URL**: Your hosted URL
- [ ] **Data handling**: Financial information (stored locally)
- [ ] Complete privacy questionnaire:
  - Handles: Financial information
  - Usage: Core functionality only
  - Transmission: Encrypted to user nodes only
  - No selling, no marketing, no third parties

### 5. Store Listing - Assets

- [ ] Upload screenshots (1280x800, at least 1)
- [ ] Icon automatically extracted from package
- [ ] Optional: Upload promotional images (440x280, 920x680)

### 6. Permissions Justification

Copy from `PUBLISHING.md` or use these:

- [ ] **storage**: Save wallet addresses, encrypted keys, preferences locally
- [ ] **alarms**: Periodic balance and mining status updates
- [ ] **usb**: Ledger hardware wallet communication for secure signing
- [ ] **hid** (optional): Trezor hardware wallet communication
- [ ] **localhost**: Connect to local XAI blockchain nodes for dev/testing

### 7. Distribution

- [ ] **Visibility**: Public
- [ ] **Regions**: All regions (or select specific)
- [ ] **Pricing**: Free

### 8. Submit

- [ ] Review all information
- [ ] Click "Submit for Review"
- [ ] Note submission time (expect 1-3 days)
- [ ] Monitor email for review status

## Firefox Add-ons Submission

### 1. Developer Hub Setup

- [ ] Sign in at https://addons.mozilla.org/developers/
- [ ] Create Firefox Account if needed (free)
- [ ] Complete developer profile

### 2. Submit Add-on

- [ ] Click "Submit a New Add-on"
- [ ] Choose "On this site" (recommended)
- [ ] Upload `xai-wallet-firefox-v0.2.0.zip`

### 3. Basic Information

Copy content from `store/FIREFOX_LISTING.md`:

- [ ] **Name**: XAI Browser Wallet
- [ ] **Slug**: xai-browser-wallet
- [ ] **Summary**: (250 chars from listing doc)
- [ ] **Description**: (Full description from listing doc)
- [ ] **Categories**: Other, Web Development
- [ ] **Tags**: cryptocurrency, blockchain, wallet, hardware-wallet, etc.

### 4. Version Information

- [ ] **Version number**: 0.2.0 (auto-detected)
- [ ] **Release notes**: Feature summary from listing doc
- [ ] **License**: Your license (e.g., MIT, GPL-3.0)
- [ ] **Source code URL**: Optional but recommended (GitHub link)

### 5. Support Information

- [ ] **Homepage URL**: Your website
- [ ] **Support email**: Your support email
- [ ] **Support URL**: GitHub issues or support site

### 6. Privacy Policy

- [ ] **Privacy policy URL**: Your hosted URL (required)

### 7. Screenshots

- [ ] Upload at least 1 screenshot (3-5 recommended)
- [ ] Recommended size: 1280x800
- [ ] Add caption to each screenshot
- [ ] Drag to reorder (first is primary)

### 8. Permissions Justification

Provide detailed explanation for each sensitive permission:

- [ ] **usb**: Explain Ledger hardware wallet communication
- [ ] **hid**: Explain Trezor hardware wallet communication
- [ ] **localhost**: Explain local blockchain node access
- [ ] **storage, alarms**: Brief explanation for each

Copy from `store/FIREFOX_LISTING.md` "Manifest Permissions Justification" section.

### 9. Source Code

- [ ] Provide GitHub/GitLab repository URL
- [ ] Note: No build process used (vanilla JavaScript)
- [ ] All files in package are source code

### 10. Submit

- [ ] Review all information
- [ ] Click "Submit Version"
- [ ] Note submission time (expect 1-7 days)
- [ ] Monitor email for review status

## Post-Submission

### Monitor Review Status

- [ ] Check email daily for review updates
- [ ] Respond to reviewer questions within 24 hours
- [ ] Address rejection reasons if any

### After Approval

- [ ] Test installation from store
- [ ] Share store links:
  - Chrome: `https://chrome.google.com/webstore/detail/[extension-id]`
  - Firefox: `https://addons.mozilla.org/firefox/addon/xai-browser-wallet/`
- [ ] Monitor user reviews
- [ ] Respond to user feedback
- [ ] Plan first update based on feedback

## Common Rejection Reasons & Fixes

### Both Stores

- **Insufficient permission justification**
  - Fix: Use detailed justifications from `PUBLISHING.md`

- **Missing/inadequate privacy policy**
  - Fix: Ensure policy is publicly hosted and linked

- **Poor screenshots**
  - Fix: Capture clear 1280x800 images showing features

### Chrome Specific

- **Too many permissions**
  - Fix: Already minimal (storage, alarms, usb, optional hid)

- **Single purpose violation**
  - Fix: Focus description on wallet functionality

### Firefox Specific

- **Source code not accessible**
  - Fix: Provide GitHub repository link

- **Unclear permission use**
  - Fix: Add more detail to permission justifications

## Verification Before Submitting

Run the verification script:

```bash
./verify-packaging.sh
```

Should show:
- ✓ READY FOR SUBMISSION
- Passed: 29
- Warnings: 0
- Failed: 0

## Quick Reference Links

### Documentation
- **Complete Guide**: `PUBLISHING.md`
- **Quick Commands**: `PACKAGING_QUICKSTART.md`
- **Chrome Content**: `store/CHROME_STORE_LISTING.md`
- **Firefox Content**: `store/FIREFOX_LISTING.md`
- **Security Info**: `SECURITY_REVIEW.md`

### Submission URLs
- **Chrome**: https://chrome.google.com/webstore/devconsole
- **Firefox**: https://addons.mozilla.org/developers/

### Support
- **Chrome Docs**: https://developer.chrome.com/docs/webstore/
- **Firefox Docs**: https://extensionworkshop.com/

## Estimated Timeline

| Task | Time Required |
|------|---------------|
| Host privacy policy | 5-10 minutes |
| Capture screenshots | 15-30 minutes |
| Create developer accounts | 10-15 minutes |
| Fill Chrome submission form | 15-30 minutes |
| Fill Firefox submission form | 20-40 minutes |
| **Total prep time** | **1-2 hours** |
| Chrome review | 1-3 days |
| Firefox review | 1-7 days |
| **Total to publication** | **2-8 days after submission** |

## Success Criteria

Your submission is ready when:

✅ All checkboxes in this document are checked
✅ `verify-packaging.sh` passes all checks
✅ Privacy policy is publicly hosted
✅ Screenshots captured and look professional
✅ Developer accounts created and verified
✅ Both packages uploaded successfully
✅ Store listing forms completely filled
✅ Permission justifications detailed and clear

---

**Next**: Submit packages and wait for review. Monitor email for updates.

**Questions**: Review `PUBLISHING.md` for detailed guidance on any step.
