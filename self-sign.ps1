<#
.사용법
.SYNOPSIS
    자체 서명 인증서를 생성하고 신뢰할 수 있는 루트 저장소에 등록한 뒤, 지정한 exe 파일을 서명합니다.
.EXAMPLE
   . PowerShell을 관리자 권한으로 실행한 후 다음의 명령을 실행
   PS C:\> powershell -ExecutionPolicy Bypass -File .\self-sign.ps1 -ExePath "C:\SecurityDrive\dist\BitLocker_Vault.exe"

   . 정상적으로 서명이 되면 다음과 같이 성공메시지가 보임

   PS C:\> powershell -ExecutionPolicy Bypass -File .\self-sign.ps1 -ExePath "C:\SecurityDrive\dist\BitLocker_Vault.exe"
   대상 파일: C:\SecurityDrive\dist\BitLocker_Vault.exe
   기존에 생성된 인증서를 재사용합니다 (CN=MyCustomSigner).
   실행 파일에 디지털 서명을 적용 중...

   [성공] 서명이 정상적으로 완료되었습니다!
   상태: Valid
   서명자: CN=MyCustomSigner
   PS C:\>
#>

[CmdletBinding()]
param (
    [Parameter(Mandatory = $true, HelpMessage = "서명할 EXE 파일의 전체 경로를 입력하세요.")]
    [string]$ExePath,

    [Parameter(Mandatory = $false)]
    [string]$CertSubject = "MyCustomSigner"
)

# 1. 관리자 권한 확인
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Error "이 스크립트는 '관리자 권한으로 실행'해야 로컬 인증서 저장소에 등록할 수 있습니다."
    exit 1
}

# 2. 파일 경로 유효성 검사
if (-not (Test-Path -Path $ExePath)) {
    Write-Error "지정한 파일을 찾을 수 없습니다: $ExePath"
    exit 1
}

$resolvedExePath = (Resolve-Path $ExePath).Path
Write-Host "대상 파일: $resolvedExePath" -ForegroundColor Cyan

# 3. 기존 인증서 확인 또는 신규 생성
$existingCert = Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert | Where-Object { $_.Subject -match "CN=$CertSubject" } | Select-Object -First 1

if ($null -eq$existingCert) {
    Write-Host "새 코드 서명 인증서를 생성합니다 (CN=$CertSubject)..." -ForegroundColor Yellow
    $cert = New-SelfSignedCertificate `
        -Type CodeSigningCert `
        -Subject "CN=$CertSubject" `
        -CertStoreLocation Cert:\CurrentUser\My `
        -NotAfter (Get-Date).AddYears(5)
    
    # 신뢰할 수 있는 루트 인증 기관(LocalMachine)에 등록
    Write-Host "신뢰할 수 있는 루트 인증 기관에 인증서를 등록합니다..." -ForegroundColor Yellow
    $rootStore = New-Object System.Security.Cryptography.X509Certificates.X509Store "Root", "LocalMachine"
    $rootStore.Open("ReadWrite")
    $rootStore.Add($cert)
    $rootStore.Close()
} else {
    Write-Host "기존에 생성된 인증서를 재사용합니다 (CN=$CertSubject)." -ForegroundColor Green
    $cert =$existingCert
}

# 4. EXE 파일 서명
Write-Host "실행 파일에 디지털 서명을 적용 중..." -ForegroundColor Cyan
$signResult = Set-AuthenticodeSignature -FilePath $resolvedExePath -Certificate $cert

# 5. 서명 결과 검증
if ($signResult.Status -eq "Valid") {
    Write-Host "`n[성공] 서명이 정상적으로 완료되었습니다!" -ForegroundColor Green
    Write-Host "상태: $($signResult.Status)" -ForegroundColor Green
    Write-Host "서명자: $($cert.Subject)" -ForegroundColor Green
} else {
    Write-Warning "`n[주의] 서명 완료 후 검증 상태: $($signResult.Status)"
    Write-Warning "메시지: $($signResult.StatusMessage)"
}