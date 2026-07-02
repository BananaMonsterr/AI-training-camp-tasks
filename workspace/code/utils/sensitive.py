"""
敏感字段脱敏工具
"""


def mask_id_card(id_card: str) -> str:
    """身份证号脱敏：110101********1234"""
    if not id_card or len(id_card) < 8:
        return id_card
    return id_card[:6] + "********" + id_card[-4:]


def mask_phone(phone: str) -> str:
    """手机号脱敏：138****8000"""
    if not phone or len(phone) < 7:
        return phone
    return phone[:3] + "****" + phone[-4:]


def mask_email(email: str) -> str:
    """邮箱脱敏：z****@company.com"""
    if not email or "@" not in email:
        return email
    local, domain = email.split("@", 1)
    if len(local) <= 1:
        return f"{local}****@{domain}"
    return local[0] + "****@" + domain


def mask_name(name: str) -> str:
    """姓名脱敏：张*"""
    if not name:
        return name
    if len(name) == 2:
        return name[0] + "*"
    return name[0] + "*" * (len(name) - 2) + name[-1]


def auto_mask(obj: dict, sensitive_fields: list = None) -> dict:
    """
    自动对字典中的敏感字段进行脱敏
    sensitive_fields: [(field_name, mask_func), ...]
    """
    if sensitive_fields is None:
        sensitive_fields = [
            ("id_card", mask_id_card),
            ("phone", mask_phone),
            ("email", mask_email),
        ]

    result = obj.copy()
    for field, mask_func in sensitive_fields:
        if field in result and result[field]:
            result[field] = mask_func(result[field])
    return result
