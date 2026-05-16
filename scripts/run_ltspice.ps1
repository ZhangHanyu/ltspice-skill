param(
  [Parameter(Mandatory = $true)]
  [string]$LtspicePath,

  [Parameter(Mandatory = $true)]
  [string]$InputFile,

  [int]$TimeoutSeconds = 3600,

  [ValidateSet("standard", "fra", "none")]
  [string]$ExpectedOutput = "standard",

  [int]$PollSeconds = 2
)

$ErrorActionPreference = "Stop"

function Resolve-ExistingPathString {
  param([string]$Path)
  return (Resolve-Path -LiteralPath $Path).Path
}

function Get-BasePath {
  param([string]$Path)
  $directory = [System.IO.Path]::GetDirectoryName($Path)
  $stem = [System.IO.Path]::GetFileNameWithoutExtension($Path)
  return [System.IO.Path]::Combine($directory, $stem)
}

function Test-FileLockFree {
  param([string]$Path)
  if (-not (Test-Path -LiteralPath $Path)) { return $false }
  foreach ($access in @([System.IO.FileAccess]::ReadWrite, [System.IO.FileAccess]::Read)) {
    try {
      $stream = [System.IO.File]::Open(
        $Path, [System.IO.FileMode]::Open, $access, [System.IO.FileShare]::None)
      $stream.Dispose()
      return $true
    } catch [System.UnauthorizedAccessException] { continue }
      catch { return $false }
  }
  return $false
}

function Wait-NetlistReady {
  param(
    [string]$Path,
    [datetime]$Deadline,
    [datetime]$NotBefore = [datetime]::MinValue
  )

  while ((Get-Date) -lt $Deadline) {
    $item = Get-Item -LiteralPath $Path -ErrorAction SilentlyContinue
    $isFresh = $item -and $item.LastWriteTime -ge $NotBefore

    if ($isFresh) {
      if (Test-FileLockFree -Path $Path) { return $true }
    }

    Start-Sleep -Seconds $PollSeconds
  }

  return $false
}

function Invoke-Ltspice {
  param(
    [string[]]$Arguments,
    [datetime]$Deadline
  )

  $quotedArguments = @($Arguments | ForEach-Object {
    if ($_ -match '[\s"]') {
      '"' + ($_ -replace '"', '\"') + '"'
    } else {
      $_
    }
  })

  $process = Start-Process -FilePath $script:LtspiceExe -ArgumentList $quotedArguments -PassThru
  $remaining = [int][Math]::Max(1, ($Deadline - (Get-Date)).TotalSeconds)
  Wait-Process -Id $process.Id -Timeout $remaining -ErrorAction SilentlyContinue
  $process.Refresh()

  if (-not $process.HasExited) {
    Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    throw "LTspice process $($process.Id) timed out before returning."
  }
}

function Get-FatalLogLines {
  param(
    [string]$LogPath,
    [datetime]$NotBefore = [datetime]::MinValue
  )

  $patterns = @(
    "Error:",
    "Analysis failed",
    ".TRAN failed",
    "No operating point found",
    "Singular matrix",
    "Time step too small",
    "Undefined model",
    "Could not open input deck"
  )

  $logItem = Get-Item -LiteralPath $LogPath -ErrorAction SilentlyContinue
  if (-not $logItem -or $logItem.LastWriteTime -lt $NotBefore) {
    return @()
  }

  $lines = Get-Content -LiteralPath $LogPath -ErrorAction SilentlyContinue
  return @($lines | Where-Object {
    $line = $_
    $patterns | Where-Object { $line -like "*$_*" }
  })
}

