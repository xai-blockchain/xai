# XAI Wallet Release Process

## Version Numbering

We follow [Semantic Versioning](https://semver.org/):
- **MAJOR.MINOR.PATCH** (e.g., 1.2.3)
- **MAJOR**: Breaking changes or major features
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes, backward compatible

### Build Numbers
- **iOS**: `buildNumber` in app.json (increments with each build)
- **Android**: `versionCode` in app.json (increments with each build)

## Pre-Release Checklist

### Code Quality
- [ ] All tests pass: `npm test`
- [ ] Linting passes: `npm run lint`
- [ ] TypeScript compiles: `npm run typecheck`
- [ ] No high/critical vulnerabilities: `npm audit`

### Feature Verification
- [ ] Create new wallet works
- [ ] Import wallet works
- [ ] Send transaction works
- [ ] Receive (QR display) works
- [ ] Transaction history loads
- [ ] Block explorer functions
- [ ] Biometric auth works (iOS/Android)
- [ ] Deep links work

### Device Testing
- [ ] iOS Simulator (latest iOS)
- [ ] iOS Physical device
- [ ] Android Emulator (API 24+)
- [ ] Android Physical device
- [ ] Tablet layout (if supported)

## Release Steps

### 1. Update Version

```bash
# Update version in package.json and app.json
npm version patch  # or minor/major

# Verify changes
git diff
```

### 2. Update Changelog

Add entry to CHANGELOG.md:
```markdown
## [1.2.3] - 2024-01-15

### Added
- Feature description

### Changed
- Change description

### Fixed
- Bug fix description
```

### 3. Create Release Branch

```bash
git checkout -b release/v1.2.3
git push origin release/v1.2.3
```

### 4. Build for Stores

```bash
# Production builds
eas build --platform all --profile production

# Wait for builds to complete
eas build:list
```

### 5. Test Production Build

Download and test the production build:
- [ ] App launches correctly
- [ ] All features work
- [ ] No debug logs visible
- [ ] Analytics/Sentry connected
- [ ] Push notifications work

### 6. Submit to Stores

```bash
# Submit to App Store and Play Store
eas submit --platform all --profile production

# Or use GitHub Actions
# Go to Actions > Mobile CI/CD > Run workflow
# Select: production, all, submit=true
```

### 7. Store Review

**App Store (iOS):**
- Review typically takes 24-48 hours
- Respond to any reviewer questions promptly
- Monitor App Store Connect for status updates

**Play Store (Android):**
- Review typically takes a few hours to 7 days
- Check Play Console for any policy violations
- Staged rollout recommended (10% -> 50% -> 100%)

### 8. Post-Release

```bash
# Merge release branch
git checkout main
git merge release/v1.2.3
git tag v1.2.3
git push origin main --tags

# Create GitHub release
gh release create v1.2.3 --generate-notes
```

## Hotfix Process

For critical bugs in production:

```bash
# Create hotfix branch from main
git checkout main
git pull
git checkout -b hotfix/v1.2.4

# Fix the issue, then:
npm version patch
# Update CHANGELOG.md
git commit -am "fix: critical bug description"

# Build and submit
eas build --platform all --profile production
eas submit --platform all --profile production
```

## Rollback

If a critical issue is found post-release:

**iOS:**
1. Go to App Store Connect
2. Select the previous version
3. Click "Promote to Production"

**Android:**
1. Go to Play Console
2. Navigate to Releases
3. Halt the current rollout
4. Create a new release with the previous APK

## Store Metadata Updates

Update store listings without a new build:

**iOS (App Store Connect):**
- Screenshots, description, keywords
- Submit for review (no new binary needed)

**Android (Play Console):**
- Edit store listing
- Changes go live immediately (no review)

## Environment Variables

Required secrets in GitHub Actions:
- `EXPO_TOKEN`: Expo access token
- `EXPO_APPLE_ID`: Apple ID email
- `EXPO_APPLE_PASSWORD`: App-specific password
- `GOOGLE_SERVICE_ACCOUNT_KEY`: Play Store service account JSON

## Changelog Format

```markdown
## [Unreleased]

## [1.2.3] - 2024-01-15

### Added
- New feature (#123)

### Changed
- Updated dependency X to v2.0

### Deprecated
- Old API endpoint (use new one)

### Removed
- Unused feature

### Fixed
- Bug in transaction history (#124)

### Security
- Updated crypto library for CVE-2024-XXX
```
