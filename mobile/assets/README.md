# XAI Mobile App Assets

## Required Assets

### App Icons

- **icon.png** - Main app icon (1024x1024 px)
  - iOS: Used as the base for all iOS icon sizes
  - Android: Used for adaptive icon fallback

- **adaptive-icon.png** - Android adaptive icon foreground (1024x1024 px)
  - Centered design with safe zone
  - Background color defined in app.json (#1a1a2e)

- **favicon.png** - Web favicon (48x48 px)

### Splash Screen

- **splash.png** - Splash screen image (1284x2778 px recommended)
  - Will be resized to fit various screen sizes
  - Background color defined in app.json (#1a1a2e)

## Design Guidelines

### Brand Colors
- Primary: #6366f1 (Indigo)
- Secondary: #8b5cf6 (Purple)
- Background: #0f0f1a (Dark Navy)
- Surface: #1e1e2e (Dark Gray)

### Logo Design
The XAI logo features:
- A hexagonal shape representing blockchain
- Downward chevron with vertical line (X + AI)
- Gradient from primary to secondary

### Icon Requirements

#### iOS Requirements
- No transparency allowed
- No alpha channel
- Round corners applied automatically

#### Android Requirements
- Adaptive icons support
- Foreground layer with 108dp safe zone (center 72dp)
- Background can be solid color or image

## Generating Assets

Use Expo's asset generation tools:

```bash
# Install eas-cli if needed
npm install -g eas-cli

# Generate icons
npx expo-optimize
```

Or use external tools:
- App Icon Generator: https://appicon.co/
- Figma export with proper sizes
