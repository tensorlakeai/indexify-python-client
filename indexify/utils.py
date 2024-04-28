from enum import Enum
from dataclasses import is_dataclass, asdict

def json_set_default(obj):
    if isinstance(obj, set):
        return list(obj)
    elif isinstance(obj, Enum):
        return obj.value
    elif is_dataclass(obj):
        return asdict(obj)
    elif obj is None:
        return None
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")