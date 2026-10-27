# Helpers to drive the real Sprite to Perler.exe through Windows UI Automation (no mouse or
# keyboard use) and capture its window without activating it. Dot-source this file.
Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes, System.Drawing
Add-Type @"
using System; using System.Runtime.InteropServices; using System.Text;
public class WinApi {
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc f, IntPtr l);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr dc, uint f);
  [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr after, int x, int y, int cx, int cy, uint f);
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
  [DllImport("user32.dll")] public static extern IntPtr SendMessage(IntPtr h, uint m, IntPtr w, IntPtr l);
  public struct RECT { public int L, T, R, B; }
  [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr p, EnumProc f, IntPtr l);
  [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern IntPtr SendMessage(IntPtr h, uint m, IntPtr w, string l);
  [DllImport("user32.dll")] public static extern IntPtr GetDlgItem(IntPtr h, int id);
  [DllImport("user32.dll")] public static extern int GetDlgCtrlID(IntPtr h);
}
"@
[WinApi]::SetProcessDPIAware() | Out-Null
$script:AE = [Windows.Automation.AutomationElement]
$script:Scope = [Windows.Automation.TreeScope]

function Get-ProcessWindows($procId) {
  $found = New-Object System.Collections.ArrayList
  $cb = [WinApi+EnumProc]{ param($h, $l)
    $p = 0; [WinApi]::GetWindowThreadProcessId($h, [ref]$p) | Out-Null
    if ($p -eq $procId -and [WinApi]::IsWindowVisible($h)) {
      $sb = New-Object System.Text.StringBuilder 256; [WinApi]::GetWindowText($h, $sb, 256) | Out-Null
      [void]$found.Add([pscustomobject]@{ Handle = $h; Title = $sb.ToString() }) }
    return $true }
  [WinApi]::EnumWindows($cb, [IntPtr]::Zero) | Out-Null
  return $found
}

function Wait-Window($procId, $title, $seconds = 30) {
  $sw = [Diagnostics.Stopwatch]::StartNew()
  while ($sw.Elapsed.TotalSeconds -lt $seconds) {
    $w = Get-ProcessWindows $procId | Where-Object { $_.Title -like $title } | Select-Object -First 1
    if ($w) { return $w.Handle }
    Start-Sleep -Milliseconds 150 }
  throw "window '$title' not found"
}

function Move-Behind($hwnd, $width, $height) {
  # On screen (so it keeps repainting) but behind every other window, never activated:
  # HWND_BOTTOM, SWP_NOACTIVATE.
  [WinApi]::SetWindowPos($hwnd, [IntPtr]1, 0, 0, $width, $height, 0x0010) | Out-Null
}

function Save-Window($hwnd, $path) {
  $r = New-Object WinApi+RECT; [WinApi]::GetWindowRect($hwnd, [ref]$r) | Out-Null
  $bmp = New-Object System.Drawing.Bitmap ($r.R - $r.L), ($r.B - $r.T)
  $g = [System.Drawing.Graphics]::FromImage($bmp); $dc = $g.GetHdc()
  [WinApi]::PrintWindow($hwnd, $dc, 2) | Out-Null; $g.ReleaseHdc($dc); $g.Dispose()
  $bmp.Save($path, [System.Drawing.Imaging.ImageFormat]::Png); $bmp.Dispose()
  return $r
}

function Find-Control($hwnd, $name, $type = $null) {
  $root = $script:AE::FromHandle($hwnd)
  $cond = New-Object Windows.Automation.PropertyCondition($script:AE::NameProperty, $name)
  $all = $root.FindAll($script:Scope::Descendants, $cond)
  foreach ($el in $all) {
    if (-not $type -or $el.Current.ControlType.ProgrammaticName -eq "ControlType.$type") { return $el } }
  return $null
}

function Invoke-Control($hwnd, $name, $type = "Button") {
  $el = Find-Control $hwnd $name $type
  if (-not $el) { throw "control '$name' ($type) not found" }
  $pattern = $null
  if ($el.TryGetCurrentPattern([Windows.Automation.InvokePattern]::Pattern, [ref]$pattern)) { $pattern.Invoke(); return }
  if ($el.TryGetCurrentPattern([Windows.Automation.SelectionItemPattern]::Pattern, [ref]$pattern)) { $pattern.Select(); return }
  if ($el.TryGetCurrentPattern([Windows.Automation.TogglePattern]::Pattern, [ref]$pattern)) { $pattern.Toggle(); return }
  throw "control '$name' cannot be pressed"
}

