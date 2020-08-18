import re
import singer


LOGGER = singer.get_logger()


# Convert camelCase to snake_case and remove forward slashes
def convert(name):
    # regsub = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    nospaces = re.sub(' ', '_', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', nospaces).lower()


# Convert keys in json array
def convert_array(arr):
    new_arr = []
    for i in arr:
        if isinstance(i, list):
            new_arr.append(convert_array(i))
        elif isinstance(i, dict):
            new_arr.append(convert_json(i))
        else:
            new_arr.append(i)
    return new_arr


# Convert keys in json
def convert_json(this_json):
    out = {}
    if isinstance(this_json, dict):
        for key in this_json:
            if key == 'items':
                new_key = 'list_items'
            else:
                new_key = convert(key)
            if isinstance(this_json[key], dict):
                out[new_key] = convert_json(this_json[key])
            elif isinstance(this_json[key], list):
                out[new_key] = convert_array(this_json[key])
            else:
                out[new_key] = this_json[key]
    else:
        return convert_array(this_json)
    return out

def transform(this_json):
    converted = convert_json(this_json)
    return convert_json(converted)
