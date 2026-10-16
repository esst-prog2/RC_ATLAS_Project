Set-StrictMode -Version Latest

function Test-IsPathWithin {
    param(
        [Parameter(Mandatory = $true)][string] $Candidate,
        [Parameter(Mandatory = $true)][string] $Container
    )

    $candidatePath = [IO.Path]::GetFullPath($Candidate).TrimEnd('\', '/')
    $containerPath = [IO.Path]::GetFullPath($Container).TrimEnd('\', '/')
    return $candidatePath.Equals($containerPath, [StringComparison]::OrdinalIgnoreCase) -or
        $candidatePath.StartsWith($containerPath + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)
}

function Get-SafeRelativePath {
    param(
        [Parameter(Mandatory = $true)][string] $BasePath,
        [Parameter(Mandatory = $true)][string] $TargetPath
    )

    $baseFullPath = [IO.Path]::GetFullPath($BasePath).TrimEnd('\', '/')
    $targetFullPath = [IO.Path]::GetFullPath($TargetPath)
    if (-not (Test-IsPathWithin -Candidate $targetFullPath -Container $baseFullPath)) {
        throw "TargetPath must remain inside BasePath."
    }

    $baseUri = [Uri]($baseFullPath + [IO.Path]::DirectorySeparatorChar)
    $targetUri = [Uri]$targetFullPath
    if ($baseUri.Scheme -ne $targetUri.Scheme) {
        throw "BasePath and TargetPath must use the same URI scheme."
    }

    $relativePath = [Uri]::UnescapeDataString($baseUri.MakeRelativeUri($targetUri).ToString()) -replace '/', [IO.Path]::DirectorySeparatorChar
    if ([IO.Path]::IsPathRooted($relativePath) -or @($relativePath.Split([IO.Path]::DirectorySeparatorChar) | Where-Object { $_ -eq '..' }).Count -gt 0) {
        throw "Calculated relative path is unsafe."
    }
    return $relativePath
}

function Get-ProhibitedPaths {
    param([Parameter(Mandatory = $true)][string[]] $Paths)

    $patterns = @(
        '(^|/)Site\.txt$',
        '(^|/)logitrack_data\.json$',
        '\.bak$',
        '\.(sqlite|sqlite3|db)(-(wal|shm|journal))?$',
        '(^|/)\.env($|\.)',
        '(^|/)(credentials|secrets?)(/|$)'
    )
    return @($Paths | Where-Object {
        $normalized = $_ -replace '\\', '/'
        @($patterns | Where-Object { $normalized -match $_ }).Count -gt 0
    })
}
