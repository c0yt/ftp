# Client.py
import socket
import argparse
import struct
import os
import getpass
from tqdm import tqdm
import sys
sys.path.append('../../key')
from crypto_utils import encrypt_message, decrypt_message, encrypt_login, decrypt_login
import json
from tkinter import filedialog
import tkinter as tk
import threading
import subprocess

# 定义数据传输的缓冲区大小
bufferSize = 2048
# 定义整数类型的字节大小
intSize = struct.calcsize('I')

class FTPClient:
    # 初始化FTP客户端
    def __init__(self, server_ip, port):
        self.server_ip = server_ip
        self.port = port
        self.socket = None
        self.chat_socket = None
        self.username = None

    # 连接到服务器
    def connect(self):
        try:
            # 建立主连接
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server_ip, self.port))
            
            # 建立聊天连接
            self.chat_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.chat_socket.connect((self.server_ip, self.port + 1))
            
            print(f"正在连接{self.server_ip}:{self.port}")
            
            # 启动聊天消息接收线程
            threading.Thread(target=self.handle_chat_messages, daemon=True).start()
            
            return True
        except Exception as e:
            print(f"服务器连接失败！\n{e}")
            return False

    # 处理接收到的聊天消息
    def handle_chat_messages(self):
        while self.chat_socket:
            try:
                message = self.receive_message(is_chat=True)
                if message:
                    # 检查是否被踢出
                    if message == "You have been kicked from the server":
                        print("\n您已被服务器踢出！")
                        try:
                            self.close()  # 安全地关闭连接
                        finally:
                            os._exit(0)  # 强制终止程序
                    print(f"\n{message}")
                    print(f"FTP {self.server_ip}:{self.port}> ", end='', flush=True)
            except Exception:
                break

    # 发送加密消息
    def send_message(self, msg, is_chat=False, use_rsa=False, public_key=None):
        try:
            if isinstance(msg, bytes):
                msg = msg.decode()
            # 根据需要选择加密方式
            if use_rsa:
                encrypted_message = encrypt_login(msg, public_key)
            else:
                encrypted_message = encrypt_message(msg)
                
            # 发送消息长度和加密消息
            msg_length = struct.pack('I', len(encrypted_message))
            
            # 选择使用的socket
            sock = self.chat_socket if is_chat else self.socket
            sock.sendall(msg_length + encrypted_message)
            return True
        except Exception as e:
            if is_chat:
                print(f"发送聊天消息失败！\n{e}")
            else:
                print(f"发送消息失败！\n{e}")
            return False

    # 接收并解密消息
    def receive_message(self, is_chat=False):
        try:
            # 选择使用的socket
            sock = self.chat_socket if is_chat else self.socket
                
            # 接收消息长度
            length = struct.unpack('I', sock.recv(intSize))[0]
            # 接收加密消息
            encrypted_message = sock.recv(length)
            # 解密消息
            return decrypt_message(encrypted_message)
        except Exception as e:
            if is_chat:
                print(f"\n接收聊天消息失败！\n{e}")
            else:
                print(f"解密消息失败！\n{e}")
            return None


    # 用户登录
    def login(self, username, password):
        try:

            # 发送登录标识
            if not self.send_message('login'):
                return False


            # 接收服务器的公钥
            public_key = self.socket.recv(2048)

            # 发送加密的登录信息
            login_info = f'login {username} {password}'
            if not self.send_message(login_info, use_rsa=True, public_key=public_key):
                return False

            # 接收登录响应
            response = self.receive_message()
            if not response:
                return False

            if "Login successful" in response:
                self.username = username
                return True
            return False
        except Exception as e:
            print(f"登录失败！\n{e}")
            return False

    # 注册新用户
    def register(self, username, password):
        try:

            # 发送注册请求
            message = f'register {username} {password}'
            if not self.send_message(message):
                print("发送注册请求失败")
                return False

            # 接收注册响应
            response = self.receive_message()

            if "successful" in response:
                print("注册成功！")
                return True
            else:
                print(f"注册失败：{response}")
                return False
        except Exception as e:
            print(f"注册失败！\n{e}")
            return False

    # 下载文件到本地
    def download_file(self, filename):
        try:
            # 创建文件选择对话框
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            
            # 选择保存目录
            save_dir = filedialog.askdirectory(
                parent=root,
                title="选择保存目录",
                initialdir=os.getcwd()
            )
            
            root.destroy()
            
            if not save_dir:
                print("下载已取消")
                return False

            file_path = os.path.join(save_dir, filename)

            # 检查文件是否存在
            if os.path.exists(file_path):
                confirm = input(f"文件 '{filename}' 已存在于目标目录，是否覆盖？(y/n): ").lower()
                if confirm != 'y':
                    print("下载已取消")
                    return False

            # 发送下载请求
            command = f'get {filename}'
            if not self.send_message(command):
                return False

            # 接收服务器响应
            response = self.receive_message()
            if not response or not response.startswith('ok'):
                print("文件未找到！")
                return False

            # 获取服务器端的MD5值
            server_md5 = response.split('|')[1]

            # 接收文件大小
            file_size = struct.unpack('I', self.socket.recv(4))[0]
            received_size = 0

            # 接收并写入文件内容
            with tqdm(total=file_size, unit='B', unit_scale=True, desc=f'正在下载 {filename}') as progress_bar:
                with open(file_path, 'wb') as f:
                    while received_size < file_size:
                        # 接收数据块
                        block_size_data = self.socket.recv(4)
                        block_size = struct.unpack('I', block_size_data)[0]

                        # 接收加密数据
                        encrypted_data = b''
                        while len(encrypted_data) < block_size:
                            chunk = self.socket.recv(min(block_size - len(encrypted_data), 8192))
                            if not chunk:
                                raise Exception("Connection lost")
                            encrypted_data += chunk

                        # 解密并写入数据
                        decrypted_data = decrypt_message(encrypted_data)
                        f.write(decrypted_data.encode('latin-1'))

                        received_size += len(decrypted_data)
                        progress_bar.update(len(decrypted_data))

            # 验证MD5
            process = subprocess.run(['certutil', '-hashfile', file_path, 'MD5'], 
                                   capture_output=True, text=True)
            client_md5 = process.stdout.split('\n')[1].strip()

            if client_md5.lower() == server_md5.lower():
                print(f"\n文件已下载到: {file_path}")
                print(f"MD5校验成功: {client_md5}")
                return True
            else:
                print("\nMD5校验失败！文件可能已损坏。")
                os.remove(file_path)
                return False

        except Exception as e:
            print(f"\n下载文件时出错: {e}")
            if os.path.exists(file_path):
                os.remove(file_path)
            return False

    # 上传文件到服务器
    def upload_file(self):
        try:
            # 创建文件选择对话框
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            
            # 选择要上传的文件
            file_path = filedialog.askopenfilename(
                parent=root,
                title="选择要上传的文件",
                filetypes=[("所有文件", "*.*")]
            )
            
            root.destroy()
            
            if not file_path:
                print("上传已取消")
                return False

            filename = os.path.basename(file_path)

            # 计算文件的MD5值
            process = subprocess.run(['certutil', '-hashfile', file_path, 'MD5'], 
                                   capture_output=True, text=True)
            md5_hash = process.stdout.split('\n')[1].strip()

            # 发送上传请求
            command = f'put {filename} {md5_hash}'
            if not self.send_message(command):
                return False

            # 接收服务器响应
            response = self.receive_message()
            if not response:
                return False
                
            if response != 'Ready to receive file':
                print(f"Server rejected upload: {response}")
                return False

            # 发送文件内容
            file_size = os.path.getsize(file_path)
            self.socket.sendall(struct.pack('I', file_size))

            # 分块读取并发送文件
            with tqdm(total=file_size, unit='B', unit_scale=True, desc=f'正在上传 {filename}') as progress_bar:
                with open(file_path, 'rb') as fp:
                    sent_size = 0
                    while sent_size < file_size:
                        chunk = fp.read(min(bufferSize, file_size - sent_size))
                        if not chunk:
                            break

                        if not self.send_message(chunk.decode('latin-1')):
                            return False
                        sent_size += len(chunk)
                        progress_bar.update(len(chunk))

            # 接收上传结果
            response = self.receive_message()
            if not response:
                return False

            if response == 'ok':
                print(f"\n文件上传成功: {filename}")
                print(f"MD5值: {md5_hash}")
                return True
            else:
                print(f"\n上传失败: {response}")
                return False

        except Exception as e:
            print(f"\n上传文件时出错: {e}")
            return False

    # 格式化显示文件列表
    def display_file_list(self, response):
        try:
            # 解析服务器返回的JSON数据
            files = json.loads(response)
            if not files:
                print("当前目录为空")
                return

            # 计算最长的文件名长度，用于对齐
            name_width = max(len(file["name"]) for file in files) + 2
            
            # 打印表头
            print("\n{:<{width}} {:<8} {}".format(
                "名称", "类型", "大小", width=name_width
            ))
            print("-" * (name_width + 20))  # 分隔线

            # 遍历并显示文件列表
            for file in files:
                # 格式化文件大小
                if file["size"] is not None:
                    size = self.format_size(file["size"])
                else:
                    size = "-"

                # 使用不同颜色显示文件夹和文件
                if file["type"] == "Folder":
                    name = f"\033[94m{file['name']}/\033[0m"  # 蓝色显示文件夹
                else:
                    name = file["name"]

                # 打印文件信息
                print("{:<{width}} {:<8} {}".format(
                    name,
                    file["type"],
                    size,
                    width=name_width
                ))
            print()

        except json.JSONDecodeError:
            print("Error parsing file list")
        except Exception as e:
            print(f"Error displaying file list: {e}")

    # 格式化文件大小显示
    def format_size(self, size):
        # 依次尝试不同的单位
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f}{unit}"
            size /= 1024.0
        return f"{size:.1f}PB"

    # 执行FTP命令
    def execute_command(self, command):
        try:
            # 处理删除文件的确认
            if command.startswith('rm '):
                confirm = input("确定要删除该文件吗？(y/n): ").lower()
                if confirm != 'y':
                    return None

            # 发送命令
            if not self.send_message(command):
                return None

            # 接收服务器响应
            response = self.receive_message()
            if not response:
                return None

            # 处理特殊命令的响应
            if command.lower() in ['ls', 'list', 'dir']:
                self.display_file_list(response)
                return None
            elif command.lower() == 'who':
                print(response)
                return None
            
            return response

        except Exception as e:
            print(f"执行命令失败！\n{e}")
            return None

    # 关闭连接
    def close(self):
        try:
            if self.socket:
                try:
                    self.execute_command('quit')
                except:
                    pass
                self.socket.close()
                self.socket = None
            if self.chat_socket:
                self.chat_socket.close()
                self.chat_socket = None
            print("连接已关闭")
            os._exit(0)
        except:
            pass
            os._exit(-1)

