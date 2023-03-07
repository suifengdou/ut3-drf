from functools import reduce
from django.db.models import F, Q


def andconmbine(condition_list, name, *args, **kwargs):
    try:
        _condition_dict = {}
        condition = None
        for value in condition_list:
            _condition_dict[name] = value
            if not condition:
                condition = Q(**_condition_dict)
            else:
                condition = condition | Q(**_condition_dict)
    except Exception as e:
        return None
    return condition


def orconmbine(condition_list, name, *args, **kwargs):
    try:
        _condition_dict = {}
        condition = None
        for value in condition_list:
            _condition_dict[name] = value
            if not condition:
                condition = Q(**_condition_dict)
            else:
                condition = condition | Q(**_condition_dict)
    except Exception as e:
        return None
    return condition





