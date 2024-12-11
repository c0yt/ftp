import threading
import struct
import logging
import os
import sys
sys.path.append('../../key')
from crypto_utils import encrypt_message, decrypt_message, generate_key_pair, decrypt_login, encrypt_login
from database import DatabaseManager
from command_handler import CommandHandler

# 定义用于数据传输的缓冲区大小
bufferSize = 2048
# 定义整数类型的字节大小
intSize = struct.calcsize('I')


class FTPServer(threading.Thread):
    # 初始化FTP服务器线程，处理单个客户端连接
    def __init__(self, client_socket, server_manager):
        super().__init__()
        self.client_socket = client_socket  # 客户端的主socket连接
        self.chat_socket = None  # 用于聊天功能的socket连接
        self.current_directory = os.getcwd()  # 当前工作目录
        self.username = None  # 客户端用户名
        self.is_admin = False  # 管理员权限标志
        self.db = DatabaseManager()  # 数据库管理器实例
        self.client_ip = self.client_socket.getpeername()[0]  # 客户端IP地址
        self.command_handler = CommandHandler(self)  # 命令处理器实例
        self.private_key, self.public_key = generate_key_pair()  # 生成RSA密钥对
        self.server_manager = server_manager  # 保存对ServerManager的引用

    # 设置聊天socket并启动消息处理线程
    def set_chat_socket(self, chat_socket):
        self.chat_socket = chat_socket
        threading.Thread(target=self.handle_chat_messages, daemon=True).start()

    # 持续监听并处理来自客户端的聊天消息
    def handle_chat_messages(self):
        while self.chat_socket:  # 只在chat_socket存在时运行
            try:
                message = self.receive_message(is_chat=True)
                if message:
                    print(f"\n{self.username}: {message}")
                    print("Server > ", end='', flush=True)
                else:
                    break  # 如果接收到None，退出循环
            except Exception:
                break

    # 发送加密消息
    def send_message(self, msg, is_chat=False, use_rsa=False, private_key=None):
        try:
            if isinstance(msg, bytes):
                msg = msg.decode()
            # 根据需要选择加密方式
            if use_rsa:
                encrypted_msg = encrypt_login(msg, private_key)
            else:
                encrypted_msg = encrypt_message(msg)
                
            # 发送消息长度和加密消息
            msg_length = struct.pack('I', len(encrypted_msg))
            
            # 选择使用的socket
            sock = self.chat_socket if is_chat else self.client_socket
            sock.sendall(msg_length + encrypted_msg)
        except Exception as e:
            if is_chat:
                print(f"\nError broadcasting chat: {e}")
            else:
                self.log_with_user(f"Error encrypting or sending message: {e}", level='error')
    # 接收并解密消息
    def receive_message(self, is_chat=False, use_rsa=False):
        try:
            sock = self.chat_socket if is_chat else self.client_socket
            if not sock:  # 检查socket是否有效
                return None
                
            length = struct.unpack('I', sock.recv(intSize))[0]
            encrypted_message = sock.recv(length)
            if use_rsa:
                return decrypt_login(encrypted_message, self.private_key)
            return decrypt_message(encrypted_message)
        except Exception as e:
            if not is_chat:  # 只记录非聊天消息的错误
                self.log_with_user(f"Error receiving message: {e}", level='error')
            return None
    # 记录带有用户信息的日志
    def log_with_user(self, message, level='info'):
        user_info = f"[User: {self.username if self.username else 'System'}]"
        log_message = f"{user_info} {message}"
        if level == 'info':
            logging.info(log_message)
        elif level == 'warning':
            logging.warning(log_message)
        elif level == 'error':
            logging.error(log_message)
        elif level == 'debug':
            logging.debug(log_message)

    # 清理客户端连接相关的资源
    def cleanup(self):
        try:
            if self.username:
                self.log_with_user("Client disconnected", level='info')
            if self.client_socket:
                self.client_socket.close()  # 关闭主socket连接
                self.client_socket = None   # 清除引用
            if self.chat_socket:
                self.chat_socket.close()    # 关闭聊天socket连接
                self.chat_socket = None     # 清除引用
        except Exception as e:
            self.log_with_user(f"Error during cleanup: {e}", level='error')


    # 处理客户端连接的主循环
    def run(self):
        try:
            while True:
                try:
                    # 接收命令类型
                    command_type = self.receive_message()
                    if not command_type:  # 如果接收到None，说明连接已断开
                        self.log_with_user("Client disconnected", level='info')
                        break  # 退出循环

                    if command_type == 'login':
                        # 首先发送公钥给客户端用于加密
                        self.client_socket.sendall(self.public_key)
                        # 处理登录命令：接收并解密登录信息
                        command = self.receive_message(use_rsa=True)
                    else:
                        command = command_type

                    if command:  # 只有在收到有效命令时才处理
                        self.log_with_user(f"Received: {command}", level='info')
                        self.command_handler.handle_command(command.strip())

                except ConnectionError:  # 捕获连接相关的错误
                    self.log_with_user("Connection lost", level='info')
                    break
                except Exception as e:
                    self.log_with_user(f"Error in client communication: {e}", level='error')
                    break
        finally:
            # 从客户端列表中移除当前客户端
            try:
                self.server_manager.clients.remove(self)  # 使用server_manager引用
            except:
                pass
            self.cleanup()  # 清理资源


