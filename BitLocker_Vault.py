import sys
import os
import ctypes
import subprocess
import time
import configparser
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

def get_base_dir():
    """스크립트 또는 PyInstaller 단일 실행 파일(.exe) 기준 폴더 경로 반환"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))

def load_vault_config(exit_on_missing=True):
    """vault_disk.cfg 파일에서 볼륨 설정 읽어오기. 파일이 없으면 안내 후 종료"""
    cfg_path = os.path.join(get_base_dir(), "vault_disk.cfg")
    
    if not os.path.exists(cfg_path):
        # UI 루트가 없으면 임시 루트 생성 후 에러창 출력
        root_temp = tk.Tk()
        root_temp.withdraw()
        messagebox.showerror(
            "설정 파일 없음", 
            f"설정 파일(vault_disk.cfg)을 찾을 수 없습니다.\n\n경로: {cfg_path}\n\n프로그램을 종료합니다."
        )
        root_temp.destroy()
        if exit_on_missing:
            sys.exit(1)
        return {}

    config = configparser.ConfigParser()
    try:
        config.read(cfg_path, encoding="utf-8")
    except Exception as e:
        root_temp = tk.Tk()
        root_temp.withdraw()
        messagebox.showerror("설정 오류", f"vault_disk.cfg 파일을 읽는 중 오류가 발생했습니다:\n{e}\n\n프로그램을 종료합니다.")
        root_temp.destroy()
        if exit_on_missing:
            sys.exit(1)
        return {}

    vault_dict = {}
    for section in config.sections():
        drive = config.get(section, "drive", fallback="").strip()
        guid = config.get(section, "guid", fallback="").strip()
        if drive and guid:
            vault_dict[section] = {
                "drive": drive,
                "guid": guid
            }

    if not vault_dict and exit_on_missing:
        root_temp = tk.Tk()
        root_temp.withdraw()
        messagebox.showerror("설정 오류", "vault_disk.cfg 파일에 유효한 볼륨 설정 섹션이 없습니다.\n\n프로그램을 종료합니다.")
        root_temp.destroy()
        sys.exit(1)

    return vault_dict

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    """관리자 권한이 없으면 UAC 창을 띄워 관리자 권한으로 재실행"""
    if not is_admin():
        script = os.path.abspath(sys.argv[0])
        params = ' '.join([f'"{arg}"' for arg in sys.argv[1:]])
        
        executable = sys.executable
        if "WindowsApps" in executable or "pythoncore" in executable:
            cmd_args = f'/c python "{script}" {params}'
            ctypes.windll.shell32.ShellExecuteW(None, "runas", "cmd.exe", cmd_args, None, 0)
        else:
            ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, f'"{script}" {params}', None, 1)
            
        sys.exit(0)

class BitLockerMultiManagerApp:
    def __init__(self, root, initial_config):
        self.root = root
        self.root.title("BitLocker 멀티 볼륨 관리자")
        self.root.geometry("420x350")
        self.root.resizable(False, False)

        self.vault_config = initial_config

        self.setup_ui()
        self.on_vault_selected()

    def setup_ui(self):
        container = ttk.Frame(self.root, padding=20)
        container.pack(fill=tk.BOTH, expand=True)

        # 1. 대상 볼륨 선택 콤보박스
        ttk.Label(container, text="제어할 볼륨 선택:", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 5))
        
        self.vault_keys = list(self.vault_config.keys())
        default_val = self.vault_keys[0] if self.vault_keys else ""
        self.selected_key_var = tk.StringVar(value=default_val)
        
        self.combo_vaults = ttk.Combobox(
            container, 
            textvariable=self.selected_key_var, 
            values=self.vault_keys, 
            state="readonly",
            font=("Segoe UI", 10)
        )
        self.combo_vaults.pack(fill=tk.X, pady=(0, 15))
        self.combo_vaults.bind("<<ComboboxSelected>>", self.on_vault_selected)

        # 2. 볼륨 세부 정보 표시 카드
        info_frame = ttk.LabelFrame(container, text="볼륨 상태 정보", padding=10)
        info_frame.pack(fill=tk.X, pady=(0, 15))

        self.lbl_drive_letter = ttk.Label(info_frame, text="할당 드라이브: -", font=("Segoe UI", 9))
        self.lbl_drive_letter.pack(anchor="w", pady=2)

        self.status_var = tk.StringVar(value="상태 확인 중...")
        self.status_label = ttk.Label(
            info_frame, 
            textvariable=self.status_var, 
            font=("Segoe UI", 9, "bold"), 
            foreground="#555555"
        )
        self.status_label.pack(anchor="w", pady=2)

        # 3. 제어 버튼 영역
        btn_frame = ttk.Frame(container)
        btn_frame.pack(fill=tk.X, pady=(0, 5))

        self.btn_mount = ttk.Button(
            btn_frame, 
            text="선택 볼륨 마운트 및 잠금 해제", 
            command=self.mount_drive
        )
        self.btn_mount.pack(fill=tk.X, pady=4, ipady=3)

        self.btn_unmount = ttk.Button(
            btn_frame, 
            text="선택 볼륨 잠금 및 언마운트", 
            command=self.unmount_drive
        )
        self.btn_unmount.pack(fill=tk.X, pady=4, ipady=3)

        self.btn_refresh = ttk.Button(
            btn_frame, 
            text="설정 다시 읽기 및 새로고침", 
            command=self.reload_config_and_status
        )
        self.btn_refresh.pack(fill=tk.X, pady=4)

    def reload_config_and_status(self):
        """실행 중 새로고침 시 파일이 삭제되었으면 경고 후 안내"""
        new_config = load_vault_config(exit_on_missing=False)
        if not new_config:
            messagebox.showwarning("주의", "vault_disk.cfg 파일이 없거나 유효한 볼륨 설정이 없습니다.")
            return

        self.vault_config = new_config
        self.vault_keys = list(self.vault_config.keys())
        self.combo_vaults["values"] = self.vault_keys
        
        current = self.selected_key_var.get()
        if current not in self.vault_keys and self.vault_keys:
            self.selected_key_var.set(self.vault_keys[0])
            self.combo_vaults.config(state="readonly")
        
        self.on_vault_selected()

    def get_current_vault(self):
        key = self.selected_key_var.get()
        return self.vault_config.get(key)

    def on_vault_selected(self, event=None):
        vault = self.get_current_vault()
        if vault:
            self.lbl_drive_letter.config(text=f"할당 드라이브: {vault['drive']}")
            self.update_status()

    def check_drive_state(self, drive_letter):
        is_mounted = os.path.exists(drive_letter + "\\")
        if not is_mounted:
            return "UNMOUNTED"

        res = subprocess.run(
            ["manage-bde", "-status", drive_letter], 
            capture_output=True, 
            text=True, 
            encoding="cp949",
            errors="ignore",
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        output = res.stdout

        if "잠김" in output or "Locked" in output:
            return "LOCKED"
        elif "잠금 해제됨" in output or "Unlocked" in output:
            return "UNLOCKED"
        return "UNKNOWN"

    def update_status(self):
        vault = self.get_current_vault()
        if not vault:
            return

        drive = vault["drive"]
        state = self.check_drive_state(drive)

        if state == "UNMOUNTED":
            self.status_var.set(f"● 언마운트됨 ({drive} 미할당 / 숨김)")
            self.status_label.config(foreground="#e74c3c")
            self.btn_mount.config(state="normal")
            self.btn_unmount.config(state="disabled")
        elif state == "LOCKED":
            self.status_var.set(f"● 마운트됨 ({drive} 할당 / BitLocker 잠김)")
            self.status_label.config(foreground="#e67e22")
            self.btn_mount.config(state="normal")
            self.btn_unmount.config(state="normal")
        elif state == "UNLOCKED":
            self.status_var.set(f"● 정상 마운트됨 ({drive} 사용 가능)")
            self.status_label.config(foreground="#27ae60")
            self.btn_mount.config(state="disabled")
            self.btn_unmount.config(state="normal")
        else:
            self.status_var.set("● 상태 확인 필요")
            self.status_label.config(foreground="#7f8c8d")

    def mount_drive(self):
        vault = self.get_current_vault()
        if not vault:
            return

        drive = vault["drive"]
        raw_guid = vault["guid"].strip()
        clean_guid = raw_guid.rstrip("\\") + "\\"

        state = self.check_drive_state(drive)

        if state == "UNLOCKED":
            os.startfile(drive + "\\")
            return

        # 1. 비밀번호 먼저 입력받기 (취소 시 마운트 안 함)
        password = simpledialog.askstring("BitLocker 잠금 해제", f"[{drive}] 암호를 입력하세요:", show='*')
        if not password:
            self.update_status()
            return

        # 2. 볼륨 GUID로 BitLocker를 먼저 해제 (탐색기 '액세스 거부' 방지)
        target_point = drive if state == "LOCKED" else clean_guid
        escaped_password = password.replace("`", "``").replace('"', '`"').replace("$", "`$")
        
        ps_cmd = (
            f'$sec = ConvertTo-SecureString -String "{escaped_password}" -AsPlainText -Force; '
            f'Unlock-BitLocker -MountPoint "{target_point}" -Password $sec'
        )

        res_unlock = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
            capture_output=True,
            text=True,
            encoding="cp949",
            errors="ignore",
            creationflags=subprocess.CREATE_NO_WINDOW
        )

        # 3. 언마운트 상태였다면 이제 잠금이 풀린 볼륨에 드라이브 문자 할당
        if state == "UNMOUNTED":
            cmd_mount = ["mountvol", drive, clean_guid]
            res_mount = subprocess.run(
                cmd_mount, 
                capture_output=True, 
                text=True, 
                encoding="cp949",
                errors="ignore",
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            if res_mount.returncode != 0:
                messagebox.showerror("오류", f"드라이브 문자 할당 실패 ({drive}):\n{res_mount.stderr or res_mount.stdout}")
                self.update_status()
                return

        # 4. 볼륨 상태가 UNLOCKED로 인식될 때까지 대기 (최대 3초)
        unlocked = False
        for _ in range(6):
            if self.check_drive_state(drive) == "UNLOCKED":
                unlocked = True
                break
            time.sleep(0.5)

        # 5. 결과 판정: 팝업 없이 바로 파일 탐색기 열기
        if unlocked:
            os.startfile(drive + "\\")
        else:
            # 실패 시 남아있는 드라이브 문자 회수
            subprocess.run(["mountvol", drive, "/d"], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            
            output_msg = res_unlock.stderr.strip() if res_unlock.stderr.strip() else res_unlock.stdout.strip()
            if not output_msg:
                output_msg = "암호가 올바르지 않거나 잠금 해제에 실패했습니다."

            messagebox.showerror(
                "잠금 해제 실패", 
                f"암호가 일치하지 않거나 볼륨을 해제하지 못했습니다.\n\n[상세 내용]\n{output_msg}"
            )

        self.update_status()

    def unmount_drive(self):
        vault = self.get_current_vault()
        if not vault:
            return

        drive = vault["drive"]

        # 1. BitLocker 잠금 및 볼륨 강제 분리
        cmd_lock = ["manage-bde", "-lock", drive, "-ForceDismount"]
        res_lock = subprocess.run(
            cmd_lock, 
            capture_output=True, 
            text=True, 
            encoding="cp949",
            errors="ignore",
            creationflags=subprocess.CREATE_NO_WINDOW
        )

        if res_lock.returncode != 0:
            if "액세스가 거부되었습니다" in res_lock.stderr or "Access is denied" in res_lock.stderr:
                messagebox.showerror("권한 오류", "관리자 권한이 필요합니다.")
                return
            else:
                retry = messagebox.askyesno(
                    "사용 중", 
                    f"[{drive}] 볼륨 내 파일이나 폴더를 사용 중인 프로그램이 있습니다.\n강제로 드라이브 문자를 분리하시겠습니까?\n\n{res_lock.stdout or res_lock.stderr}"
                )
                if not retry:
                    return

        # 2. 드라이브 문자 분리
        cmd_unmount = ["mountvol", drive, "/d"]
        res_unmount = subprocess.run(
            cmd_unmount, 
            capture_output=True, 
            text=True, 
            encoding="cp949",
            errors="ignore",
            creationflags=subprocess.CREATE_NO_WINDOW
        )

        if res_unmount.returncode != 0:
            messagebox.showwarning("주의", f"드라이브 문자 분리 실패 ({drive}):\n{res_unmount.stderr or res_unmount.stdout}")

        # 성공 시 팝업 없이 상태 라벨만 갱신
        self.update_status()

if __name__ == "__main__":
    run_as_admin()
    
    # 시작 시 설정 파일 유무 검사 및 없으면 경고 후 종료
    initial_vault_config = load_vault_config(exit_on_missing=True)

    root = tk.Tk()
    app = BitLockerMultiManagerApp(root, initial_vault_config)
    root.mainloop()