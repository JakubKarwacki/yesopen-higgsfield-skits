# Runs a command of this skill in its Docker client environment (docker/Dockerfile): no WSL, nothing installed on
# Windows besides Docker Desktop. The repo is mounted at /skill and Videos at /videos.
#
# usage (from anywhere):
#   scripts\skill.ps1 build                  build the image
#   scripts\skill.ps1 test                   the client tests (gpu/tests)
#   scripts\skill.ps1 gpu status             = python3 gpu/client/gpu.py status
#   scripts\skill.ps1 gpu up --yes
#   scripts\skill.ps1 shell                  a bash inside
#   scripts\skill.ps1 unlock | lock          pull the secrets into the in-memory sidecar with your GitHub account / wipe them
#   scripts\skill.ps1 secret list|set <NAME>|rotate-ssh   change a secret in the secrets repo and reload (others pick it up on their next command)
#   scripts\skill.ps1 nebius-keygen          Nebius: key pair in the volume, prints the public key for Adrian
#   scripts\skill.ps1 nebius-config <json> <publickey-id>   Nebius: settings + key id from Adrian, checks `iam whoami`
#   scripts\skill.ps1 nebius-up [--dry-run]  Nebius: H200 -> H200 preemptible -> H100 on the kept disk, starts ComfyUI (Slack first!)
#   scripts\skill.ps1 nebius-down [--force]  Nebius: stops ComfyUI, DELETES the machine, checks the disk is READY
#   scripts\skill.ps1 nebius <args>         the Nebius CLI with the yesopen-farm profile, e.g. nebius compute disk list
#   scripts\skill.ps1 <any command>         run as is, e.g. scripts\skill.ps1 python3 scripts\fit_lines.py ...
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$compose = @('compose', '-f', (Join-Path $repo 'docker-compose.yml'), 'run', '--rm', 'skill')
$cmd, $rest = $args
$rest = @($rest)   # a single argument must stay an array, or @rest splats it character by character
$file = Join-Path $repo 'docker-compose.yml'
$image = 'yesopen-skill:local'

# The secrets sit in the memory of the `secrets` container, pulled with your GitHub account (you must be a collaborator
# of the private secrets repo). Asked for once; `skill.ps1 lock` or stopping Docker wipes them. Nothing goes to a file.
function Ensure-Secrets {
    docker compose -f $file up -d secrets
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    # fresh = loaded and unchanged in the secrets repo since; somebody's rotation or edit makes this pull them again
    $ErrorActionPreference = 'Continue'; docker compose -f $file exec -T secrets check 2>&1 | Out-Null; $ready = $LASTEXITCODE -eq 0; $ErrorActionPreference = 'Stop'
    if (-not $ready) {
        docker compose -f $file exec secrets unlock
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
}

# The image is always built locally from docker/Dockerfile on first use; nothing is published to or pulled from GitHub.
if ($cmd -notin 'build', 'lock', 'unlock', 'secret', $null) {
    $ErrorActionPreference = 'Continue'; docker image inspect $image 2>&1 | Out-Null; $ErrorActionPreference = 'Stop'
    if ($LASTEXITCODE -ne 0) {
        Write-Host 'no local image yet, building it (first run, a few minutes)' -ForegroundColor Yellow
        docker compose -f $file build skill
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
}

switch ($cmd) {
    'build' { docker compose -f $file build @rest }
    'test'  { & docker @compose python3 -m unittest discover -s gpu/tests @rest }
    'unlock' { Ensure-Secrets }
    'lock'  { docker compose -f $file stop secrets }
    'secret' {
        # update the secrets: list | set <NAME> | rotate-ssh (needs write access to the secrets repo); reloads them after
        docker compose -f $file up -d secrets
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        docker compose -f $file exec secrets secret @rest
    }
    # Nebius needs no sidecar secrets: the service-account key lives in the gpu-home volume (never in the image or on Windows)
    'nebius-keygen' {
        # makes the key pair in the volume (once) and prints the PUBLIC key to send to Adrian
        $sh = 'set -e; d=$YESOPEN_GPU_HOME/nebius; mkdir -p $d; chmod 700 $d; ' +
              'if [ ! -f $d/sa.pem ]; then openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:4096 -out $d/sa.pem 2>/dev/null; chmod 600 $d/sa.pem; fi; ' +
              'openssl rsa -in $d/sa.pem -pubout 2>/dev/null'
        $out = & docker compose -f $file run --rm --no-deps -T skill bash -c $sh
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        $out | Set-Content (Join-Path $HOME 'Downloads\sa-jakub.pub.pem') -Encoding ascii
        $out
        Write-Host "public key also saved to Downloads\sa-jakub.pub.pem - send it to Adrian (never the private key)" -ForegroundColor Yellow
    }
    'nebius-config' {
        # nebius-config <nebius-<name>.json> <publickey-id>: stores the settings with the key id Adrian sent back
        if ($rest.Count -lt 2) { Write-Host 'usage: skill.ps1 nebius-config <nebius-name.json> <publickey-id>'; exit 2 }
        $cfg = Get-Content $rest[0] -Raw | ConvertFrom-Json
        $cfg.public_key_id = $rest[1]
        $cfg | ConvertTo-Json | & docker compose -f $file run --rm --no-deps -T skill bash -c 'mkdir -p $YESOPEN_GPU_HOME/nebius && cat > $YESOPEN_GPU_HOME/nebius/nebius.json'
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        & docker compose -f $file run --rm --no-deps skill nebius iam whoami --format json
    }
    # a Nebius session: the machine is made and deleted by gpu/client/nebius_session.py (the SSH key comes from the sidecar)
    'nebius-up'   { Ensure-Secrets; & docker @compose python3 gpu/client/nebius_session.py up @rest }
    'nebius-down' { Ensure-Secrets; & docker @compose python3 gpu/client/nebius_session.py down @rest }
    'nebius' { & docker compose -f $file run --rm --no-deps skill nebius @rest }
    'gpu'   { Ensure-Secrets; & docker @compose python3 gpu/client/gpu.py @rest }
    'shell' { Ensure-Secrets; & docker @compose bash }
    $null   { Get-Content $PSCommandPath -TotalCount 12 | Select-Object -Skip 1 | ForEach-Object { $_ -replace '^# ?', '' } }
    default { Ensure-Secrets; & docker @compose $cmd @rest }
}
exit $LASTEXITCODE
