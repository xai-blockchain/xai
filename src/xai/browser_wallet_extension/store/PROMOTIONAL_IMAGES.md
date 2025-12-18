# Promotional Images - XAI Browser Wallet

Guide for creating promotional images for Chrome Web Store.

## Overview

Chrome Web Store allows optional promotional images to increase visibility and appeal. While not required, they significantly improve your extension's presentation.

## Image Sizes

### Small Promo Tile
- **Size**: 440x280 pixels
- **Format**: PNG
- **Purpose**: Featured in store listings
- **Required**: No (but recommended)

### Large Promo Tile
- **Size**: 920x680 pixels
- **Format**: PNG
- **Purpose**: Featured promotions
- **Required**: No

### Marquee Promo Tile
- **Size**: 1400x560 pixels
- **Format**: PNG
- **Purpose**: Top of store page
- **Required**: No

### Promotional Image (deprecated but still supported)
- **Size**: 1400x560 pixels
- **Format**: PNG
- **Purpose**: Legacy promotional banner

## Design Guidelines

### Branding
- Use XAI brand colors consistently
- Include XAI logo/wordmark
- Match extension icon design
- Professional appearance

### Content
- Extension name prominently displayed
- Key benefit or tagline
- Icon or visual element
- Clean, uncluttered design

### Colors
Suggested XAI wallet colors (customize as needed):
- Primary: #2E7D32 (green - cryptocurrency theme)
- Accent: #FFA000 (amber - warning/attention)
- Dark: #1B5E20 (dark green)
- Text: #FFFFFF (white on dark backgrounds)
- Background: #F5F5F5 or gradient

### Typography
- Clear, readable fonts
- Sans-serif for modern look
- Font size appropriate for image size
- High contrast with background

## Design Concepts

### Concept 1: Security Focus

**Small Promo (440x280)**:
```
[Icon] XAI Browser Wallet
       Hardware Wallet Security for XAI Blockchain
       [Ledger + Trezor logos]
```

**Large Promo (920x680)**:
```
             XAI Browser Wallet

    [Large extension icon]

    Secure • Private • Hardware-Enabled

    ✓ Ledger & Trezor Support
    ✓ Encrypted Local Storage
    ✓ Mining & Trading Built-In
```

**Marquee (1400x560)**:
```
[Icon]  XAI BROWSER WALLET            [Hardware wallet images]

        Your Keys, Your Crypto, Your Control

        Full hardware wallet support • No tracking • Open source
```

### Concept 2: Feature Showcase

**Small Promo (440x280)**:
```
XAI Wallet
[4 feature icons]
Hardware • Mining • Trading • Secure
```

**Large Promo (920x680)**:
```
        XAI Browser Wallet

[Icon]  Hardware Wallet Integration
        Mine XAI from Your Browser
        Decentralized Trading (DEX)
        Military-Grade Encryption

        Download for Chrome & Firefox
```

### Concept 3: Clean Minimal

**Small Promo (440x280)**:
```
                XAI
        [Extension icon]

        Secure XAI Wallet
        with Hardware Support
```

## Creating Promotional Images

### Tools

**GIMP** (Free, desktop):
```bash
sudo apt install gimp
gimp
# File > New > Set dimensions
# Create design
# Export as PNG
```

**Inkscape** (Free, vector):
```bash
sudo apt install inkscape
inkscape
# Create artboard with exact dimensions
# Design with vectors for scalability
# Export as PNG
```

**Canva** (Free, web-based):
1. Go to canva.com
2. Create custom size design
3. Use templates or start from scratch
4. Export as PNG

**Photopea** (Free, web-based):
1. Go to photopea.com
2. File > New > Set dimensions
3. Design your promo image
4. File > Export as PNG

### Design Templates

**Small Promo Template (440x280)**:
```
Background: Gradient (dark green to lighter green)
Top section (60px): Empty padding
Center: Extension icon (128x128)
Below icon: "XAI Browser Wallet" (24px font)
Below text: Tagline (16px font)
Bottom (40px): Feature icons or badges
```

**Large Promo Template (920x680)**:
```
Background: Gradient or solid color
Left side: Extension icon (256x256)
Right side:
  - Title (48px)
  - Tagline (24px)
  - Feature list (20px each)
  - Call to action
Bottom: Decorative element or badges
```

**Marquee Template (1400x560)**:
```
Background: Professional gradient
Left: Icon + Name (large)
Center: Main tagline/benefit
Right: Feature highlights or device mockup
```

## Sample Layout (ASCII Art)

### Small Promo (440x280)
```
╔════════════════════════════════════════════╗
║                                            ║
║           ╔════════════╗                   ║
║           ║    ICON    ║                   ║
║           ║  (128x128) ║                   ║
║           ╚════════════╝                   ║
║                                            ║
║         XAI Browser Wallet                 ║
║    Hardware Security for XAI Blockchain    ║
║                                            ║
║     [Ledger]  [Trezor]  [Secure]          ║
║                                            ║
╚════════════════════════════════════════════╝
```

