<#
This helper adds read/write permissions for the Codex service account to
`C:\Users\decri\.codex` and all files/subfolders beneath it.

Usage:
1. Save this file where you can run it (e.g., in your project root).
2. Update `$account` so it matches the exact user/service that runs Codex.
3. Run from an elevated PowerShell prompt to grant permissions recursively.
#>

$targetPath = "C:\Users\decri\.codex"
$account = 'jeffs_laptop\\decri'
$rights = "ReadAndExecute", "Write", "Modify"
$inheritance = "ContainerInherit", "ObjectInherit"
$propagation = "None"

$accessRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
    $account,
    $rights,
    $inheritance,
    $propagation,
    "Allow"
)

$applyRule = {
    param ($path)

    try {
        $acl = Get-Acl -Path $path
        $acl.SetAccessRule($accessRule)
        Set-Acl -Path $path -AclObject $acl
    } catch {
        Write-Warning "Could not update permissions on $path : $_"
    }
}

Write-Host "Applying permissions to $targetPath"
$applyRule.Invoke($targetPath)

Get-ChildItem -Path $targetPath -Recurse -Force | ForEach-Object {
    $applyRule.Invoke($_.FullName)
}

Write-Host "Permissions updated. Verify with `Get-Acl $targetPath` or `icacls $targetPath`."
