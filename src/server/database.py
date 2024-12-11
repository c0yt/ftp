import sqlite3
import hashlib
import logging

class DatabaseManager:
    # 初始化数据库管理器，设置数据库文件名
    def __init__(self, db_name: str = 'users.db'):
        self.db_name = db_name
        self.init_database()

    # 初始化数据库结构和默认管理员账户
    def init_database(self):
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                # 只保留用户表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        username TEXT PRIMARY KEY,
                        password TEXT NOT NULL,
                        is_admin INTEGER DEFAULT 0
                    )
                """)
                
                # 创建默认管理员账户，admin/admin
                cursor.execute("SELECT * FROM users WHERE username=?", ('admin',))
                if not cursor.fetchone():
                    default_password = hashlib.md5('admin'.encode()).hexdigest()
                    cursor.execute(
                        "INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)",
                        ('admin', default_password, 1)
                    )
                conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Database initialization error: {e}")
            raise

    # 验证用户登录并返回管理员状态
    def verify_user(self, username, password):
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                hashed_password = hashlib.md5(password.encode()).hexdigest()
                cursor.execute(
                    "SELECT is_admin FROM users WHERE username=? AND password=?",
                    (username, hashed_password)
                )
                result = cursor.fetchone()
                return (True, result[0] == 1) if result else (False, False)
        except sqlite3.Error as e:
            logging.error(f"Database error during user verification: {e}")
            return (False, False)

    # 添加新用户到数据库
    def add_user(self, username, password):
        try:
            is_admin = False
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                hashed_password = hashlib.md5(password.encode()).hexdigest()
                cursor.execute(
                    "INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)",
                    (username, hashed_password, 1 if is_admin else 0)
                )
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            logging.warning(f"User {username} already exists")
            return False
        except sqlite3.Error as e:
            logging.error(f"Database error adding user: {e}")
            return False

    # 修改用户密码
    def change_password(self, username, old_password, new_password):
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                # 验证旧密码
                old_hash = hashlib.md5(old_password.encode()).hexdigest()
                cursor.execute(
                    "SELECT username FROM users WHERE username=? AND password=?",
                    (username, old_hash)
                )
                if not cursor.fetchone():
                    return False
                
                # 更新新密码
                new_hash = hashlib.md5(new_password.encode()).hexdigest()
                cursor.execute(
                    "UPDATE users SET password=? WHERE username=?",
                    (new_hash, username)
                )
                conn.commit()
                return True
        except sqlite3.Error as e:
            logging.error(f"Database error changing password: {e}")
            return False

    # 获取所有用户列表
    def get_all_users(self):
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT username, is_admin FROM users")
                return cursor.fetchall()
        except sqlite3.Error as e:
            logging.error(f"Database error getting user list: {e}")
            return []

    # 提升用户为管理员
    def promote_user(self, username):
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET is_admin=1 WHERE username=?",
                    (username,)
                )
                conn.commit()
                return True
        except sqlite3.Error as e:
            logging.error(f"Database error promoting user: {e}")
            return False

    # 降级管理员为普通用户
    def demote_user(self, username):
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET is_admin=0 WHERE username=?",
                    (username,)
                )
                conn.commit()
                return True
        except sqlite3.Error as e:
            logging.error(f"Database error demoting user: {e}")
            return False

    # 删除指定用户
    def delete_user(self, username):
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM users WHERE username=?", (username,))
                conn.commit()
                return True
        except sqlite3.Error as e:
            logging.error(f"Database error deleting user: {e}")
            return False
  