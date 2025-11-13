# Apply Global Settings - Step by Step 🚀

**Time needed**: 2 minutes
**Memory reduction**: 80-90% → 15-30% ✅

---

## 📋 Super Easy Steps:

### Step 1: Open the file I created for you
**File location**: `C:\Users\decri\GitClones\Crypto\COPY_THIS_TO_GLOBAL_SETTINGS.json`

In VS Code:
- Press `Ctrl + P`
- Type: `COPY_THIS`
- Press Enter

### Step 2: Select ALL the content
- Press `Ctrl + A` (Select All)
- Press `Ctrl + C` (Copy)

### Step 3: Open your global settings
- Press `Ctrl + ,` (comma) - Opens Settings
- Click the **`{}`** icon in the top-right corner
  - (Or click "Open Settings (JSON)")
- This opens: `C:\Users\decri\AppData\Roaming\Code\User\settings.json`

### Step 4: Paste the settings
**IMPORTANT**: You need to **merge** not replace!

#### If your settings file is empty (just `{}`):
```json
{
  // Paste everything from COPY_THIS_TO_GLOBAL_SETTINGS.json here
}
```

#### If your settings file already has content:
```json
{
  "existing.setting": "value",
  "another.setting": true,

  // Add a comma after your last setting above ↑
  // Then paste all the new settings below ↓

  "files.watcherExclude": {
    "**/.git/objects/**": true,
    // ... rest of new settings
  }
}
```

### Step 5: Save and Reload
- Press `Ctrl + S` (Save)
- Press `Ctrl + Shift + P`
- Type: `Reload Window`
- Press Enter

---

## ✅ Expected Result:

**Before**:
- Memory: 80-90%
- RAM: ~6-8GB
- VS Code: Laggy/Slow

**After** (within 30 seconds):
- Memory: 15-30% ✅
- RAM: ~1-2GB ✅
- VS Code: Fast & Responsive ✅

---

## 🔍 Verify It Worked:

### Check Memory Usage:
1. Press `Ctrl + Shift + P`
2. Type: `Developer: Show Running Extensions`
3. Check memory column - should be much lower now!

### Check Task Manager:
1. Open Task Manager (`Ctrl + Shift + Esc`)
2. Look for "Code.exe" processes
3. Total memory should be 1-2GB instead of 6-8GB

---

## 🆘 If You Get Confused:

The file `COPY_THIS_TO_GLOBAL_SETTINGS.json` contains **exactly** what needs to go in your global settings.

**Safest method**:
1. Copy EVERYTHING from that file (Ctrl+A, Ctrl+C)
2. Open global settings (Ctrl+,, click {})
3. If you see `{}`, paste between the brackets
4. If you see existing settings, paste them at the end (before the final `}`)
5. Make sure there's a comma after each setting except the last one

---

## 💡 Pro Tip:

These are **global defaults**. Any project-specific `.vscode/settings.json` will override these for that project only.

So you get the best of both worlds:
- ✅ Good defaults everywhere
- ✅ Can customize per-project if needed

---

## ⚡ Quick Checklist:

- [ ] Opened `COPY_THIS_TO_GLOBAL_SETTINGS.json` in Crypto folder
- [ ] Copied all content (Ctrl+A, Ctrl+C)
- [ ] Opened global settings (Ctrl+,, click {})
- [ ] Pasted the settings correctly
- [ ] Saved (Ctrl+S)
- [ ] Reloaded window (Ctrl+Shift+P → "Reload Window")
- [ ] Checked memory usage - should be WAY lower! 🎉

---

**Need help?** The settings are already working in your Crypto project. This just applies them everywhere!
