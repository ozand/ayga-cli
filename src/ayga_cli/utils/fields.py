from typing import Any, Dict, List, Union

def _get_nested_value(data: Dict[str, Any], path: str) -> Any:
    keys = path.split(".")
    current = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current

def _set_nested_value(data: Dict[str, Any], path: str, value: Any) -> None:
    keys = path.split(".")
    current = data
    for key in keys[:-1]:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value

def filter_fields(data: Union[Dict[str, Any], List[Any]], fields: Union[str, None]) -> Union[Dict[str, Any], List[Any]]:
    if not fields:
        return data

    field_list = [f.strip() for f in fields.split(",") if f.strip()]
    if not field_list:
        return data

    if isinstance(data, list):
        return [filter_fields(item, fields) for item in data]
    
    if isinstance(data, dict):
        result = {}
        for field in field_list:
            val = _get_nested_value(data, field)
            if val is not None:
                _set_nested_value(result, field, val)
        return result
        
    return data
