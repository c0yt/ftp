# 简易FTP服务端&客户端实现

### 文件结构

```tree
├── certs
│   ├── private.pem
│   └── public.pem
├── key
│   └── crypto_utils.py
├── logs
│   └── ftp_server.log
├── src
│   ├── client
│   │   └── Client.py
│   └── server
│       ├── command_handler.py
│       ├── database.py
│       ├── server_handler.py
│       ├── Server.py
│       ├── Users
│       │   ├── admin
│       └── users.db
```

### 服务端

1. 基础命令实现

   - 普通用户命令

     - `ls`或`list`或`dir`: 显示当前目录下的文件和文件夹，包含大小、修改时间等详细信息。
     - `cd [directory]`: `cd..`返回上级目录，`cd /`返回根目录，`cd path`进入指定目录。
     - `pwd`: 显示当前工作目录的完整路径。
     - `home`: 返回到用户的主目录。
     - `get [filename]`: 下载指定文件到本地，支持断点续传和进度显示，自动进行 MD5 校验。
     - `put`: 上传本地文件到服务器，支持断点续传和进度显示，自动进行 MD5 校验。
     - `mkdir [directory]`: 在当前目录创建新文件夹。
     - `rm [filename]`: 删除指定的文件或空目录，需要确认。

     - `login [username] [password]`: 登录到 FTP 服务器。
     - `register [username] [password]`: 注册新用户账号。
     - `passwd`: 修改当前用户的密码。
     - `whoami`: 显示当前登录用户的身份信息。
     - `chat [message]`: 发送聊天消息到服务器。
     - `quit`: 安全退出 FTP 客户端。

   - 管理员命令

     - `userlist`: 查看所有注册用户。
     - `promote [username]`: 将指定用户提升为管理员。
     - `demote [username]`: 将指定管理员降级为普通用户。
     - `deleteuser [username]`: 删除指定用户账号。

2. 服务器控制台命令

   - `chat [message]`: 向所有在线客户端广播消息。
   - `list` : 显示当前所有连接的客户端列表
   - `kick [number]`: 踢出指定用户。
   - `quit`: 关闭服务器。
   - `help`:  展示帮助信息。

3. 服务器界面
   ![image](https://github.com/user-attachments/assets/9fa99e1c-20ee-4550-be29-4d961175d9d4)


### 客户端

1. 连接参数
   - `-s`或`--server`: 指定服务器 IP 地址。
   - `-P`或`--port`: 指定服务器端口 (默认 8081)。
   - `-u`或`--username`: 指定登录用户名。
   - `-r`或`--register`: 注册新用户。
   - `-h`或`--help`: 显示帮助信息。

2. 客户端界面

   ![image](https://github.com/user-attachments/assets/fb448976-742f-4047-bde2-229f73c6603f)

### 更新日志

- 2024/10/29
  - 创建了项目，并实现了基础功能。
- 2024/10/30
  - 完善了服务端和客户端的`get`和`put`功能。
- 2024/11/3
  - 增加了 AES 加密通讯。
- 2024/11/4
  - 增加了不显示输入密码功能。
  - 下载功能的加密传输功能已实现，但进度条略微有点问题。上传功能未加密。
- 2024/11/8
  - 修复了下载功能进度条显示的问题。
  - 上传功能已加密。
  - 增加了错误捕捉，待完善。

- 2024/11/30
  - 增加命令，修复加密通信bug

- 2024/12/10
  - 增加RSA登录验证
  - 优化代码结构，文件结构
  - 采用统一函数处理接受信息和发送信息
