# BitLocker Multi Volume Manager (BitLocker 멀티 볼륨 관리자)

Windows 환경에서 BitLocker로 암호화된 가상 디스크(VHDX 등) 및 분리된 볼륨들을 손쉽게 관리할 수 있는 GUI 도구입니다.

![BitLocker Volume Manager](disk.png)

## 주요 기능

- **볼륨 일괄 관리**: `vault_disk.cfg` 설정을 통해 여러 BitLocker 볼륨(드라이브 문자 및 볼륨 GUID)을 등록하고 콤보박스로 선택하여 제어.
- **실시간 상태 모니터링**: 
  - `언마운트됨` (드라이브 미할당 / 숨김)
  - `마운트됨` (드라이브 할당 / BitLocker 잠김)
  - `정상 마운트됨` (잠금 해제 / 즉시 사용 가능)
- **안전한 마운트 및 잠금 해제**:
  - 비밀번호를 먼저 입력받은 후, 볼륨 GUID를 통해 BitLocker를 **선(先) 잠금 해제**하고 드라이브 문자를 **후(後) 마운트**하여 윈도우 탐색기의 '액세스 거부' 오류 방지.
  - 마운트 완료 시 파일 탐색기 자동 실행.
- **안전한 잠금 및 언마운트**:
  - `manage-bde` 강제 언마운트 및 드라이브 문자 회수(`mountvol /d`).
- **UAC 자동 권한 상승**:
  - 관리자 권한이 필요할 경우 실행 시 UAC 승인 창을 띄워 자동 재실행.

---

## 사전 요구 사항

- **운영체제**: Windows 10 / 11 (Pro 이상, BitLocker 및 PowerShell 지원 환경)
- **실행 권한**: 관리자 권한 (Administrator)

---

## 설정 방법 (`vault_disk.cfg`)

실행 파일(`.exe`) 또는 스크립트(`BitLocker_Vault.py`)와 동일한 디렉터리에 `vault_disk.cfg` 파일을 생성하고 관리할 볼륨 정보를 입력합니다:

```ini
[개인저장소 (X:)]
drive = X:
guid = \\?\Volume{00000000-0000-0000-0000-000000000001}\

[메모리즈 (Z:)]
drive = Z:
guid = \\?\Volume{00000000-0000-0000-0000-000000000002}\
```

> **볼륨 GUID 확인 방법**:  
> 관리자 권한 PowerShell 또는 명령 프롬프트에서 `mountvol` 명령을 실행하면 현재 시스템의 볼륨 GUID 목록을 확인할 수 있습니다.

---

## 실행 및 빌드

### 1. 소스 코드로 직접 실행
```bash
python BitLocker_Vault.py
```

### 2. PyInstaller 단일 실행 파일 패키징
`build.bat`을 실행하거나 아래 명령어를 사용합니다:
```bash
python -m PyInstaller --noconsole --onefile --uac-admin BitLocker_Vault.py
```
빌드 결과물은 `dist/BitLocker_Vault.exe`로 생성됩니다.

### 3. 자체 서명 인증서(Self-Sign) 적용
SmartScreen 경고 최소화 및 실행 안정성을 위해 제공된 PowerShell 스크립트를 관리자 권한으로 실행할 수 있습니다:
```powershell
powershell -ExecutionPolicy Bypass -File .\self-sign.ps1 -ExePath "dist\BitLocker_Vault.exe"
```
