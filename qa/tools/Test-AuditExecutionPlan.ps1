[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $PlanPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

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

$resolvedPlan = (Resolve-Path -LiteralPath $PlanPath).Path
$plan = Get-Content -LiteralPath $resolvedPlan -Raw | ConvertFrom-Json

if ($plan.schema_version -ne 1 -or $plan.lead_owner -ne 'qa_lead') {
    throw "Execution plan is not a Lead-owned schema version 1 plan."
}
if ($plan.audit_id -notmatch '^[A-Z0-9][A-Z0-9._-]{7,127}$') {
    throw "Execution plan audit ID is invalid."
}
if ($plan.baseline_commit_sha -notmatch '^[0-9a-f]{40}$') {
    throw "Execution plan baseline SHA is invalid."
}
if (-not $plan.authorization.source_only) {
    throw "This validator authorizes source-only plans only."
}
if ($null -ne $plan.execution.runtime_id -or $plan.execution.process_policy -ne 'no_processes' -or $plan.execution.ports.Count -ne 0) {
    throw "Source-only plans cannot allocate runtimes, processes, or ports."
}
if (-not $plan.safety.original_checkout_reference_prohibited -or
    $plan.safety.runtime_access -ne 'prohibited' -or
    $plan.safety.network_access -ne 'prohibited' -or
    $plan.safety.protected_resource_access -ne 'prohibited') {
    throw "Source-only safety controls are incomplete."
}

$snapshotRoot = (Resolve-Path -LiteralPath $plan.source_snapshot.root).Path
$metadataPath = (Resolve-Path -LiteralPath $plan.source_snapshot.metadata_file).Path
if (-not (Test-IsPathWithin -Candidate $metadataPath -Container $snapshotRoot)) {
    throw "Snapshot metadata must be inside the snapshot root."
}
$metadata = Get-Content -LiteralPath $metadataPath -Raw | ConvertFrom-Json
if (-not $metadata.verified -or $metadata.audit_id -ne $plan.audit_id -or
    $metadata.baseline_commit_sha -ne $plan.baseline_commit_sha -or
    $plan.source_snapshot.baseline_commit_sha -ne $plan.baseline_commit_sha -or
    $metadata.untracked_files_included -ne $false -or $metadata.prohibited_path_count -ne 0) {
    throw "Snapshot metadata does not match the Lead execution plan."
}

foreach ($assignment in $plan.execution.specialist_assignments) {
    if ($assignment.verification_mode -ne 'source_inspection' -or $assignment.scenario_ids.Count -eq 0) {
        throw "Every source-only assignment requires source_inspection mode and at least one scenario."
    }
}

[ordered]@{
    valid = $true
    audit_id = $plan.audit_id
    baseline_commit_sha = $plan.baseline_commit_sha
    specialist_assignment_count = $plan.execution.specialist_assignments.Count
    source_snapshot_verified = $true
    stateful_resources_allocated = $false
} | ConvertTo-Json -Depth 4
