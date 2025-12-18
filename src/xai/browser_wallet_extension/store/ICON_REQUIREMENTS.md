# Icon Requirements for Browser Extension Stores

## Current Icons

Located in `../icons/`:
- icon16.png (16x16)
- icon32.png (32x32)
- icon48.png (48x48)
- icon128.png (128x128)

## Chrome Web Store

### Required Icons

1. **Extension Icons** (already included in manifest.json):
   - 16x16 - Favicon and browser toolbar
   - 32x32 - Windows computers often require this size
   - 48x48 - Extension management page
   - 128x128 - Chrome Web Store and installation

2. **Store Listing Images**:
   - **Small Promo Tile**: 440x280 PNG (optional but recommended)
   - **Large Promo Tile**: 920x680 PNG (optional)
   - **Marquee Promo Tile**: 1400x560 PNG (optional)

3. **Screenshots**:
   - At least 1 screenshot required, up to 5 recommended
   - Recommended size: 1280x800 or 640x400
   - PNG or JPEG format
   - Show key features of the extension

### Design Guidelines

- Use PNG format for icons (transparency supported)
- Icons should be clear and recognizable at all sizes
- Maintain consistent branding across all sizes
- Use simple, bold designs that scale well
- Test visibility on both light and dark backgrounds

## Firefox Add-ons (AMO)

### Required Icons

1. **Extension Icons** (already included in manifest.json):
   - 16x16 - Not displayed, but required by spec
   - 32x32 - Extension management
   - 48x48 - Add-ons Manager and permission prompts
   - 128x128 - AMO listing and installation

2. **Store Listing**:
   - Uses 128x128 icon from manifest automatically
   - No additional promo images required

3. **Screenshots**:
   - At least 1 screenshot required, up to 10 allowed
   - Recommended size: 1280x800 or similar aspect ratio
   - PNG or JPEG format
   - Caption each screenshot

### Design Guidelines

- PNG format recommended for transparency
- SVG support varies (stick with PNG for compatibility)
- Clear visibility at small sizes (32px and below)
- Compatible with Firefox's light and dark themes

## Creating Professional Icons

If you need to improve the current placeholder icons:

### Tools

- **GIMP** (free, cross-platform): Raster graphics
- **Inkscape** (free, cross-platform): Vector graphics
- **Figma** (free web app): Design and export multiple sizes
- **Photopea** (free web app): Photoshop alternative

### Design Tips

1. **Start with vector** (SVG) for scalability
2. **Keep it simple**: Complex details don't scale down well
3. **Test at actual size**: View 16x16 at 100% zoom
4. **Use a grid**: Align elements to pixel grid
5. **Consider context**: How it looks in browser toolbar vs. store

### Quick Icon Creation Workflow

```bash
# If you have SVG source and ImageMagick installed:
convert icon-source.svg -resize 16x16 icon16.png
convert icon-source.svg -resize 32x32 icon32.png
convert icon-source.svg -resize 48x48 icon48.png
convert icon-source.svg -resize 128x128 icon128.png

# Or with Inkscape (better quality):
inkscape icon-source.svg --export-filename=icon16.png -w 16 -h 16
inkscape icon-source.svg --export-filename=icon32.png -w 32 -h 32
inkscape icon-source.svg --export-filename=icon48.png -w 48 -h 48
inkscape icon-source.svg --export-filename=icon128.png -w 128 -h 128
```

## Current Icon Status

The existing icons in `../icons/` are basic placeholders. They meet the technical requirements but may benefit from professional design before store submission.

**Recommendations**:
- Consider hiring a designer or using a service like Fiverr for professional icons
- Ensure icons represent XAI branding consistently
- Create promotional tiles for better store visibility (Chrome)
- Design icons that work on both light and dark backgrounds

## Screenshots

### What to Capture

1. **Main Dashboard**: Clean, populated with example data
2. **Key Features**: Hardware wallet connection, transactions, mining
3. **User Flow**: Show 2-3 steps of common tasks
4. **Professional Look**: Use realistic but not actual user data

### Screenshot Tips

- Use browser zoom to get exact dimensions (e.g., zoom out to fit 1280x800)
- Hide personal information (addresses, balances)
- Use "example" or "demo" mode if available
- Annotate key features with arrows/labels if helpful
- Maintain consistent UI state across screenshots
- Consider dark mode screenshots for one variation

### Creating Screenshots

```bash
# Open extension popup
# Press Ctrl+Shift+I to open DevTools
# Use Device Toolbar (Ctrl+Shift+M) to set exact dimensions
# Take screenshot with browser screenshot tool or:
# Chrome: Capture screenshot button in DevTools
# Firefox: Page Actions > Take a Screenshot
```

## Validation Checklist

Before submission:

- [ ] All required icon sizes present (16, 32, 48, 128)
- [ ] Icons are PNG format with transparency
- [ ] Icons look good at each size (test in browser)
- [ ] Icons work on light and dark backgrounds
- [ ] At least 1 screenshot (3-5 recommended)
- [ ] Screenshots are appropriate dimensions
- [ ] No personal/sensitive data in screenshots
- [ ] Promotional images created (Chrome, optional)
- [ ] Icons match XAI branding
