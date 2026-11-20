from sqlalchemy import Column, Integer, String, JSON, Float, Text, Date, UniqueConstraint
from src.config.database import Base


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    email = Column(String(120), unique=True)
    role = Column(String(20))
    password = Column(String(250))


class Audit(Base):
    __tablename__ = 'audits'
    id = Column(Integer, primary_key=True)
    actor = Column(String(120))
    action = Column(String(80))
    detail = Column(Text)
    at = Column(Float)


class Line(Base):
    """产品线/售后随访线。各线随访长短不一，曲线按线分别核算。"""
    __tablename__ = 'lines'
    id = Column(Integer, primary_key=True)
    code = Column(String(60), unique=True)
    name = Column(String(120))
    created = Column(Float)


class BatchVersion(Base):
    """
    批次的有效日期版本（append-only）。
    录入与更正都新增一行：record_date 为该版本进入查账视野的日期，
    历史查账日只能看到 record_date <= audit_date 的最新版本。
    出厂日 ship_date 为风险时间原点；入组日 enroll_date 决定批次进入在险集的天数。
    """
    __tablename__ = 'batch_versions'
    id = Column(Integer, primary_key=True)
    batch_no = Column(String(80), index=True)
    line_code = Column(String(60), index=True)
    ship_date = Column(Date, nullable=False)
    enroll_date = Column(Date, nullable=False)
    record_date = Column(Date, nullable=False, index=True)
    superseded_id = Column(Integer, default=0)  # 被本行取代的旧版本 id，首版为 0
    actor = Column(String(120))
    created = Column(Float)


class OutcomeVersion(Base):
    """
    结局版本流水（append-only）。report 登记、correct 更正、void 作废均新增一行。
    查账日 T 可见的有效登记 = 每个 batch_no 下 record_date<=T 的最新非 void 行。
    event_date 为结局实际发生日；reason 为失败原因（返修/报废必填）。
    """
    __tablename__ = 'outcome_versions'
    id = Column(Integer, primary_key=True)
    batch_no = Column(String(80), index=True)
    action = Column(String(20))           # report / correct / void
    outcome = Column(String(20), nullable=True)  # repair / scrap / censor，void 时为空
    event_date = Column(Date, nullable=True)
    reason = Column(String(200), nullable=True)
    record_date = Column(Date, nullable=False, index=True)  # 报送到账日，决定可见性
    actor = Column(String(120))
    created = Column(Float)


class AuditJob(Base):
    """查账日核算任务。同一查账日唯一：重试复用原任务，绝不重复出曲线。"""
    __tablename__ = 'audit_jobs'
    id = Column(Integer, primary_key=True)
    audit_date = Column(Date, unique=True)
    status = Column(String(20))
    error = Column(Text)
    # full=无历史曲线整体重算；incremental=按受影响线最早变动天数增量重算，其余沿用
    mode = Column(String(20), default='')
    changed_lines = Column(JSON, default=list)
    created = Column(Float)
    started = Column(Float, nullable=True)
    finished = Column(Float, nullable=True)
    actor = Column(String(120))


class CurvePoint(Base):
    """
    某查账日版本下、某条线的寿命表点。整条曲线随查账任务在同一事务内一次性切换。
    """
    __tablename__ = 'curve_points'
    __table_args__ = (UniqueConstraint('job_id', 'line_code', 'day', name='uq_curve_point'),)
    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, index=True)
    line_code = Column(String(60), index=True)
    day = Column(Integer)                  # 出厂后天数
    n_risk = Column(Integer)               # 当日同一在险批数（先入组后核算）
    n_repair = Column(Integer)             # 当日返修批数
    n_scrap = Column(Integer)              # 当日报废批数
    n_censor = Column(Integer)             # 当日随访结束批数（当日核算后移除）
    cif_repair = Column(Float)             # 累计返修风险 Aalen-Johansen
    cif_scrap = Column(Float)              # 累计报废风险
    survival = Column(Float)               # 仍在随访占比（1-两CIF之和）


class ReasonStat(Base):
    """查账日 × 线 × 结局 × 失败原因 的累计批数（截至该查账日有效登记）。"""
    __tablename__ = 'reason_stats'
    __table_args__ = (UniqueConstraint('job_id', 'line_code', 'outcome', 'reason', name='uq_reason_stat'),)
    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, index=True)
    line_code = Column(String(60), index=True)
    outcome = Column(String(20))
    reason = Column(String(200))
    n_batches = Column(Integer)