function Wait-SimulationComplete {
  param(
    [string]$BasePath,
    [string]$ExpectedOutput,
    [datetime]$NotBefore,
    [datetime]$Deadline
  )

  $logPath = "$BasePath.log"
  $standardRaw = "$BasePath.raw"
  $resolvedRawPath = $null

  while ((Get-Date) -lt $Deadline) {
    $logItem = Get-Item -LiteralPath $logPath -ErrorAction SilentlyContinue
    $logIsFresh = $logItem -and $logItem.LastWriteTime -ge $NotBefore
    $logText = if ($logIsFresh) { Get-Content -Raw -LiteralPath $logPath -ErrorAction SilentlyContinue } else { "" }
    $hasCompletionMarker = $logText -match "Total elapsed time"
    $fatalLines = @(Get-FatalLogLines -LogPath $logPath -NotBefore $NotBefore)
    if ($fatalLines.Count -gt 0) {
      throw ("LTspice log contains failure indicators:`n" + ($fatalLines -join "`n"))
    }

    if ($ExpectedOutput -eq "none") {
      if ($hasCompletionMarker) {
        return @{ LogPath = $logPath; RawPath = $null }
      }
    } else {
      # Resolve the raw path once on first discovery to avoid re-globbing each poll.
      if (-not $resolvedRawPath) {
        if ($ExpectedOutput -eq "standard") {
          $candidate = Get-Item -LiteralPath $standardRaw -ErrorAction SilentlyContinue
          if ($candidate -and $candidate.LastWriteTime -ge $NotBefore) {
            $resolvedRawPath = $candidate.FullName
          }
        } elseif ($ExpectedOutput -eq "fra") {
          $fraDir  = [System.IO.Path]::GetDirectoryName($BasePath)
          $fraStem = [System.IO.Path]::GetFileName($BasePath)
          $candidate = Get-ChildItem -LiteralPath $fraDir `
            -Filter "${fraStem}.fra_*.raw" -ErrorAction SilentlyContinue |
            Where-Object { $_.LastWriteTime -ge $NotBefore } |
            Sort-Object Name | Select-Object -First 1
          if ($candidate) { $resolvedRawPath = $candidate.FullName }
        }
      }

      if ($resolvedRawPath -and $hasCompletionMarker) {
        # Succeeds the moment LTspice releases the output file handle.
        if (Test-FileLockFree -Path $resolvedRawPath) {
          return @{ LogPath = $logPath; RawPath = $resolvedRawPath }
        }
      }
    }

    Start-Sleep -Seconds $PollSeconds
  }

  $logItem = Get-Item -LiteralPath $logPath -ErrorAction SilentlyContinue
  $rawItem = Get-Item -LiteralPath $standardRaw -ErrorAction SilentlyContinue
  $logExists = $logItem -and $logItem.LastWriteTime -ge $NotBefore
  $rawExists = $rawItem -and $rawItem.LastWriteTime -ge $NotBefore
  if (-not $logExists -and -not $rawExists) {
    throw "Timed out with no .log or .raw output. This looks like an LTspice launch/environment failure."
  }
  if ($logExists) {
    $logText = Get-Content -Raw -LiteralPath $logPath -ErrorAction SilentlyContinue
    if ($logText -notmatch "Total elapsed time") {
      throw "Timed out before '$logPath' contained 'Total elapsed time'. Simulation may still be running or output is incomplete."
    }
  }
  throw "Timed out before expected output stabilized for '$BasePath'."
}

try {
  if ($TimeoutSeconds -le 0) {
    throw "-TimeoutSeconds must be greater than zero."
  }
  if ($PollSeconds -le 0) {
    throw "-PollSeconds must be greater than zero."
  }

  $script:LtspiceExe = Resolve-ExistingPathString $LtspicePath
  $inputPath = Resolve-ExistingPathString $InputFile
  $extension = [System.IO.Path]::GetExtension($inputPath).ToLowerInvariant()
  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)

  if ($extension -eq ".asc") {
    $deckPath = [System.IO.Path]::ChangeExtension($inputPath, ".net")
    $netlistStart = Get-Date
    Invoke-Ltspice -Arguments @("-netlist", $inputPath) -Deadline $deadline
    if (-not (Wait-NetlistReady -Path $deckPath -Deadline $deadline -NotBefore $netlistStart)) {
      throw "Timed out waiting for generated netlist to stabilize: $deckPath"
    }
  } elseif ($extension -eq ".net" -or $extension -eq ".cir") {
    $deckPath = $inputPath
  } else {
    throw "Unsupported input type '$extension'. Use .asc, .net, or .cir."
  }

  $simulationStart = Get-Date
  Invoke-Ltspice -Arguments @("-b", $deckPath) -Deadline $deadline
  $basePath = Get-BasePath $deckPath
  $result = Wait-SimulationComplete -BasePath $basePath -ExpectedOutput $ExpectedOutput -NotBefore $simulationStart -Deadline $deadline
  $fatalLines = @(Get-FatalLogLines -LogPath $result.LogPath -NotBefore $simulationStart)

  if ($fatalLines.Count -gt 0) {
    Write-Error ("LTspice log contains failure indicators:`n" + ($fatalLines -join "`n"))
    exit 1
  }

  Write-Host "LTspice simulation completed."
  Write-Host "Deck: $deckPath"
  Write-Host "Log: $($result.LogPath)"
  if ($result.RawPath) {
    Write-Host "Raw: $($result.RawPath)"
  }
  exit 0
} catch {
  Write-Error $_.Exception.Message
  exit 1
}
