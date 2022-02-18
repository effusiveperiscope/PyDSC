import json
from dsc import DSCData

def store_dsc(data, analyses):
    store_dict = {
        'data': data.to_dict(),
        'analyses': analyses.analyses}
    return json.dumps(store_dict)

def restore_dsc(text):
    restore_dict = json.loads(text)
    data = DSCData()
    data.__dict__.update(restore_dict['data'])
    return data, restore_dict['analyses']
