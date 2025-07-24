import paramiko


def ssh_execute_command(server, command):
    try:
        # initialize ssh client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # connect server
        print(f"connecting {server['hostname']}...")
        ssh.connect(
            server["hostname"],
            username=server["username"],
            password=server["password"]
        )
        
        # sudo
        print(f"execute {command} in {server['hostname']}:")
        stdin, stdout, stderr = ssh.exec_command(command, get_pty=True)
        
        # input passwd
        if "sudo" in command:
            stdin.write(server["password"] + "\n")
            stdin.flush()
        
        # output results
        output = stdout.read().decode()
        error = stderr.read().decode()
        if output:
            print(f"{server['hostname']} output:\n{output}")
        if error:
            print(f"{server['hostname']} error:\n{error}")
        
        # 关闭连接
        ssh.close()
        print(f"close the connection to {server['hostname']}.")
    except Exception as e:
        print(f"incur error when executing ssh command.: {e}")