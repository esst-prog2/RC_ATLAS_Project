[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $RepositoryRoot,

    [Parameter(Mandatory = $true)]
    [string] $BaselineSha,

    [Parameter(Mandatory = $true)]
    [string] $AuditId,

    [Parameter(Mandatory = $true)]
    [string] $DestinationRoot,

    [switch] $PlanOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$helperPath = Join-Path $PSScriptRoot 'SourceAuditPathHelpers.ps1'
if (-not (Test-Path -LiteralPath $helperPath -PathType Leaf)) {
    throw "Required path helper is missing."
}
. $helperPath

function Invoke-RepositoryGit {
    param([Parameter(Mandatory = $true)][string[]] $Arguments)

    $output = & git -C $script:ResolvedRepositoryRoot @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "git $($Arguments -join ' ') failed: $($output -join [Environment]::NewLine)"
    }
    return @($output)
}

if ($AuditId -notmatch '^[A-Z0-9][A-Z0-9._-]{7,127}$') {
    throw "AuditId must be 8-128 uppercase identifier characters."
}

$script:ResolvedRepositoryRoot = (Resolve-Path -LiteralPath $RepositoryRoot).Path
$gitRoot = ((Invoke-RepositoryGit -Arguments @('rev-parse', '--show-toplevel')) -join "`n").Trim()
if (-not ([IO.Path]::GetFullPath($gitRoot).TrimEnd('\', '/')).Equals(
        [IO.Path]::GetFullPath($script:ResolvedRepositoryRoot).TrimEnd('\', '/'),
        [StringComparison]::OrdinalIgnoreCase)) {
    throw "RepositoryRoot is not the verified Git worktree root."
}

$resolvedBaseline = ((Invoke-RepositoryGit -Arguments @('rev-parse', '--verify', "$BaselineSha^{commit}")) -join "`n").Trim()
if ($resolvedBaseline -notmatch '^[0-9a-f]{40}$') {
    throw "BaselineSha did not resolve to a full commit SHA."
}

$resolvedDestination = [IO.Path]::GetFullPath($DestinationRoot)
if (Test-Path -LiteralPath $resolvedDestination) {
    throw "DestinationRoot already exists; refusing to overwrite it."
}
if (Test-IsPathWithin -Candidate $resolvedDestination -Container $script:ResolvedRepositoryRoot) {
    throw "DestinationRoot must be outside the original checkout."
}
$destinationParent = Split-Path -Parent $resolvedDestination
if (-not (Test-Path -LiteralPath $destinationParent -PathType Container)) {
    throw "DestinationRoot parent does not exist."
}

$trackedPaths = @(Invoke-RepositoryGit -Arguments @('ls-tree', '-r', '--name-only', $resolvedBaseline))
$treeEntries = @(Invoke-RepositoryGit -Arguments @('ls-tree', '-r', $resolvedBaseline))
$unsafeTreeEntries = @($treeEntries | Where-Object { $_ -match '^(120000|160000) ' })
if ($unsafeTreeEntries.Count -gt 0) {
    throw "The committed baseline contains symbolic links or submodules, which require separate snapshot review."
}
$unsafeTrackedPaths = @($trackedPaths | Where-Object {
    $normalized = $_ -replace '\\', '/'
    [IO.Path]::IsPathRooted($normalized) -or @($normalized.Split('/') | Where-Object { $_ -eq '..' }).Count -gt 0
})
if ($unsafeTrackedPaths.Count -gt 0) {
    throw "The committed baseline contains unsafe archive paths: $($unsafeTrackedPaths -join ', ')"
}
$prohibitedTrackedPaths = @(Get-ProhibitedPaths -Paths $trackedPaths)
if ($prohibitedTrackedPaths.Count -gt 0) {
    throw "The committed baseline contains prohibited snapshot paths: $($prohibitedTrackedPaths -join ', ')"
}

$requiredFrameworkPaths = @(
    'qa/README.md',
    'qa/audit_manifest.yaml',
    'qa/oracle_readiness.yaml',
    'qa/protocols/source_snapshot.md',
    'qa/schemas/audit-execution-plan.schema.json',
    'qa/tools/SourceAuditPathHelpers.ps1',
    '.agents/skills/rc-atlas-qa-audit/SKILL.md'
)
$missingFrameworkPaths = @($requiredFrameworkPaths | Where-Object { $_ -notin $trackedPaths })

$plan = [ordered]@{
    schema_version = 1
    audit_id = $AuditId
    baseline_commit_sha = $resolvedBaseline
    source_kind = 'git_archive'
    tracked_path_count = $trackedPaths.Count
    prohibited_tracked_path_count = $prohibitedTrackedPaths.Count
    unsafe_tree_entry_count = $unsafeTreeEntries.Count
    unsafe_tracked_path_count = $unsafeTrackedPaths.Count
    framework_ready = ($missingFrameworkPaths.Count -eq 0)
    missing_framework_paths = $missingFrameworkPaths
    destination_exists = $false
    destination_outside_checkout = $true
}

if ($PlanOnly) {
    $plan | ConvertTo-Json -Depth 5
    if ($missingFrameworkPaths.Count -gt 0) {
        exit 2
    }
    exit 0
}

if ($missingFrameworkPaths.Count -gt 0) {
    throw "The baseline does not contain the required QA framework: $($missingFrameworkPaths -join ', ')"
}

$archivePath = Join-Path $destinationParent (".{0}.{1}.source.tar" -f (Split-Path -Leaf $resolvedDestination), $AuditId)
if (Test-Path -LiteralPath $archivePath) {
    throw "Temporary archive path already exists; refusing to overwrite it."
}

& git -C $script:ResolvedRepositoryRoot archive --format=tar --output=$archivePath $resolvedBaseline
if ($LASTEXITCODE -ne 0) {
    throw "git archive failed."
}

New-Item -ItemType Directory -Path $resolvedDestination | Out-Null
& tar -xf $archivePath -C $resolvedDestination
if ($LASTEXITCODE -ne 0) {
    throw "Snapshot extraction failed; the partial destination was retained for Lead inspection."
}
Remove-Item -LiteralPath $archivePath

$snapshotPaths = @(Get-ChildItem -LiteralPath $resolvedDestination -File -Recurse | ForEach-Object {
    (Get-SafeRelativePath -BasePath $resolvedDestination -TargetPath $_.FullName) -replace '\\', '/'
})
$prohibitedSnapshotPaths = @(Get-ProhibitedPaths -Paths $snapshotPaths)
if ($prohibitedSnapshotPaths.Count -gt 0) {
    throw "Snapshot verification found prohibited paths: $($prohibitedSnapshotPaths -join ', ')"
}

$metadata = [ordered]@{
    schema_version = 1
    audit_id = $AuditId
    baseline_commit_sha = $resolvedBaseline
    source_kind = 'git_archive'
    source_root = '.'
    tracked_path_count = $trackedPaths.Count
    extracted_file_count = $snapshotPaths.Count
    prohibited_path_count = 0
    untracked_files_included = $false
    verified = $true
    generated_at_utc = [DateTime]::UtcNow.ToString('o')
}
$metadata | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $resolvedDestination '.qa-source-snapshot.json') -Encoding utf8
$metadata | ConvertTo-Json -Depth 5
