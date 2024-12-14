import os
import json
import struct
import subprocess
import sys
sys.path.append('../../key')
from crypto_utils import encrypt_message, decrypt_message

# 定义数据传输的缓冲区大小
bufferSize = 2048
# 定义整数类型的字节大小
intSize = struct.calcsize('I')

class CommandHandler:
    # 初始化命令处理器
    def __init__(self, server):
        self.server = server
        # 不需要参数的命令
        self.no_args_commands = {
            'pwd': self.handle_pwd,
            'ls': self.handle_list,
            'list': self.handle_list,
            'dir': self.handle_list,
            'whoami': self.handle_whoami,
            'userlist': self.handle_userlist,
            'home': self.handle_home,
            'quit': self.handle_quit
        }
        # 需要参数的命令
        self.args_commands = {
            'login': self.handle_login,
            'register': self.handle_register,
            'cd': self.handle_cd,
            'get': self.handle_get,
            'put': self.handle_put,
            'mkdir': self.handle_mkdir,
            'rm': self.handle_delete,
            'passwd': self.handle_change_password,
            'promote': self.handle_promote,
            'demote': self.handle_demote,
            'deleteuser': self.handle_deleteuser,
            'help': self.handle_help,
            'chat': self.handle_chat
        }
        # 无需登录即可使用的命令
        self.no_login_commands = {'login', 'register', 'help'}

    # 处理客户端发送的命令
    def handle_command(self, command):
        try:
            # 解析命令和参数
            parts = command.split()
            if not parts:
                return
                
            cmd = parts[0].lower()
            args = parts[1:]

            # 检查命令是否存在
            if cmd not in self.no_args_commands and cmd not in self.args_commands:
                self.server.send_message(b'Unknown command')
                return

            # 检查是否需要登录
            if not self.server.username and cmd not in self.no_login_commands:
                self.server.send_message(b'Please login first')
                return

            # 执行命令
            if cmd in self.no_args_commands:
                self.no_args_commands[cmd]()
            else:
                self.args_commands[cmd](args)

        except Exception as e:
            error_msg = f"Command execution failed: {str(e)}"
            self.server.log_with_user(error_msg, level='error')
            self.server.send_message(error_msg.encode())

    # 显示当前目录下的文件和文件夹列表
    def handle_list(self):
        try:
            # 获取当前目录下所有文件和文件夹
            files_and_dirs = os.listdir(self.server.current_directory)
            file_info_list = []
            
            # 遍历并收集每个项目的信息
            for item in files_and_dirs:
                full_path = os.path.join(self.server.current_directory, item)
                # 判断是文件还是文件夹
                if os.path.isfile(full_path):
                    file_type = "File"
                    size = os.path.getsize(full_path)  # 获取文件大小
                else:
                    file_type = "Folder"
                    size = None

                # 添加到文件信息列表
                file_info_list.append({
                    "name": item,
                    "type": file_type,
                    "size": size
                })

            # 将文件信息转换为JSON并发送给客户端
            msg = json.dumps(file_info_list).encode()
            self.server.send_message(msg)
            self.server.log_with_user("Listed files successfully.", level='info')

        except Exception as e:
            msg = b'error'
            self.server.send_message(msg)
            self.server.log_with_user(f"Error listing files: {e}", level='error')

    # 切换当前工作目录
    def handle_cd(self, args):
        # 检查参数
        if not args:
            self.server.send_message(b'Usage: cd <directory>')
            return
            
        path = " ".join(args)
        try:
            # 规范化路径格式
            path = os.path.normpath(path).replace('/', '\\')
            full_path = os.path.join(self.server.current_directory, path)
            
            # 验证并切换目录
            if os.path.isdir(full_path):
                self.server.current_directory = full_path
                msg = b'success'
                self.server.send_message(msg)
                self.server.log_with_user(f"Changed directory to: {full_path}", level='info')
            else:
                raise FileNotFoundError
        except FileNotFoundError:
            msg = '目录不存在！'
            self.server.send_message(msg)
            self.server.log_with_user(f"Directory not found: {path}", level='warning')
        except Exception as e:
            msg = b'error'
            self.server.send_message(msg)
            self.server.log_with_user(f"Error changing directory: {e}", level='error')

    # 处理用户登录请求
    def handle_login(self, args):
        # 检查登录参数
        if len(args) < 2:
            self.server.send_message(b'Usage: login <username> <password>')
            return

        username, password = args
        # 验证用户身份
        success, is_admin = self.server.db.verify_user(username, password)
        
        if success:
            # 设置用户信息和工作目录
            self.server.username = username
            self.server.is_admin = is_admin
            user_dir = os.path.join(os.getcwd(), 'Users', username)
            os.makedirs(user_dir, exist_ok=True)
            self.server.current_directory = user_dir
            self.server.send_message(b'Login successful')
        else:
            self.server.send_message(b'Login failed')

    # 处理用户注册请求
    def handle_register(self, args):
        if len(args) < 2:
            self.server.send_message(b'Usage: register <username> <password>')
            return

        username, password = args
        try:
            if self.server.db.add_user(username, password):
                msg = b'Registration successful'
                self.server.log_with_user(f"User {username} registered successfully.", level='info')
            else:
                msg = b'Username already exists'
                self.server.log_with_user(f"Registration failed: Username {username} already exists.", level='warning')
        except Exception as e:
            msg = b'error'
            self.server.log_with_user(f"Registration error for {username}: {e}", level='error')
        finally:
            self.server.send_message(msg)

    # 处理文件下载请求
    def handle_get(self, args):
        # 检查参数
        if len(args) < 1:
            self.server.send_message(b'Usage: get <filename>')
            return

        filename = args[0]
        file_path = os.path.join(self.server.current_directory, filename)
        if not os.path.isfile(file_path):
            self.server.send_message(b'File not found')
            return

        try:
            # 计算文件的MD5值
            process = subprocess.run(['certutil', '-hashfile', file_path, 'MD5'], 
                                   capture_output=True, text=True)
            md5_hash = process.stdout.split('\n')[1].strip()
            
            # 获取文件大小并发送文件信息
            file_size = os.path.getsize(file_path)
            self.server.send_message(f'ok|{md5_hash}'.encode())
            self.server.client_socket.sendall(struct.pack('I', file_size))

            # 分块读取并发送文件内容
            with open(file_path, 'rb') as f:
                sent = 0
                while sent < file_size:
                    data = f.read(bufferSize)
                    if not data:
                        break
                    # 加密并发送数据块
                    encrypted_data = encrypt_message(data.decode('latin-1'))
                    encrypted_block_size = struct.pack('I', len(encrypted_data))
                    self.server.client_socket.sendall(encrypted_block_size + encrypted_data)
                    sent += len(data)

            self.server.log_with_user(f"Sent file: {filename}", level='info')
        except Exception as e:
            self.server.log_with_user(f"Error sending file {filename}: {e}", level='error')
            raise

    # 处理文件上传请求
    def handle_put(self, args):
        # 检查参数
        if len(args) < 2:
            self.server.send_message(b'Usage: put <filename> <md5>')
            return

        filename = args[0]
        client_md5 = args[1]
        try:
            # 准备用户目录
            user_dir = os.path.join(os.getcwd(), 'Users', self.server.username)
            os.makedirs(user_dir, exist_ok=True)
            file_path = os.path.join(user_dir, filename)

            self.server.send_message(b'Ready to receive file')

            # 接收文件大小
            buffer = self.server.client_socket.recv(intSize)
            
            file_size = struct.unpack('I', buffer)[0]
            received = 0

            # 接收并写入文件内容
            with open(file_path, 'wb') as fp:
                while received < file_size:
                    # 接收数据块大小
                    block_size_data = self.server.client_socket.recv(4)
                    block_size = struct.unpack('I', block_size_data)[0]
                    
                    # 接收加密的数据块
                    encrypted_content = b''
                    while len(encrypted_content) < block_size:
                        chunk = self.server.client_socket.recv(min(block_size - len(encrypted_content), 8192))
                        encrypted_content += chunk

                    # 解密并写入数据
                    decrypted_content = decrypt_message(encrypted_content)
                    fp.write(decrypted_content.encode('latin-1'))
                    received += len(decrypted_content)

            # 验证文件MD5
            process = subprocess.run(['certutil', '-hashfile', file_path, 'MD5'], 
                                   capture_output=True, text=True)
            server_md5 = process.stdout.split('\n')[1].strip()

            if server_md5.lower() == client_md5.lower():
                self.server.send_message(b'ok')
                self.server.log_with_user(f"Received file: {filename}", level='info')
            else:
                self.server.send_message(b'MD5 verification failed')
                os.remove(file_path)  # 校验失败删除文件
                self.server.log_with_user(f"MD5 verification failed for file: {filename}", level='error')

        except Exception as e:
            error_msg = f"Error receiving file {filename}: {str(e)}"
            self.server.log_with_user(error_msg, level='error')
            if os.path.exists(file_path):
                os.remove(file_path)
            self.server.send_message(b'fail')
            raise

    # 显示当前工作目录
    def handle_pwd(self):
        msg = self.server.current_directory.encode()
        self.server.send_message(msg)

    # 创建新目录
    def handle_mkdir(self, args):
        # 检查参数
        if len(args) < 1:
            self.server.send_message(b'Usage: mkdir <directory>')
            return

        dirname = args[0]
        try:
            # 创建目录
            dir_path = os.path.join(self.server.current_directory, dirname)
            os.mkdir(dir_path)
            msg = b'success'
            self.server.send_message(msg)
            self.server.log_with_user(f"Created directory: {dir_path}", level='info')
        except FileExistsError:
            msg = '文件夹已存在！'
            self.server.send_message(msg)
            self.server.log_with_user(f"Directory already exists: {dir_path}", level='warning')
        except Exception as e:
            msg = b'error'
            self.server.send_message(msg)
            self.server.log_with_user(f"Error creating directory {dir_path}: {e}", level='error')

    # 删除文件
    def handle_delete(self, args):
        # 检查参数
        if len(args) < 1:
            self.server.send_message(b'Usage: del <filename>')
            return

        filename = args[0]
        try:
            # 删除文件
            file_path = os.path.join(self.server.current_directory, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
                msg = b'success'
                self.server.log_with_user(f"File deleted: {file_path}", level='info')
            else:
                msg = '文件不存在！'
                self.server.log_with_user(f"File not found: {file_path}", level='warning')
        except Exception as e:
            msg = b'error'
            self.server.log_with_user(f"Error deleting file {filename}: {e}", level='error')
        finally:
            self.server.send_message(msg)

    # 返回用户主目录
    def handle_home(self):
        # 获取用户主目录路径
        user_dir = os.path.join(os.getcwd(), 'Users', self.server.username)
        if os.path.exists(user_dir):
            self.server.current_directory = user_dir
            msg = b'success'
            self.server.send_message(msg)
            self.server.log_with_user(f"Changed to home directory: {user_dir}", level='info')
        else:
            msg = b'error'
            self.server.send_message(msg)
            self.server.log_with_user(f"Home directory not found: {user_dir}", level='warning')

    # 修改用户密码
    def handle_change_password(self, args):
        # 检查参数
        if len(args) != 2:
            self.server.send_message(b'Usage: passwd <old_password> <new_password>')
            return

        old_password, new_password = args
        try:
            # 验证并更新密码
            if self.server.db.change_password(self.server.username, old_password, new_password):
                self.server.send_message(b'success')
                self.server.log_with_user(f"Password changed for user {self.server.username}", level='info')
            else:
                self.server.send_message('密码验证失败！')
                self.server.log_with_user(f"Failed to change password for user {self.server.username}: Invalid old password", level='warning')
        except Exception as e:
            error_msg = f"error: {str(e)}"
            self.server.log_with_user(error_msg, level='error')
            self.server.send_message(error_msg.encode())

    # 显示所有用户列表（仅管理员）
    def handle_userlist(self):
        # 检查权限
        if not self.server.is_admin:
            self.server.send_message(b'Permission denied')
            return

        try:
            # 获取并格式化用户列表
            users = self.server.db.get_all_users()
            user_list = [f"{user[0]} - {'Admin' if user[1] == 1 else 'User'}" for user in users]
            response = '\n'.join(user_list)
            self.server.send_message(response.encode())
        except Exception as e:
            self.server.log_with_user(f"Error getting user list: {e}", level='error')
            self.server.send_message(b'error')

    # 提升用户为管理员（仅管理员）
    def handle_promote(self, args):
        # 检查参数
        if len(args) < 1:
            self.server.send_message(b'Usage: promote <username>')
            return

        # 检查权限
        if not self.server.is_admin:
            self.server.send_message(b'Permission denied')
            return

        username = args[0]
        try:
            # 提升用户权限
            if self.server.db.promote_user(username):
                msg = f'{username} 已被添加到管理员组！'.encode()
                self.server.log_with_user(f"User {username} promoted to admin", level='info')
        except Exception as e:
            msg = b'error'
            self.server.log_with_user(f"Error promoting user {username}: {e}", level='error')
        finally:
            self.server.send_message(msg)

    # 降级管理员为普通用户（仅管理员）
    def handle_demote(self, args):
        # 检查参数
        if len(args) < 1:
            self.server.send_message(b'Usage: demote <username>')
            return

        # 检查权限
        if not self.server.is_admin:
            self.server.send_message(b'Permission denied')
            return

        username = args[0]
        try:
            # 降级用户权限
            if self.server.db.demote_user(username):
                msg = f'{username} 已被添加到普通用户组！'
                self.server.log_with_user(f"User {username} demoted to normal user", level='info')
        except Exception as e:
            msg = b'error'
            self.server.log_with_user(f"Error demoting user {username}: {e}", level='error')
        finally:
            self.server.send_message(msg)

    # 删除用户（仅管理员）
    def handle_deleteuser(self, args):
        # 检查参数
        if len(args) < 1:
            self.server.send_message(b'Usage: deleteuser <username>')
            return

        # 检查权限
        if not self.server.is_admin:
            self.server.send_message(b'Permission denied')
            return

        username = args[0]
        try:
            # 删除用户
            if self.server.db.delete_user(username):
                msg = f'{username} 已被删除！'
                self.server.log_with_user(f"User {username} deleted successfully", level='info')
        except Exception as e:
            msg = 'error'
            self.server.log_with_user(f"Error deleting user {username}: {e}", level='error')
        finally:
            self.server.send_message(msg)

    # 显示当前用户身份信息
    def handle_whoami(self):
        # 检查是否已登录
        if self.server.username:
            # 获取并发送用户角色信息
            role = 'Admin' if self.server.is_admin else 'User'
            response = f'{role}/{self.server.username}'.encode()
            self.server.send_message(response)
        else:
            msg = '未登录！'
            self.server.send_message(msg)

    # 处理聊天消息
    def handle_chat(self, args):
        # 检查参数
        if not args:
            self.server.send_message(b'Usage: chat <message>')
            return


    # 处理客户端退出
    def handle_quit(self):
        try:
            self.server.send_message(b'Goodbye!')
            self.server.client_socket.close()
        except Exception as e:
            self.server.log_with_user(f"Error during quit: {e}", level='error')

    # 显示帮助信息
    def handle_help(self, args):
        # 定义所有可用命令的帮助信息
        help_text = {
            'login': 'login <username> <password> - 登录到FTP服务器',
            'register': 'register <username> <password> - 注册新用户账号',
            'ls': 'ls/list/dir - 显示当前目录下的文件和文件夹',
            'cd': 'cd <directory> - 切换到指定目录',
            'get': 'get <filename> - 下载文件（自动进行MD5校验）',
            'put': 'put - 上传文件（自动进行MD5校验）',
            'pwd': 'pwd - 显示当前工作目录的完整路径',
            'mkdir': 'mkdir <directory> - 在当前目录下创建新文件夹',
            'rm': 'rm <filename> - 删除指定的文件或空目录',
            'home': 'home - 返回到用户的主目录',
            'passwd': 'passwd - 修改当前用户的密码',
            'whoami': 'whoami - 显示当前登录用户的身份信息',
            'chat': 'chat <message> - 发送聊天消息到服务器',
            'quit': 'quit - 退出FTP客户端',
            # 管理员命令
            'userlist': 'userlist - [管理员] 查看所有注册用户',
            'promote': 'promote <username> - [管理员] 将指定用户提升为管理员',
            'demote': 'demote <username> - [管理员] 将指定管理员降级为普通用户',
            'deleteuser': 'deleteuser <username> - [管理员] 删除指定用户账号'
        }

        if not args:
            # 根据用户权限显示命令列表
            if self.server.is_admin:
                # 管理员可以看到所有命令
                commands = list(help_text.values())
            else:
                # 普通用户看不到管理员命令
                commands = [help_text[cmd] for cmd in help_text 
                          if cmd not in ['userlist', 'promote', 'demote', 'deleteuser']]
            
            # 发送命令列表
            response = "\n".join(commands)
            self.server.send_message(response.encode())
        elif args[0] in help_text:
            # 显示特定命令的帮助信息
            if not self.server.is_admin and args[0] in ['userlist', 'promote', 'demote', 'deleteuser']:
                self.server.send_message(b'Permission denied')
            else:
                self.server.send_message(help_text[args[0]].encode())
        else:
            self.server.send_message(b'Unknown command')
