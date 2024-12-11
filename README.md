FTP项目需求分析
系统概述
本项目实现一个基于Python的安全FTP文件传输系统，包含服务端和客户端两个部分，支持文件上传下
载、用户认证、权限管理等功能。系统采用加密传输确保数据安全性。
服务端
1. 基础命令实现
 文件操作命令：
ls 或 list 或 dir：显示当前目录下的文件和文件夹，包含大小、修改时间等详细信息。
cd [directory]：
cd .. 返回上级目录
cd / 返回根目录
cd path 进入指定目录
pwd：显示当前工作目录的完整路径。
home：返回到用户的主目录。
get [filename]：下载指定文件到本地，支持断点续传和进度显示，自动进行MD5校验。
put：上传本地文件到服务器，支持断点续传和进度显示，自动进行MD5校验。
mkdir [directory]：在当前目录创建新文件夹。
rm [filename]：删除指定的文件或空目录，需要确认。
 用户管理命令：
login [username] [password]：登录到FTP服务器。
register [username] [password]：注册新用户账号。
passwd：修改当前用户的密码。
whoami：显示当前登录用户的身份信息。
chat [message]：发送聊天消息到服务器。
quit：安全退出FTP客户端。
 管理员命令：
userlist：查看所有注册用户。
promote [username]：将指定用户提升为管理员。
demote [username]：将指定管理员降级为普通用户。
deleteuser [username]：删除指定用户账号。
2. 安全性功能
用户身份认证
基于RSA加密
密码输入采用非明文显示方式
用户权限管理
高级用户：具备所有权限，包括上传、创建目录等
管理员：具有用户管理权限，可以提升其他用户权限
数据安全
密码使用MD5加密存储在SQLite数据库中
文件传输采用AES加密
支持文件MD5校验，确保传输完整性
3. 系统功能
日志管理
记录用户登录登出信息
记录文件传输操作
记录系统错误信息
日志分级：INFO、WARNING、ERROR
并发处理
支持多用户同时连接
支持多文件同时传输
性能优化
大文件传输支持分块处理
传输速度限制配置
服务器资源监控
4. 服务器控制台命令
chat [message]：向所有在线客户端广播消息
list：显示当前所有连接的客户端列表，包含：
客户端编号
用户名
IP地址
kick [number]：根据客户端编号断开指定客户端的连接
quit：安全关闭服务器
通知所有客户端服务器即将关闭
等待所有文件传输完成
关闭所有客户端连接
保存服务器状态
help：显示所有可用的服务器控制命令及其说明
客户端
1. 连接参数
-s 或 --server ：指定服务器IP地址
-P 或 --port ：指定服务器端口（默认8081）
-u 或 --username ：指定登录用户名
-p 或 --password ：指定登录密码（不推荐，建议通过交互输入）
-r 或 --register ：注册新用户，格式： -r username password
-h 或 --help ：显示帮助信息
2. 界面与交互
命令行界面
命令帮助
help ：显示所有可用命令
help [command] ：显示指定命令的详细用法
传输进度显示
文件名和大小
传输速度（KB/s）
进度条
预计剩余时间
MD5校验结果
错误提示
命令格式错误提示
权限不足提示
文件操作错误提示
网络连接异常提示
更新日志
2024/10/29
创建了项目，并实现了基础功能
2024/10/30
完善了服务端和客户端的get和put功能
2024/11/3
增加了AES加密通讯
FTP [username]@IP:Port >
增加了不显示输入密码功能
下载功能的加密传输功能已实现，但进度条略微有点问题。上传功能未加密。
2024/11/8
修复了下载功能进度条显示的问题
上传功能已加密
增加了错误捕捉，待完善
项目结构与文件说明
服务端文件
1. src/server/Server.py
服务器主程序入口
实现服务器的启动和初始化
管理客户端连接和会话
提供服务器控制台界面
处理服务器命令（如：查看在线用户、踢出用户等）
实现聊天广播功能
2. src/server/server_handler.py
FTPServer类：处理单个客户端连接的核心类
实现命令解析和执行
管理用户会话状态
处理文件传输
实现聊天功能
日志记录
ServerManager类：
管理所有客户端连接
实现广播消息功能
提供服务器控制命令处理
3. src/server/database.py
数据库管理类
用户认证和权限验证
用户信息的CRUD操作
密码加密存储
提供以下功能：
用户验证
添加/删除用户
修改密码
权限管理
用户列表查询
客户端文件
1. src/client/Client.py
客户端主程序
实现命令行参数解析
处理用户输入命令
管理服务器连接
实现文件上传下载功能
显示传输进度
处理聊天功能
工具类文件
1. utils/crypto_utils.py
加密工具类
实现以下功能：
RSA密钥对生成
登录信息的RSA加密
文件传输的AES加密/解密
消息加密/解密
数据文件
1. data/users.db
SQLite数据库文件
存储用户信息
包含用户表：
username (主键)
password (MD5加密)
is_admin (权限标志)
created_at (创建时间)
2. logs/server.log
服务器日志文件
记录：
用户活动
文件操作
错误信息
系统状态
项目结构树
FTP_Project/
目录说明
1. src/：源代码目录
server/：服务器端代码
client/：客户端代码
2. utils/：工具类目录
加密
3. logs/：日志文件目录
服务器日志文件
关键文件说明
1. requirements.txt
项目依赖包列表
包含版本信息
2. README.md
项目说明文档
安装和使用说明
开发指南
├── README.md
├── requirements.txt
├── src/
│ ├── server/
│ │ ├── __init__.py
│ │ ├── Server.py # 服务器主程序
│ │ ├── server_handler.py # 服务器处理类
│ │ ├── database.py # 数据库管理
│ │ └── command_handler.py # 命令处理类
│ │ └── users.db # 用户数据库
│ └── client/
│ ├── __init__.py
│ ├── Client.py # 客户端主程序
│
├── utils/
│ ├── __init__.py
│ ├── crypto_utils.py # 加密工具
│
├── logs/
│ ├── server.log # 服务器日志
pycryptodome>=3
