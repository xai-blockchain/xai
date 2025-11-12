$env:PYTHONPATH = 'C:\Users\decri\GitClones\Crypto;C:\Users\decri\GitClones\Crypto\aixn' 
if ($args.Count -eq 0) {
    Write-Host "Usage: .\run-python.ps1 <script> [args]"
    exit 1
}

python $args
