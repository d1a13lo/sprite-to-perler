# Capture every documented state of the real packaged program.
#   powershell -ExecutionPolicy Bypass -File docs\tools\capture_screens.ps1
# Raw screenshots + control positions go to build\docs_raw (not committed); exports used in the
# guide are written to C:\SpriteToBeadPatternDocs (a neutral path, removed by the build script).
param([string]$Exe = "", [string]$Raw = "", [string]$Exports = "C:\SpriteToBeadPatternDocs")
$ErrorActionPreference = "Stop"
$Root = Resolve-Path "$PSScriptRoot\..\.."
. "$PSScriptRoot\uia.ps1"
if (-not $Exe) { $Exe = "$Root\dist\Sprite-to-Bead Pattern\Sprite-to-Bead Pattern.exe" }
if (-not $Raw) { $Raw = "$Root\build\docs_raw" }
$Ex = $Exports  # examples are opened from the neutral folder, so dialogs default to it
New-Item -ItemType Directory -Force $Raw | Out-Null
Remove-Item -Recurse -Force $Exports -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $Exports | Out-Null
Copy-Item "$Root\docs\examples\*" $Exports
$W, $H = 1600, 1000

function Start-App($sprite) {
  $argLine = if ($sprite) { "`"$sprite`"" } else { $null }
  $p = if ($argLine) { Start-Process -FilePath $Exe -ArgumentList $argLine -PassThru } else { Start-Process -FilePath $Exe -PassThru }
  $h = Wait-Window $p.Id "Sprite-to-Bead Pattern"
  Move-Behind $h $W $H
  Start-Sleep -Milliseconds 1500
  return @($p, $h)
}
function Stop-App($p) { $p.CloseMainWindow() | Out-Null; if (-not $p.WaitForExit(15000)) { $p.Kill() } }
function Press($h, $name, $type = "Button", $times = 1) {
  for ($i = 0; $i -lt $times; $i++) { Invoke-Control $h $name $type; Start-Sleep -Milliseconds 350 } }

"1. empty window"
$p, $h = Start-App $null
Save-Shot $h $Raw "01_empty"
Stop-App $p

"2. Pip loaded: overview, zoom, tables, pegboards"
$p, $h = Start-App "$Ex\pip_mushroom.png"
Save-Shot $h $Raw "02_loaded"
Press $h "100%"
Save-Shot $h $Raw "03_zoom_100"
Press $h "Fit"
Press $h "Pegboards" "TabItem"
Save-Shot $h $Raw "06_pegboards"
Press $h "Colors & Perler Supplies" "TabItem"

"3. Adjust Layers"
Press $h "Adjust Layers"
Save-Shot $h $Raw "07_adjust_open"
Press $h "→" "Button" 3
Press $h "↓" "Button" 2
Save-Shot $h $Raw "08_sprite_moved"
Press $h "←" "Button" 14   # two presses past the left edge
Save-Shot $h $Raw "11_sprite_edge"
Press $h "Reset Selected Layer"
Press $h "Bead Rings" "RadioButton"
Press $h "→" "Button" 6
Save-Shot $h $Raw "09_rings_moved"
Press $h "Pegboard Lines" "RadioButton"
Press $h "↓" "Button" 4
Press $h "Pegboards" "TabItem"
Save-Shot $h $Raw "10_lines_off_grid"
Press $h "Colors & Perler Supplies" "TabItem"
Press $h "Reset All Layers"
Save-Shot $h $Raw "12_reset_all"
Press $h "Done"

"4. Generate PNG and Export Charts & CSV"
Press $h "Generate PNG"
Set-DialogFile $p.Id "Save bead pattern PNG" "" "Save"   # default name, in the sprite's folder
Start-Sleep -Seconds 2
Save-Shot $h $Raw "13_png_saved"
Press $h "Export Charts & CSV"
Set-DialogFile $p.Id "Choose where to save*" "" "Select Folder"   # default: the sprite's folder
Start-Sleep -Seconds 3
Save-Shot $h $Raw "14_charts_saved"
Stop-App $p

"5. GIF, solid background, background question, error"
$p, $h = Start-App "$Ex\twinkle_star_animated.gif"
Save-Shot $h $Raw "15_animated_gif"
Stop-App $p
$p, $h = Start-App "$Ex\glob_slime_solid_background.png"
Save-Shot $h $Raw "16_solid_background"
Stop-App $p
$p = Start-Process -FilePath $Exe -ArgumentList "`"$Ex\glob_slime_white_background.png`"" -PassThru
$d = Wait-Window $p.Id "Background color"
Save-Shot $d $Raw "17_background_question"
Invoke-Control $d "Remove outside only"
$h = Wait-Window $p.Id "Sprite-to-Bead Pattern"; Move-Behind $h $W $H; Start-Sleep -Seconds 1
Save-Shot $h $Raw "18_background_outside"
Stop-App $p
$p = Start-Process -FilePath $Exe -ArgumentList "`"$Ex\not_an_image.png`"" -PassThru
$d = Wait-Window $p.Id "Cannot use this file"
Save-Shot $d $Raw "19_error"
Invoke-Control $d "OK"
Start-Sleep -Milliseconds 500
Stop-App $p

"6. Large sprite"
$p = Start-Process -FilePath $Exe -ArgumentList "`"$Ex\dusk_valley_large.png`"" -PassThru
$d = Wait-Window $p.Id "Background color"
Save-Shot $d $Raw "20_keep_every_pixel"
Invoke-Control $d "Keep every pixel"
$h = Wait-Window $p.Id "Sprite-to-Bead Pattern"; Move-Behind $h $W $H
Start-Sleep -Seconds 6
Save-Shot $h $Raw "21_large_loaded"
Press $h "100%"
Start-Sleep -Seconds 2
Save-Shot $h $Raw "22_large_detail"
Stop-App $p
"done"