function Get-ControlRect($hwnd, $name, $type = $null) {
  # Rectangle relative to the window's top-left corner (window capture coordinates).
  $el = Find-Control $hwnd $name $type
  if (-not $el) { return $null }
  $w = New-Object WinApi+RECT; [WinApi]::GetWindowRect($hwnd, [ref]$w) | Out-Null
  $b = $el.Current.BoundingRectangle
  return [pscustomobject]@{ X = [int]($b.X - $w.L); Y = [int]($b.Y - $w.T); W = [int]$b.Width; H = [int]$b.Height }
}

function Save-Shot($hwnd, $dir, $name) {
  # Window capture plus the window-relative rectangle of every control, for callouts.
  Start-Sleep -Milliseconds 700
  Save-Window $hwnd "$dir\$name.png" | Out-Null
  $w = New-Object WinApi+RECT; [WinApi]::GetWindowRect($hwnd, [ref]$w) | Out-Null
  $root = $script:AE::FromHandle($hwnd)
  $items = $root.FindAll($script:Scope::Descendants, [Windows.Automation.Condition]::TrueCondition) | ForEach-Object {
    $b = $_.Current.BoundingRectangle
    if (-not $b.IsEmpty) { [pscustomobject]@{ type = $_.Current.ControlType.ProgrammaticName.Replace("ControlType.", "");
      name = $_.Current.Name; x = [int]($b.X - $w.L); y = [int]($b.Y - $w.T); w = [int]$b.Width; h = [int]$b.Height } } }
  $items | ConvertTo-Json -Depth 3 | Set-Content -Encoding UTF8 "$dir\$name.json"
  "  saved $name"
}

function Set-DialogFile($procId, $title, $path, $button) {
  # Type a path into a Windows file/folder dialog and confirm it (no mouse or keyboard).
  # Uses the dialog's classic child windows: the Edit box of the file name / folder field gets
  # the path (WM_SETTEXT) and the OK/Save button (control ID 1) is clicked (BM_CLICK).
  $d = Wait-Window $procId $title 20
  $edit = [IntPtr]::Zero
  for ($i = 0; $i -lt 40 -and $edit -eq [IntPtr]::Zero; $i++) {
    Start-Sleep -Milliseconds 250
    $edits = New-Object System.Collections.ArrayList
    $cb = [WinApi+EnumProc]{ param($c, $l)
      $sb = New-Object System.Text.StringBuilder 64; [WinApi]::GetClassName($c, $sb, 64) | Out-Null
      if ($sb.ToString() -eq "Edit" -and [WinApi]::IsWindowVisible($c)) { [void]$edits.Add($c) }
      return $true }
    [WinApi]::EnumChildWindows($d, $cb, [IntPtr]::Zero) | Out-Null
    $pick = $edits | Where-Object { [WinApi]::GetDlgCtrlID($_) -in 1001, 1152 } | Select-Object -First 1
    if (-not $pick) { $pick = $edits | Select-Object -Last 1 }
    if ($pick) { $edit = $pick } }
  if ($edit -eq [IntPtr]::Zero) { throw "file name box not found in '$title'" }
  if ($path) { [WinApi]::SendMessage($edit, 0x000C, [IntPtr]::Zero, $path) | Out-Null }  # WM_SETTEXT
  Start-Sleep -Milliseconds 400
  $ok = [WinApi]::GetDlgItem($d, 1)
  if ($ok -eq [IntPtr]::Zero) { throw "confirm button not found in '$title'" }
  [WinApi]::SendMessage($ok, 0x00F5, [IntPtr]::Zero, [IntPtr]::Zero) | Out-Null  # BM_CLICK
}

function Get-AllControls($hwnd) {
  $root = $script:AE::FromHandle($hwnd)
  $root.FindAll($script:Scope::Descendants, [Windows.Automation.Condition]::TrueCondition) |
    ForEach-Object { [pscustomobject]@{ Type = $_.Current.ControlType.ProgrammaticName.Replace("ControlType.", ""); Name = $_.Current.Name } }
}
