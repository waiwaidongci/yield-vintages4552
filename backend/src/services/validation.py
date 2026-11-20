"""售后随访领域的严格输入校验。所有日期统一 YYYY-MM-DD。"""
import re
from datetime import date

from src.constants.enums import OUTCOMES, OUTCOME_ACTIONS

_DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')


def parse_date(value, field):
    if not isinstance(value, str) or not _DATE_RE.match(value):
        raise ValueError(f'{field} 必须是 YYYY-MM-DD 格式日期')
    try:
        y, m, d = (int(x) for x in value.split('-'))
        return date(y, m, d)
    except ValueError:
        raise ValueError(f'{field} 不是合法日历日期')


def text(value, field, max_len=200, required=True):
    if value is None or (isinstance(value, str) and not value.strip()):
        if required:
            raise ValueError(f'{field} 不能为空')
        return None
    if not isinstance(value, str) or len(value) > max_len:
        raise ValueError(f'{field} 必须为 1-{max_len} 字的非空文本')
    return value.strip()


def validate_line(data):
    if not isinstance(data, dict) or set(data) != {'code', 'name'}:
        raise ValueError('随访线字段必须且只能包含 code、name')
    text(data['code'], '随访线编号', 60)
    text(data['name'], '随访线名称', 120)
    return {'code': data['code'].strip(), 'name': data['name'].strip()}


def validate_batch(data):
    """批次录入/更正：出厂日、入组日、记录到账日（record_date）。"""
    if not isinstance(data, dict) or set(data) != {'batch_no', 'line_code', 'ship_date', 'enroll_date', 'record_date'}:
        raise ValueError('批次字段必须且只能包含 batch_no、line_code、ship_date、enroll_date、record_date')
    batch_no = text(data['batch_no'], '批次号', 80)
    line_code = text(data['line_code'], '随访线编号', 60)
    ship = parse_date(data['ship_date'], '出厂日期')
    enroll = parse_date(data['enroll_date'], '入组日期')
    record = parse_date(data['record_date'], '记录到账日期')
    if enroll < ship:
        raise ValueError('入组日期不能早于出厂日期')
    if record < ship:
        raise ValueError('记录到账日期不能早于出厂日期（迟报也不能倒签至出厂前）')
    return {'batch_no': batch_no, 'line_code': line_code, 'ship_date': ship,
            'enroll_date': enroll, 'record_date': record}


def validate_outcome(data, void=False):
    """结局登记/更正/作废。作废只需 batch_no + record_date。"""
    allowed = {'batch_no', 'record_date'} if void else \
        {'batch_no', 'outcome', 'event_date', 'reason', 'record_date'}
    if not isinstance(data, dict) or set(data) != allowed:
        raise ValueError('结局字段集合不匹配：' + '、'.join(sorted(allowed)))
    batch_no = text(data['batch_no'], '批次号', 80)
    record = parse_date(data['record_date'], '报送/更正到账日期')
    if void:
        return {'batch_no': batch_no, 'record_date': record}
    if data['outcome'] not in OUTCOMES:
        raise ValueError('结局类型必须是 repair / scrap / censor')
    event = parse_date(data['event_date'], '结局发生日期')
    reason = text(data.get('reason'), '失败原因', 200,
                  required=data['outcome'] in ('repair', 'scrap'))
    if data['outcome'] == 'censor' and data.get('reason'):
        raise ValueError('随访结束为删失，不登记失败原因')
    return {'batch_no': batch_no, 'outcome': data['outcome'], 'event_date': event,
            'reason': reason, 'record_date': record}


def validate_action(action):
    if action not in OUTCOME_ACTIONS:
        raise ValueError('结局动作必须是 report / correct / void')
    return action


def validate_audit_date(value):
    return parse_date(value, '查账日')