class ServerManager:
    # 初始化服务器管理器
    def __init__(self):
        self.clients = []  # 存储所有客户端连接的列表
        self.running = True  # 服务器运行状态标志

    # 向所有客户端广播消息
    def broadcast_message(self, message):
        broadcast_message = f"Server: {message}".encode()
        for client in self.clients:
            try:
                if client.chat_socket:
                    client.send_message(broadcast_message, is_chat=True)
                    print("success")
            except Exception as e:
                print("error")

    # 显示当前所有连接的客户端信息
    def list_clients(self):
        print("\n当前连接的客户端：")
        for i, client in enumerate(self.clients, 1):
            username = client.username
            print(f"{i}. {username} - {client.client_ip}")
        print()

    # 断开指定客户端的连接
    def kick_client(self, arg):
        try:
            index = int(arg) - 1
            if 0 <= index < len(self.clients):
                client = self.clients[index]
                try:
                    # 先发送踢出通知
                    client.send_message("You have been kicked from the server", is_chat=True)
                    # 等待一小段时间确保消息发送
                    import time
                    time.sleep(0.1)
                    # 关闭连接
                    client.cleanup()  # 使用cleanup方法来关闭连接
                    # 从列表中移除客户端（如果还在列表中的话）
                    if client in self.clients:
                        self.clients.remove(client)
                    print(f"已踢出客户端: {client.username or '未登录'}")
                except Exception as e:
                    print(f"踢出客户端时出错: {e}")
            else:
                print("无效的客户端编号")
        except ValueError:
            print("Usage: kick <client_number>")

    # 显示服务器支持的命令帮助信息
    def show_help(self):
        commands = {
            'chat <message>': '向所有客户端发送消息',
            'list': '显示当前连接的客户端列表',
            'kick <number>': '断开指定客户端的连接',
            'quit': '关闭服务器',
            'help': '显示此帮助信息'
        }
        print("\n可用命令：")
        for cmd, desc in commands.items():
            print(f"{cmd:15} - {desc}")
        print()

    # 处理服务器控制台输入的命令
    def handle_command(self, command):
        if not command:
            return True

        parts = command.split(maxsplit=1)
        cmd = parts[0].lower()  # 获取命令类型
        arg = parts[1] if len(parts) > 1 else ''  # 获取命令参数

        if cmd == 'chat' and arg:
            self.broadcast_message(arg)
        elif cmd == 'list':
            self.list_clients()
        elif cmd == 'kick':
            self.kick_client(arg)
        elif cmd == 'help':
            self.show_help()
        elif cmd == 'quit':
            confirm = input("确定要关闭服务器吗？(y/n): ").lower()
            if confirm == 'y':
                print("正在关闭服务器...")
                for client in self.clients:
                    try:
                        client.client_socket.close()
                        client.chat_socket.close()
                    except:
                        pass
                self.running = False
                return False
        else:
            print("Unknown command")
        return True
