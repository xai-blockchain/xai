# Apply VS Code Memory Fixes Globally 🌍

**Goal**: Make these memory optimizations work for ALL your projects

---

## ⚡ Quick Method (2 minutes):

### Step 1: Open Global Settings
```
1. Open VS Code
2. Press: Ctrl + , (comma)
3. Click the "{}" icon in top-right (or click "Open Settings (JSON)")
```

This opens: `C:\Users\decri\AppData\Roaming\Code\User\settings.json`

### Step 2: Add These Settings

Copy and paste this into your **global** settings.json:

```json
{
  // ========================================================================
  // MEMORY OPTIMIZATION - Global Settings
  // ========================================================================

  // File Watching Exclusions (Reduces CPU/Memory by ~40%)
  "files.watcherExclude": {
    "**/.git/objects/**": true,
    "**/.git/subtree-cache/**": true,
    "**/node_modules/**": true,
    "**/.pytest_cache/**": true,
    "**/__pycache__/**": true,
    "**/site/**": true,
    "**/archived_*/**": true,
    "**/.mypy_cache/**": true,
    "**/data/**": true,
    "**/logs/**": true,
    "**/secure_keys/**": true,
    "**/*.log": true,
    "**/.venv/**": true,
    "**/venv/**": true,
    "**/env/**": true,
    "**/.docker/**": true,
    "**/docker/data/**": true
  },

  // Search Exclusions
  "search.exclude": {
    "**/node_modules": true,
    "**/.git": true,
    "**/__pycache__": true,
    "**/site": true,
    "**/.pytest_cache": true,
    "**/.mypy_cache": true,
    "**/archived_*": true,
    "**/data": true,
    "**/logs": true,
    "**/venv": true,
    "**/.venv": true
  },

  // File Explorer Exclusions
  "files.exclude": {
    "**/__pycache__": true,
    "**/.pytest_cache": true,
    "**/.mypy_cache": true,
    "**/*.pyc": true
  },

  // Python Language Server Optimization (MAJOR MEMORY SAVER)
  "python.analysis.memory.keepLibraryAst": false,
  "python.analysis.indexing": false,
  "python.analysis.diagnosticMode": "openFilesOnly",

  // Git Optimization
  "git.autorefresh": false,
  "git.autofetch": false,
  "git.postCommitCommand": "none",

  // TypeScript/JavaScript
  "typescript.disableAutomaticTypeAcquisition": true,
  "typescript.tsserver.maxTsServerMemory": 4096,

  // Editor Performance
  "editor.minimap.enabled": false,
  "editor.suggestOnTriggerCharacters": true,
  "editor.wordBasedSuggestions": "off",

  // Terminal Optimization
  "terminal.integrated.gpuAcceleration": "off",
  "terminal.integrated.rendererType": "dom",

  // Disable Telemetry
  "telemetry.telemetryLevel": "off",

  // Auto-save (optional - remove if you prefer manual save)
  "files.autoSave": "afterDelay",
  "files.autoSaveDelay": 1000
}
```

### Step 3: Reload VS Code
```
Press: Ctrl + Shift + P
Type: "Reload Window"
Press: Enter
```

---

## ✅ Done!

These settings now apply to:
- ✅ Your blockchain project
- ✅ WordPress projects
- ✅ Any future projects
- ✅ All folders you open in VS Code

---

## 🔧 Per-Project Overrides

You can still override these globally for specific projects by adding `.vscode/settings.json` in that project.

**Example**: If you want Git auto-refresh ONLY in one project:

```json
// ProjectFolder/.vscode/settings.json
{
  "git.autorefresh": true  // Overrides global setting for this project only
}
```

---

## 📍 File Locations Summary

| Scope | Location | When It Applies |
|-------|----------|-----------------|
| **Global** (User) | `C:\Users\decri\AppData\Roaming\Code\User\settings.json` | ALL projects |
| **Workspace** | `C:\Users\decri\GitClones\.vscode\settings.json` | Only if you open GitClones folder |
| **Project** | `C:\Users\decri\GitClones\Crypto\.vscode\settings.json` | Only when Crypto folder is open |

---

## 🎯 Precedence Order (if settings conflict):

1. **Project** settings (highest priority)
2. **Workspace** settings
3. **Global** settings (lowest priority)

So you can have global defaults and override them per-project!

---

**Recommendation**: Apply globally, then customize per-project only when needed.