### Large Promo (920x680)
```
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║                                                            ║
║    ╔════════╗          XAI BROWSER WALLET                 ║
║    ║        ║                                              ║
║    ║  ICON  ║     Secure Cryptocurrency Wallet            ║
║    ║        ║     with Hardware Support                   ║
║    ║ 256px  ║                                              ║
║    ╚════════╝     ✓ Ledger & Trezor Compatible           ║
║                   ✓ Encrypted Local Storage               ║
║                   ✓ Mining Controls                       ║
║                   ✓ DEX Trading                           ║
║                   ✓ Open Source                           ║
║                                                            ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
```

## Asset Checklist

For professional promotional images:

- [ ] Use high-resolution graphics (no pixelation)
- [ ] Maintain consistent branding
- [ ] Include extension name clearly
- [ ] Highlight key benefit or differentiator
- [ ] Use professional colors and fonts
- [ ] Export at exact dimensions
- [ ] Optimize file size (under 1 MB recommended)
- [ ] Test on different backgrounds
- [ ] Verify text is readable
- [ ] Include call-to-action or feature list

## Where to Place Files

```
store/
├── promotional/
│   ├── small-promo-440x280.png
│   ├── large-promo-920x680.png
│   ├── marquee-1400x560.png
│   └── sources/
│       ├── small-promo.xcf (GIMP)
│       └── large-promo.svg (Inkscape)
```

## Quick Creation with ImageMagick

Simple promotional image from extension icon:

```bash
cd store/promotional

# Small promo with icon and text
convert -size 440x280 xc:'#2E7D32' \
  ../icons/icon128.png -geometry +156+40 -composite \
  -pointsize 24 -fill white -gravity south \
  -annotate +0+80 "XAI Browser Wallet" \
  -pointsize 16 -annotate +0+50 "Hardware Security for XAI" \
  small-promo-440x280.png

# Large promo
convert -size 920x680 gradient:'#1B5E20-#2E7D32' \
  ../icons/icon128.png -geometry +100+276 -composite \
  -pointsize 48 -fill white \
  -annotate +300+300 "XAI Browser Wallet" \
  -pointsize 24 \
  -annotate +300+350 "Secure • Private • Hardware-Enabled" \
  large-promo-920x680.png
```

Note: These are basic examples. For best results, use a proper design tool.

## Design Resources

### Fonts
- **Google Fonts** (fonts.google.com): Free fonts
  - Roboto (modern, clean)
  - Open Sans (friendly)
  - Montserrat (professional)

### Icons
- **Font Awesome** (fontawesome.com): Icon library
- **Material Icons** (fonts.google.com/icons): Google's icon set
- **Noun Project** (thenounproject.com): Icon marketplace

### Colors
- **Coolors** (coolors.co): Color palette generator
- **Adobe Color** (color.adobe.com): Color wheel tool

### Inspiration
- **Chrome Web Store**: Browse top extensions for ideas
- **Dribbble** (dribbble.com): Design inspiration
- **Behance** (behance.net): Professional design work

## Testing Promotional Images

Before uploading to Chrome Web Store:

1. **Visual Check**:
   - Text is readable
   - Colors are professional
   - Design is not cluttered
   - Icon is clear

2. **Technical Check**:
   ```bash
   # Verify dimensions
   file small-promo-440x280.png
   # Should show: PNG image data, 440 x 280

   # Check file size
   du -h small-promo-440x280.png
   # Should be under 1 MB
   ```

3. **Preview**:
   - View at actual size (100% zoom)
   - View on different backgrounds
   - Check on light and dark themes

## Optional: Hire a Designer

If design isn't your strength:

**Fiverr** (fiverr.com):
- Search "chrome extension promotional images"
- Price range: $10-50
- Provide: Extension icon, brand colors, key features
- Turnaround: 1-3 days

**99designs** (99designs.com):
- Run a design contest
- Multiple designers submit concepts
- Choose the best one
- Higher cost but more options

**Upwork** (upwork.com):
- Hire a freelance designer
- Good for ongoing design needs

## Quick Start

If you want to submit without promotional images:

1. **Skip promotional images** - They're optional
2. **Use good screenshots** - Focus on these instead
3. **Add promotional images later** - Can update anytime

Promotional images improve visibility but aren't required for approval.

## Summary

- **Small Promo**: 440x280 - Most important, shows in listings
- **Large Promo**: 920x680 - Featured sections
- **Marquee**: 1400x560 - Top of extension page
- **Tools**: GIMP, Inkscape, Canva, or hire designer
- **Content**: Icon + Name + Key benefit/features
- **Optional**: Can launch without them, add later
