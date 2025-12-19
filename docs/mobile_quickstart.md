# XAI Mobile Quickstart (Text Guide)

Follow these steps to get the mobile scaffold running locally (video still pending):

1) Install dependencies
   - Android: Android Studio (latest), SDK 34, platform tools
   - iOS (macOS): Xcode (latest), CocoaPods (`sudo gem install cocoapods`)
   - Node: 18+ with npm or yarn

2) Clone and install
   ```bash
   cd mobile-app
   npm install
   ```

3) Configure environment
   - Copy `.env.example` to `.env` in `mobile-app`
   - Set `API_BASE_URL` to your node (e.g., `http://localhost:12001`)
   - Set `WS_BASE_URL` to your node WS endpoint (e.g., `ws://localhost:12001/ws`)

4) Run on Android emulator
   ```bash
   npm run android
   ```

5) Run on iOS simulator (macOS)
   ```bash
   cd ios && pod install && cd ..
   npm run ios
   ```

6) Basic verification
   - Wallet view loads and can fetch balance
   - Node status screen shows `healthy: true`
   - Transactions screen can pull latest tx list (read-only)

Security note: never embed production API keys or secrets in the mobile app; use environment variables and remote config.
