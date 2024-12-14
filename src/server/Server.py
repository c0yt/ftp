import socket
import threading
import logging
from server_handler import FTPServer, ServerManager

# 配置日志记录
log_format = '%(asctime)s - %(levelname)s - %(message)s'
file_handler = logging.FileHandler('../../logs/ftp_server.log')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter(log_format))

# 配置日志记录器
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)


def start_server():
    try:
        # 创建主服务器和聊天服务器的套接字
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        chat_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # 绑定服务器地址和端口
        server_socket.bind(('0.0.0.0', 8081))
        chat_server_socket.bind(('0.0.0.0', 8082))

        # 开始监听连接
        server_socket.listen(5)
        chat_server_socket.listen(5)

        # 管理服务器状态和连接的类
        server_manager = ServerManager()

        # 接受连接的函数
        def accept_connections():
            while server_manager.running:
                try:
                    # 接受文件传输和聊天的连接
                    client_socket, addr = server_socket.accept()
                    chat_socket, _ = chat_server_socket.accept()

                    # 创建FTP服务处理对象，传入server_manager
                    client_handler = FTPServer(client_socket, server_manager)
                    client_handler.set_chat_socket(chat_socket)
                    server_manager.clients.append(client_handler)
                    client_handler.start()
                except Exception as e:
                    if server_manager.running:
                        print(f"\nError accepting connection: {e}")
                        print("Server > ", end='', flush=True)

        # 启动接受连接的线程
        accept_thread = threading.Thread(target=accept_connections, daemon=True)
        accept_thread.start()

        print("FTP服务器已启动，输入 'help' 查看可用命令")

        # 服务器主控制台循环
        while True:
            try:
                command = input("Server > ").strip()  # 读取用户输入的命令
                if not server_manager.handle_command(command):  # 处理命令
                    break
            except Exception as e:
                print(f"Error: {e}")

    except socket.error as e:
        print(f"Error setting up server: {e}")
    finally:
        # 确保关闭套接字
        server_socket.close()
        chat_server_socket.close()


if __name__ == "__main__":
    start_server()
