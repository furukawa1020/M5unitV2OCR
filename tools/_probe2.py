import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("10.254.239.1", username="m5stack", password="12345678", timeout=10)

def run(cmd):
    _, out, err = client.exec_command(cmd, timeout=15)
    return out.read().decode(errors="replace")

print("=== すべての @app.route ===")
print(run("grep -n '@app.route' /home/m5stack/payload/server_core.py"))

print("\n=== 260-330行 (stream付近) ===")
print(run("sed -n '260,330p' /home/m5stack/payload/server_core.py"))

print("\n=== 395-430行 (main page付近) ===")
print(run("sed -n '395,430p' /home/m5stack/payload/server_core.py"))

client.close()