# FTP客户端主函数
def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='FTP Client')
    parser.add_argument('-s', '--server', required=True, help='服务器IP地址')
    parser.add_argument('-P', '--port', type=int, default=8081, help='服务器端口')
    parser.add_argument('-u', '--username', help='登录用户名')
    parser.add_argument('-r', '--register', nargs=2, metavar=('username', 'password'), 
                        help='注册新用户')

    args = parser.parse_args()
    client = FTPClient(args.server, args.port)

    try:
        # 连接到服务器
        if not client.connect():
            return

        # 处理注册请求
        if args.register:
            client.register(args.register[0], args.register[1])
            return

        # 检查用户名参数
        if not args.username:
            print("错误：需要提供用户名")
            return

        # 执行登录
        print(f"正在尝试登录用户：{args.username}")
        # password = getpass.getpass("请输入密码: ")
        password = 'admin'
        if not client.login(args.username, password):
            return

        print("\n登录成功！输入 'help' 查看可用命令。\n")

        # 主命令循环
        while True:
            try:
                command = input(f"FTP {args.server}:{args.port}> ").strip()
                if not command:
                    continue

                # 处理退出命令
                if command.lower() == 'quit':
                    confirm = input("确定要退出程序吗？(y/n): ").lower()
                    if confirm == 'y':
                        break
                # 处理聊天命令
                elif command.startswith('chat '):
                    message = command[5:]  # 提取聊天内容
                    if not client.chat_socket:
                        print("未连接到聊天服务器")
                        continue
                    if client.send_message(message, is_chat=True):
                        print("消息已发送")  # 添加成功提示
                # 处理下载命令
                elif command.startswith('get '):
                    try:
                        filename = command.split()[1]
                        client.download_file(filename)
                    except IndexError:
                        print("错误：请指定要下载的文件名")
                # 处理上传命令
                elif command.startswith('put'):
                    client.upload_file()
                # 处理其他命令
                else:
                    response = client.execute_command(command)
                    if response:
                        print(response)
            except Exception as e:
                print(f"错误：{str(e)}")

    except KeyboardInterrupt:
        print("\n程序已终止")
        os._exit(-1)
    except Exception as e:
        print(f"错误：{str(e)}")
        os._exit(-1)
    finally:
        client.close()

# 程序入口点
if __name__ == "__main__":
    main()
