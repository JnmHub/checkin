from app.db.session import SessionLocal
from app.models import Admin
from app.utils.pwd import get_password_hash

def init_admin():
    db = SessionLocal()
    # 检查是否已有管理员
    admin = db.query(Admin).filter(Admin.username == "admin").first()
    if not admin:
        print("正在创建默认管理员账号: admin/123456")
        new_admin = Admin(
            username="admin",
            password_hash=get_password_hash("123456")
        )
        db.add(new_admin)
        db.commit()
    db.close()