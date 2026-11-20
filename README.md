# 砚泉售后批次返修风险曲线簿

各随访线随访长短不一，售后按**查账日能看到的版本**核算批次出厂后的累计返修与报废风险（Aalen-Johansen 竞争风险），回答「出厂后多久容易返修」。迟报与更正只影响新查账日，历史查账日曲线冻结；并发更正按受影响线增量重算，整条曲线在同一事务内一次性切换。

## 业务场景与工作流

模拟客户：砚泉售后协作组。每条售后随访线持续时间不同，批次先有出厂日与入组日，随后陆续收到返修、报废或随访结束的结局登记，登记可能迟报、被更正或作废。售后分析员录入批次与结局版本，负责人按查账日发起核算，阅读者查看各线累计返修风险曲线、对应在险批数与失败原因。

模块：业务总览、批次与结局录入、查账日与风险曲线、失败原因、过程留痕。

- **批次版本（append-only）**：录入与日期更正都新增一行 `batch_versions`，以 `record_date`（到账日）决定可见性，永不覆盖旧版本。
- **结局流水（append-only）**：首报 `report` / 更正 `correct` / 作废 `void` 均追加 `outcome_versions`；查账日 T 只取每批次 `record_date<=T` 的最新流水，最新为 void 则该批次无有效结局。
- **查账任务**：同一查账日任务唯一；Redis 队列异步核算，worker 中断重启自动恢复 `running` 原单，失败重试复用原任务，绝不重复出曲线。

## 算法口径

时间原点为**出厂日**，时间尺度为**出厂后天数**。每个事件日严格按以下顺序处理：

1. **先入组**：当日入组的批次进入在险集（同日入组即承担当日风险）；
2. **再核算**：用**同一在险批数**并列累计返修与报废两类竞争事件；
3. **最后移除**：随访结束（删失）的批次在当日事件核算之后才离开在险集。

Aalen-Johansen 累计发生函数（CIF）增量：`CIF_k(t) += S(t-) × d_k(t)/n(t)`，其中 `S(t-)=1-CIF_repair-CIF_scrap` 为上一步仍在随访占比，`d_k` 为当日事件数，`n` 为同一在险批数。查账日仍无结局的批次在查账日行政删失。

**版本化与增量**：查账日 T 的快照只含 `record_date<=T` 的版本，迟报/更正不影响更早查账日已冻结的曲线。新查账日核算时，先定位两查账日之间发生版本变动的线，仅对这些线从**最早变动天数**起重算（之前的点逐点沿用），未受影响线整线沿用；出现全新随访线等无法沿用的情形时退化为整体重算。所有曲线点在单事务内先清后写，外部永远只看到完整的一版。

## 一天的验收剧本

1. 09:00 admin 查看 seed 的 2 条随访线、40 个批次版本与含迟报/更正/作废的结局流水。
2. 09:10 analyst 录入一批新出厂批次，并对一批次登记返修（含失败原因与到账日）。
3. 09:20 analyst 发起查账日 `2026-09-01` 核算，worker 出两线寿命表与 CIF 曲线（整体重算）。
4. 09:30 admin 查看各线累计返修风险、每日在险批数与失败原因汇总。
5. 09:40 analyst 对一条返修登记做更正（返修→报废，新到账日），发起第二个查账日：仅受影响线增量重算，另一线逐点沿用，模式标记为 incremental。
6. 09:45 重复提交同一查账日，系统复用原任务不重复出曲线；worker 重启后 running 原单自动恢复。
7. viewer 只读查看曲线与失败原因，写入请求被 403 拒绝；过程留痕页可追溯全部操作者与时间。

## 快速启动

```sh
cp .env.example .env
docker compose up -d --build
docker compose exec -T backend python -m scripts.seed_demo
```

前端 http://localhost:18253 ，后端 http://localhost:19253/docs ，数据库宿主端口 17753。恰好 5 服务 frontend/backend/worker/db/redis，均有真实 healthcheck。停止并清空演示数据：`docker compose down -v --remove-orphans`。

| 角色 | 邮箱 | 密码 | 权限 |
|---|---|---|---|
| admin | admin@demo.local | Demo2026! | 全部录入、查账核算、重试 |
| analyst | analyst@demo.local | Demo2026! | 批次/结局录入、发起查账；无管理类限制外只读 |
| viewer | viewer@demo.local | Demo2026! | 只读曲线、批数与失败原因 |

## 工程结构与本地开发

Python3.11 / FastAPI / SQLAlchemy / Redis，MySQL8；前端原生 HTML/CSS/JS ES modules，Nginx 代理 `/api/` 剥前缀至后端。`backend/src` 按 models/schemas/services/controllers/routes/middlewares/config/utils/constants 拆分；核心算法在 `services/statistics.py`，as-of 快照在 `services/snapshot.py`，增量编排在 `services/audit_compute.py`，全部业务计算在 Python。

无 Docker / 无 MySQL 的本地开发：不设 `DATABASE_URL` 时自动使用 SQLite，无 Redis 时队列退化为进程内内存队列（行为同 rpush/lpop）。

```sh
cd backend
python3 -m pytest                 # 11 个测试：手算 oracle、as-of、增量、幂等、API 权限
SEED_DEMO=true uvicorn src.main:app --reload   # 另开一窗：python3 -m src.worker
```

环境变量：`COMPOSE_PROJECT_NAME`、`FRONTEND_PORT`、`BACKEND_PORT`、`DB_PORT`、`JWT_SECRET`（部署替换）、`DATABASE_URL`、`REDIS_URL`、`SEED_DEMO`、`QUEUE_FALLBACK`。角色枚举 admin/analyst/viewer 与任务状态 queued/running/completed/failed 分别定义于 `backend/src/constants/enums.py` 与 `frontend/src/constants/enums.js`。两个中间件：统一可恢复校验错误、每 IP 每分钟 360 次限流。

## 已知边界

单 worker 轮询；内存队列退化仅用于本地开发，容器内始终使用 Redis。曲线为纯 SVG 阶梯连线，适合演示规模（40 批）；寿命表全量随查账任务持久化。日期按日历日处理，时间显示 Asia/Shanghai。后端以专属字段对象收发，页面通过业务表单录入，不要求手写 JSON。JWT 演示有效期 2 小时。

MIT License。

## 实际实体与表

随访线 `lines`；批次有效日期版本 `batch_versions`；结局版本流水 `outcome_versions`；查账任务 `audit_jobs`；曲线寿命表点 `curve_points`；失败原因汇总 `reason_stats`；账号 `users` 与留痕 `audits`。
