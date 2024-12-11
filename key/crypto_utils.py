from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Util.Padding import pad, unpad
# 16字节密钥，用于AES-128加密
KEY = b'Fh9X#mP2$kL7vN4@'

# 生成RSA公私钥对
def generate_key_pair():
    key = RSA.generate(2048)
    private_key = key.export_key()
    public_key = key.publickey().export_key()
    return private_key, public_key

# 使用RSA公钥加密登录信息
def encrypt_login(message, public_key):
    cipher = PKCS1_OAEP.new(RSA.import_key(public_key))
    return cipher.encrypt(message.encode())

# 使用RSA私钥解密登录信息
def decrypt_login(encrypted_message, private_key):
    cipher = PKCS1_OAEP.new(RSA.import_key(private_key))
    return cipher.decrypt(encrypted_message).decode()

# 使用AES加密消息
def encrypt_message(message):
    cipher = AES.new(KEY, AES.MODE_CBC)  # 创建AES对象，使用CBC模式
    iv = cipher.iv  # 获取随机生成的IV
    ct_bytes = cipher.encrypt(pad(message.encode(), AES.block_size))  # 加密并填充
    return iv + ct_bytes  # 返回 IV 和密文

# 使用AES解密消息
def decrypt_message(encrypted_message):
    iv = encrypted_message[:AES.block_size]  # 提取IV
    ct = encrypted_message[AES.block_size:]  # 提取密文
    cipher = AES.new(KEY, AES.MODE_CBC, iv)  # 使用IV创建AES对象
    pt = unpad(cipher.decrypt(ct), AES.block_size)  # 解密并去填充
    return pt.decode()  # 返回解密后的明文
