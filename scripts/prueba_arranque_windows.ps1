# Prueba de humo del exe congelado: arranca con PARTES_PRUEBA_DE_ARRANQUE, espera
# a que salga y busca en su registro la marca de ventana principal. Que el exe
# exista no basta (Guardias publicó uno que se cerraba solo a los dos segundos).
# Solo ASCII a proposito: asi da igual con que PowerShell se abra.
#
# Uso: pwsh scripts/prueba_arranque_windows.ps1 -Exe dist/PartesDeSalida/PartesDeSalida.exe

param(
    [Parameter(Mandatory = $true)][string]$Exe,
    [int]$Segundos = 180
)

$ErrorActionPreference = "Stop"
$Logs = Join-Path $env:APPDATA "PartesSalida\logs"
$Marca = "PRUEBA DE ARRANQUE: ventana principal a la vista"
if (-not (Test-Path $Exe)) { Write-Host "[ERROR] No existe $Exe"; exit 1 }
$Exe = (Resolve-Path $Exe).Path
$antes = @()
if (Test-Path $Logs) { $antes = Get-ChildItem $Logs -Filter "app_*.log" | ForEach-Object { $_.FullName } }
$inicio = Get-Date

$env:PARTES_PRUEBA_DE_ARRANQUE = "ventana"
$proceso = Start-Process -FilePath $Exe -WorkingDirectory (Split-Path $Exe) -PassThru
$termino = $proceso.WaitForExit($Segundos * 1000)
Remove-Item Env:PARTES_PRUEBA_DE_ARRANQUE -ErrorAction SilentlyContinue
if (-not $termino) {
    Write-Host "[ERROR] Sigue abierto tras $Segundos s: se da por colgado"
    Stop-Process -Id $proceso.Id -Force -ErrorAction SilentlyContinue
}

$registro = $null
if (Test-Path $Logs) {
    $registro = Get-ChildItem $Logs -Filter "app_*.log" | Sort-Object LastWriteTime | Select-Object -Last 1
}
$llego = $false
if ($null -eq $registro) {
    Write-Host "[ERROR] No hay registro: el proceso no llego a ejecutar Python"
} else {
    Write-Host "=== $($registro.Name) (ultimas 80 lineas) ==="
    Get-Content $registro.FullName -Encoding UTF8 | Select-Object -Last 80 | ForEach-Object { Write-Host $_ }
    $llego = [bool](Select-String -Path $registro.FullName -SimpleMatch $Marca -Quiet)
}
$falta = Join-Path $Logs "faulthandler.log"
if ((Test-Path $falta) -and ((Get-Item $falta).Length -gt 0)) {
    Write-Host "=== faulthandler.log ==="
    Get-Content $falta | Select-Object -Last 60 | ForEach-Object { Write-Host $_ }
}
if ($llego -and $termino -and $proceso.ExitCode -eq 0) {
    Write-Host "[OK] $Marca y salida limpia"
    exit 0
}
Write-Host "[ERROR] El exe no ha llegado a la ventana principal (termino=$termino)"
exit 1
