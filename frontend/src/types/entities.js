// API 实体约定：
// Line {code,name}；BatchVersion {batch_no,line_code,ship_date,enroll_date,record_date}
// OutcomeVersion {batch_no,action,outcome,event_date,reason,record_date}
// AuditJob {audit_date,status,mode,changed_lines}；CurvePoint {day,n_risk,...,cif_*}
export const ENTITY_KEYS = ['lines', 'batches', 'outcomes', 'jobs', 'logs'];
