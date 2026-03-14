"""UnitV2 セットアップヘルパー - SSH キー登録 + カメラURL確認"""
import sys

try:
    import paramiko
except ImportError:
    print("pip install paramiko")
    sys.exit(1)

HOST = "10.254.239.1"
USER = "m5stack"
PASS = "12345678"

def ssh_run(client, cmd, timeout=10):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace").strip()
    err = stderr.read().decode(errors="replace").strip()
    return out, err

def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"[INFO] SSH接続中: {USER}@{HOST}")
    try:
        client.connect(HOST, username=USER, password=PASS, timeout=10)
    except Exception as e:
        print(f"[ERR] 接続失敗: {e}")
        sys.exit(1)
    print("[OK] SSH接続成功")

    # --- SSH公開鍵を登録 ---
    import os
    key_path = os.path.expanduser("~/.ssh/id_ed25519.pub")
    if os.path.exists(key_path):
        with open(key_path) as f:
            pubkey = f.read().strip()
        out, err = ssh_run(client,
            f"mkdir -p ~/.ssh; "
            f"grep -qF '{pubkey}' ~/.ssh/authorized_keys 2>/dev/null || "
            f"echo '{pubkey}' >> ~/.ssh/authorized_keys; "
            f"chmod 700 ~/.ssh; chmod 600 ~/.ssh/authorized_keys; "
            f"echo DONE")
        if "DONE" in out:
            print("[OK] SSH公開鍵を登録しました (以後パスワード不要)")
        else:
            print(f"[ERR] キー登録失敗: {err}")
    else:
        print("[INFO] 公開鍵ファイルなし (スキップ)")

    # --- server_core.py のルートとポートを確認 ---
    out, _ = ssh_run(client,
        "grep -n 'port\\|Port\\|listen\\|route\\|stream\\|video\\|shot\\|capture\\|app\\.' "
        "/home/m5stack/payload/server_core.py | head -50")
    print("\n[INFO] server_core.py HTTP定義:")
    print(out)

    # --- ポートを確認 ---
    out2, _ = ssh_run(client, "cat /proc/net/tcp | awk 'NR>1{printf \"%d\\n\", strtonum(\"0x\"substr($2,index($2,\":\")+1))}' | sort -nu")
    print("\n[INFO] Listening ポート:")
    print(out2)

    # --- カメラデバイス確認 ---
    out3, _ = ssh_run(client, "ls /dev/video* 2>/dev/null")
    print(f"\n[INFO] カメラデバイス: {out3}")

    client.close()
    print("\n[INFO] 完了")

if __name__ == "__main__":
    main()
