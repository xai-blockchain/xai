# Aura/Paw Exit 192 Fix Guide

**Diagnostic Result:** Go installation works perfectly. Issue is **project-specific**.

---

## Quick Fix Steps

### Step 1: Navigate to Project
```bash
cd /path/to/Aura  # or /path/to/Paw
```

### Step 2: Clean and Tidy
```bash
go clean -cache -testcache -modcache
go mod tidy
go mod download
```

### Step 3: Test Incrementally
```bash
# Test each package one by one
go list ./...  # Lists all packages

# Test first package
go test ./cmd/... -v

# Test next package
go test ./pkg/... -v

# Continue until you find which package causes exit 192
```

### Step 4: Run Debug Script
```bash
# Copy the debug script to Aura/Paw directory
cp /c/Users/decri/GitClones/Crypto/debug_aura_paw.sh /path/to/Aura/
cd /path/to/Aura
chmod +x debug_aura_paw.sh
./debug_aura_paw.sh
```

---

## Common Causes in Projects

### Cause 1: Panic in init() Function

**Check:**
```bash
grep -rn "func init()" . --include="*.go"
```

**Look for:**
- `panic()` calls in `init()`
- File operations that might fail
- Environment variables that don't exist
- Network calls in `init()`

**Example Problem:**
```go
func init() {
    file, err := os.Open("config.yaml")  // Panics if file missing
    if err != nil {
        panic(err)  // ← This causes exit 192
    }
}
```

**Fix:**
```go
func init() {
    // Don't panic in init, just log or set default
    if _, err := os.Stat("config.yaml"); err != nil {
        log.Println("Config not found, using defaults")
        return
    }
}
```

### Cause 2: Package-Level Variable Initialization

**Check:**
```bash
grep -rn "var.*=" . --include="*.go" | grep -v "//"
```

**Look for:**
```go
// These can panic during initialization:
var db = mustConnect()  // ← Panics if connection fails
var config = loadConfig()  // ← Panics if file missing
var client = http.Client{Timeout: -1}  // ← Invalid value
```

**Fix:**
```go
var db *sql.DB
var config *Config

func init() {
    var err error
    db, err = connect()
    if err != nil {
        log.Printf("DB connection failed: %v", err)
        // Don't panic, handle gracefully
    }
}
```

### Cause 3: Import Cycle

**Check:**
```bash
go list -f '{{.ImportPath}} {{.Imports}}' ./...
```

**Look for circular imports:**
```
package A imports package B
package B imports package A
```

**Fix:** Refactor to break the cycle (extract shared code to new package)

### Cause 4: CGO Issues (If Enabled)

**Check:**
```bash
go env CGO_ENABLED
```

**Test without CGO:**
```bash
CGO_ENABLED=0 go test ./...
```

If this works, your C dependencies are the problem.

### Cause 5: Test File Issues

**Check individual test files:**
```bash
# Compile each test file without running
for file in $(find . -name "*_test.go"); do
    echo "Checking: $file"
    go test -c $(dirname $file) 2>&1 | grep -i error
done
```

---

## Isolation Technique

Find the exact package causing the issue:

```bash
# Create a test script
cat > find_bad_package.sh << 'EOF'
#!/bin/bash
for pkg in $(go list ./...); do
    echo "Testing: $pkg"
    if go test "$pkg" 2>&1 | grep -q "exit status 192"; then
        echo "❌ FOUND IT: $pkg"
        exit 0
    fi
done
EOF

chmod +x find_bad_package.sh
./find_bad_package.sh
```

Once you find the bad package:

```bash
# Investigate that package
cd path/to/bad/package

# List all files
ls -la

# Check for init() in that package
grep -n "func init()" *.go

# Try to compile test binary
go test -c -o test.exe

# If compilation succeeds, run the binary manually
./test.exe -test.v
```

---

## Advanced Debugging

### Debug with Delve
```bash
cd /path/to/failing/package
dlv test
```

### Check for Race Conditions
```bash
go test -race ./...
```

### Preserve Work Directory
```bash
go test -work ./...
# This will print: WORK=/tmp/go-build...
# Go to that directory to see what was compiled
```

### Maximum Verbosity
```bash
GODEBUG=gctrace=1 go test -v -x ./...
```

---

## Known Project Issues

### If Aura/Paw use databases:
- Check database connection strings in test files
- Make sure test database is running
- Check for `init()` that connects to DB

### If Aura/Paw use configuration files:
- Check for hardcoded config paths
- Make sure test config files exist
- Check for environment variable requirements

### If Aura/Paw use external services:
- Check for HTTP clients in init()
- Make sure test services are available
- Check for network timeouts

---

## After Finding the Problem

Once you identify the problematic `init()` or package variable:

1. **Move initialization out of init():**
   ```go
   // Before:
   func init() {
       db = mustConnect()
   }

   // After:
   func setupDB() error {
       var err error
       db, err = connect()
       return err
   }

   // Call from TestMain or individual tests
   func TestMain(m *testing.M) {
       if err := setupDB(); err != nil {
           log.Fatal(err)
       }
       os.Exit(m.Run())
   }
   ```

2. **Use lazy initialization:**
   ```go
   var (
       db   *sql.DB
       once sync.Once
   )

   func getDB() *sql.DB {
       once.Do(func() {
           db, _ = connect()
       })
       return db
   }
   ```

3. **Add defensive checks:**
   ```go
   func init() {
       if os.Getenv("SKIP_INIT") != "" {
           return  // Skip for tests
       }
       // ... initialization code
   }
   ```

---

## Testing the Fix

After fixing:

```bash
# Clean everything
go clean -cache -testcache -modcache

# Verify modules
go mod verify

# Test again
go test ./...

# Should see actual test output instead of exit 192
```

---

## Still Stuck?

If none of this works:

1. **Create minimal reproduction:**
   ```bash
   # Copy just the failing package to a new directory
   # Remove all code except the init() and basic structure
   # Test until you find the exact line causing the issue
   ```

2. **Check Go version compatibility:**
   ```bash
   # Check go.mod for required Go version
   cat go.mod | grep "^go "

   # Make sure your Go version matches
   go version
   ```

3. **Ask for help with specifics:**
   - Which package fails?
   - What's in that package's `init()`?
   - Any recent changes before it started failing?

---

**Remember:** Exit 192 = crash during test initialization, before any test code runs.
The problem is in `init()`, package-level `var`, or import statements.
