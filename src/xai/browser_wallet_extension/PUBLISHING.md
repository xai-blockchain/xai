# Publishing Guide - XAI Browser Wallet

Complete guide for publishing the XAI Browser Wallet to Chrome Web Store and Firefox Add-ons.

## Prerequisites

Before starting the submission process:

- [ ] Extension fully tested in target browser
- [ ] All security issues resolved
- [ ] Icons created (16, 32, 48, 128px)
- [ ] Screenshots captured (see store/ICON_REQUIREMENTS.md)
- [ ] Privacy policy hosted publicly (required)
- [ ] Support email/website ready
- [ ] Developer account created (Chrome and/or Firefox)

## Building and Packaging

### 1. Build the Extension

```bash
cd /home/hudson/blockchain-projects/xai/src/xai/browser_wallet_extension
bash build.sh
```

This creates a `build/` directory with production-ready files.

### 2. Package for Chrome

```bash
bash package-chrome.sh
```

Creates `xai-wallet-chrome-v[version].zip` ready for Chrome Web Store.

### 3. Package for Firefox

```bash
bash package-firefox.sh
```

Creates `xai-wallet-firefox-v[version].zip` with Firefox-specific manifest adjustments.

## Chrome Web Store Submission

### Step 1: Create Developer Account

1. Go to [Chrome Web Store Developer Dashboard](https://chrome.google.com/webstore/devconsole)
2. Sign in with Google account
3. Pay one-time $5 registration fee
4. Complete developer profile

### Step 2: Upload Extension

1. Click "New Item" in dashboard
2. Upload `xai-wallet-chrome-v[version].zip`
3. Wait for automated analysis (checks for malware, policy violations)
4. Fix any errors reported by the validator

### Step 3: Store Listing

Fill in all required fields using `store/CHROME_STORE_LISTING.md`:

**Product Details:**
- Extension name: XAI Browser Wallet
- Description: Use detailed description from listing guide
- Category: Productivity
- Language: English

**Privacy:**
- Upload privacy policy link (must be publicly hosted)
- Declare data usage: Financial information, stored locally
- Complete privacy questionnaire

**Assets:**
- Upload 128x128 icon (automatically extracted from extension)
- Upload screenshots (1280x800, at least 1 required)
- Upload promotional images (optional but recommended)

**Distribution:**
- Visibility: Public
- Regions: All regions (or select specific ones)
- Pricing: Free

### Step 4: Justification for Permissions

In the "Justification" section, explain each permission:

**storage**: Required to save wallet addresses, encrypted keys, and user preferences locally in the browser.

**alarms**: Enables periodic background updates for wallet balance and mining status without persistent connections.

**usb**: Essential for communicating with Ledger hardware wallets via USB protocol for secure transaction signing.

**hid** (optional): Alternative communication method for Trezor hardware wallets and some Ledger models.

**host_permissions (localhost)**: Allows connection to local XAI blockchain nodes for development, testing, and users running their own nodes.

### Step 5: Submit for Review

1. Review all information carefully
2. Click "Submit for Review"
3. Initial review typically takes 1-3 days
4. You'll receive email when review is complete

### Step 6: After Approval

- Extension is published to Chrome Web Store
- Users can install from the store page
- You can monitor installs and user reviews in dashboard
- Updates follow the same submission process

## Firefox Add-ons (AMO) Submission

### Step 1: Create Developer Account

1. Go to [Firefox Add-ons Developer Hub](https://addons.mozilla.org/developers/)
2. Sign in with Firefox Account (or create one)
3. Complete developer profile (no registration fee)

### Step 2: Submit Add-on

1. Click "Submit a New Add-on"
2. Choose:
   - "On this site" (recommended for most developers)
   - "On your own" (self-distribution, less visibility)
3. Upload `xai-wallet-firefox-v[version].zip`

### Step 3: Add-on Details

Fill in required information using `store/FIREFOX_LISTING.md`:

**Basic Information:**
- Name: XAI Browser Wallet
- Slug: xai-browser-wallet (used in AMO URL)
- Summary: Short description (250 chars)
- Categories: Other, Web Development

**Version Information:**
- Release notes: What's new in this version
- License: Choose appropriate license
- Source code URL: Link to GitHub/GitLab repository

**Descriptions:**
- Description: Full description from listing guide
- Tags: cryptocurrency, blockchain, wallet, hardware-wallet, etc.

**Support:**
- Homepage URL
- Support email
- Support URL (or GitHub issues)

**Privacy Policy:**
- Privacy policy URL (required, must be publicly hosted)

### Step 4: Upload Screenshots

- At least 1 required, up to 10 allowed
- Recommended size: 1280x800
- Add captions to describe each screenshot
- Drag to reorder (first is primary)

### Step 5: Permissions Justification

Firefox requires detailed explanation for sensitive permissions:

**For USB permission:**
"This permission is required to communicate with Ledger hardware wallets via USB protocol. The extension uses the WebUSB API to securely sign transactions on the hardware device, ensuring private keys never leave the device. This is a core security feature of the wallet."

**For HID permission:**
"This permission enables communication with Trezor hardware wallets using the WebHID API. Like USB, this allows secure transaction signing on the hardware device itself. This is an optional permission users can grant when connecting their Trezor device."

**For localhost host permissions:**
"These permissions allow users to connect the wallet to local XAI blockchain nodes running on their computer. This is essential for developers testing the blockchain and users who prefer to run their own nodes for maximum privacy and decentralization."

### Step 6: Source Code (Important for Firefox)

Firefox may request source code if the review process cannot fully verify your extension:

**If using build tools:**
- Provide link to source repository
- Include build instructions
- Explain any minification or bundling

**For this extension:**
- No build tools used (vanilla JavaScript)
- All files in package are source code
- Can provide GitHub repository link for transparency

### Step 7: Submit for Review

1. Review all information
2. Click "Submit Version"
3. Initial review typically takes 1-7 days
4. More thorough than Chrome due to manual review process

### Step 8: After Approval

- Extension is published on addons.mozilla.org
- Users can install from AMO
- Monitor statistics and reviews in dashboard
- Updates require new submission and review

## Review Process Expectations

### Chrome Web Store

**Timeline**: Usually 1-3 days, can be longer

**Process**:
- Automated scanning for malware and policy violations
- May include manual review for sensitive permissions
- Hardware wallet permissions (USB/HID) may trigger additional review
- Be prepared to provide test credentials

**Common Issues**:
- Unclear permission justifications
- Missing or inadequate privacy policy
- Screenshots not showing key features
- Minified code without source maps (not applicable here)

### Firefox Add-ons

**Timeline**: Usually 1-7 days, can be longer for complex extensions

**Process**:
- Manual code review by Mozilla staff
- Automated security scans
- Permissions carefully scrutinized
- Source code may be requested

**Common Issues**:
- Inadequate permissions justification
- Missing privacy policy
- Source code not accessible
- Use of eval() or remote code (not applicable here)
- Insufficient screenshots or description

## Post-Publication

### Monitoring

**Chrome:**
- Track installs, uninstalls, crash reports in dashboard
- Respond to user reviews
- Monitor for policy violation warnings

**Firefox:**
- View statistics in developer hub
- Respond to user reviews
- Check for review flags or issues

### Updates

**Version Numbering:**
- Follow semantic versioning: MAJOR.MINOR.PATCH
- Example: 0.2.0 → 0.2.1 (bugfix), 0.3.0 (new features)

**Update Process:**
1. Update version in manifest.json
2. Rebuild and repackage extension
3. Submit new version to stores
4. Provide clear release notes
5. Wait for review (usually faster for updates)

**Chrome:**
- Updates pushed automatically to users after approval
- Can control rollout percentage

**Firefox:**
- Updates pushed automatically to users
- Can set minimum Firefox version if needed

### Responding to Reviews

**Best Practices:**
- Respond professionally to all reviews
- Thank users for positive feedback
- Address concerns in negative reviews
- Fix bugs mentioned in reviews
- Update version notes to mention fixed issues

### Handling Policy Violations

If flagged for policy violation:

1. Read the violation notice carefully
2. Address the specific issue mentioned
3. Respond to the review team with explanation
4. Submit updated version if needed
5. Appeal if you believe it's a mistake

## Common Rejection Reasons

### Both Stores

1. **Insufficient Permission Justification**
   - Fix: Provide detailed, specific use cases for each permission

2. **Missing/Inadequate Privacy Policy**
   - Fix: Host privacy-policy.md publicly and link it

3. **Misleading Description**
   - Fix: Accurately describe features, don't overpromise

4. **Poor Quality Screenshots**
   - Fix: Use high-resolution, clear images showing actual features

### Chrome Specific

5. **Requesting Too Many Permissions**
   - Fix: Use optional permissions where possible (we already do this for HID)

6. **Single Purpose Policy**
   - Fix: Ensure extension has one clear purpose (wallet functionality)

### Firefox Specific

7. **Source Code Not Available**
   - Fix: Provide public repository link

8. **Build Process Not Documented**
   - Fix: Include clear build instructions (not applicable - we use vanilla JS)

## Security Hardening Checklist

Before submission, verify:

- [ ] No eval() or Function() constructors
- [ ] No inline scripts in HTML
- [ ] Content Security Policy properly configured
- [ ] No remote code loading
- [ ] All external resources (if any) are from trusted sources
- [ ] Permissions minimized to essential only
- [ ] Private keys encrypted at rest
- [ ] HTTPS used for all network requests
- [ ] Input validation on all user inputs
- [ ] XSS protection via CSP and safe DOM manipulation

Our extension passes all these checks.

## Testing Before Submission

### Chrome

1. Load unpacked extension in chrome://extensions
2. Enable Developer Mode
3. Click "Load unpacked" and select build/ directory
4. Test all features thoroughly
5. Check console for errors
6. Verify permissions are correct

### Firefox

1. Go to about:debugging#/runtime/this-firefox
2. Click "Load Temporary Add-on"
3. Select manifest.json from build/ directory
4. Test all features
5. Check console for errors
6. Verify manifest compatibility

### Hardware Wallet Testing

Both browsers:
- Test Ledger connection and signing
- Test Trezor connection and signing
- Verify USB/HID permissions work
- Test permission grant/deny flows

## Support and Maintenance

### Required Ongoing Tasks

1. **Monitor reviews**: Respond within 1-2 days
2. **Fix bugs**: Release updates promptly for critical issues
3. **Security updates**: Keep dependencies updated (if any)
4. **Policy compliance**: Stay updated on store policies
5. **User support**: Respond to support emails

### Recommended Tools

- **Google Analytics**: Optional (requires disclosure in privacy policy)
- **Sentry**: Error tracking (requires disclosure)
- **GitHub Issues**: Free support ticketing system

## Resources

### Official Documentation

- [Chrome Web Store Developer Documentation](https://developer.chrome.com/docs/webstore/)
- [Chrome Extension Best Practices](https://developer.chrome.com/docs/extensions/mv3/security/)
- [Firefox Extension Workshop](https://extensionworkshop.com/)
- [Firefox Add-on Policies](https://extensionworkshop.com/documentation/publish/add-on-policies/)

### Tools

- [Chrome Extension Manifest Validator](https://chrome-extension-manifest-validator.com/)
- [web-ext](https://github.com/mozilla/web-ext) - Firefox extension CLI tool

### Community

- [Chrome Extension Google Group](https://groups.google.com/a/chromium.org/g/chromium-extensions)
- [Firefox Add-ons Discourse](https://discourse.mozilla.org/c/add-ons/)

## Troubleshooting

### Package Rejected Immediately

**Cause**: Automated scanner found policy violation
**Fix**: Review rejection email, fix specific issue, resubmit

### Review Taking Too Long

**Chrome**: Email chromium-extensions@googlegroups.com after 3+ days
**Firefox**: Post on AMO Discourse or email amo-editors@mozilla.org

### Permission Warnings

**Cause**: Extension requests sensitive permissions
**Fix**: Provide detailed justification in submission form

### Source Code Request (Firefox)

**Cause**: Reviewer cannot verify code
**Fix**: Provide GitHub repository link, explain no build process used

## Quick Reference Commands

```bash
# Build extension
cd /home/hudson/blockchain-projects/xai/src/xai/browser_wallet_extension
bash build.sh

# Package for Chrome
bash package-chrome.sh

# Package for Firefox
bash package-firefox.sh

# Check file sizes
du -sh xai-wallet-*.zip

# Verify package contents
unzip -l xai-wallet-chrome-v*.zip
unzip -l xai-wallet-firefox-v*.zip

# Test in browser
# Chrome: chrome://extensions -> Load unpacked -> select build/
# Firefox: about:debugging -> Load Temporary Add-on -> select build/manifest.json
```

## Final Checklist

Before clicking "Submit":

- [ ] Extension tested in target browser
- [ ] All features working correctly
- [ ] No console errors
- [ ] Icons look good at all sizes
- [ ] Screenshots captured and look professional
- [ ] Privacy policy hosted and linked
- [ ] All store listing fields completed
- [ ] Permission justifications written
- [ ] Support contact information provided
- [ ] Version number updated in manifest
- [ ] Package built and verified
- [ ] Tested as unpacked/temporary extension
- [ ] Hardware wallet features tested (if applicable)
- [ ] No sensitive data in screenshots
- [ ] Release notes written

## After Publication

1. Share the store links:
   - Chrome: `https://chrome.google.com/webstore/detail/[your-extension-id]`
   - Firefox: `https://addons.mozilla.org/firefox/addon/xai-browser-wallet/`

2. Monitor for first reviews and respond promptly
3. Set up analytics (optional, requires privacy policy update)
4. Plan first update based on user feedback
5. Celebrate your published extension!

---

**Questions?** Review the store policies or reach out to developer support for each platform.
