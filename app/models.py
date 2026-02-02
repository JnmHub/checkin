from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean  # 导入常用的字段类型和外键约束
from sqlalchemy.ext.declarative import declarative_base  # 导入声明式基类的构造函数
from datetime import datetime  # 导入 Python 标准库的日期时间模块

Base = declarative_base()  # 创建所有数据库模型的基类，用于跟踪所有映射的表

class Admin(Base):  # 定义管理员模型类
    __tablename__ = "admins"  # 设置数据库中对应的表名为 admins
    id = Column(Integer, primary_key=True, index=True)  # 自增主键 ID，并建立索引以优化查询速度
    username = Column(String(50), unique=True)  # 管理员登录账号，最长 50 字符，且字段值必须唯一
    password_hash = Column(String(255))  # 存储加密后的密码哈希值，长度设为 255 以兼容不同加密算法

class Employee(Base):
    __tablename__ = "employees"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50))
    account = Column(String(50), unique=True)
    password_hash = Column(String(255)) # 新增：加密后的密码
    wechat_openid = Column(String(100), unique=True, nullable=True)
    is_active = Column(Boolean, default=True)


class CheckInPoint(Base):  # 定义打卡点（地理围栏）模型类
    __tablename__ = "check_in_points"  # 设置数据库中对应的表名为 check_in_points
    id = Column(Integer, primary_key=True, index=True)  # 点位唯一自增 ID
    title = Column(String(100))  # 打卡点名称（如：XX大厦正门）
    address = Column(String(255))  # 详细地址文字描述
    latitude = Column(Float)  # 打卡点中心位置的纬度（高德坐标系）
    longitude = Column(Float)  # 打卡点中心位置的经度（高德坐标系）
    radius = Column(Integer, default=500)  # 允许打卡的有效半径，单位为米，默认为 500 米

class CheckInRecord(Base):  # 定义打卡记录模型类
    __tablename__ = "check_in_records"  # 设置数据库中对应的表名为 check_in_records
    id = Column(Integer, primary_key=True, index=True)  # 记录唯一自增 ID
    employee_id = Column(Integer, ForeignKey("employees.id"))  # 关联员工表的外键 ID
    point_id = Column(Integer, ForeignKey("check_in_points.id"))  # 关联打卡点表的外键 ID
    photo_url = Column(String(255))  # 存储在 MinIO 中的图片对象路径（Key）
    lat = Column(Float)  # 员工打卡时，设备实际上传的纬度
    lon = Column(Float)  # 员工打卡时，设备实际上传的经度
    location_name = Column(String(255))  # 调用高德逆地理编码 API 后得到的实际打卡位置名称
    create_time = Column(DateTime, default=datetime.now)  # 记录创建时间，默认使用服务器当前系统时间