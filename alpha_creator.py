import csv
import os
import pandas as pd
import numpy as np
from auth_utils import global_sign_in

def get_datafields(sess, searchScope, dataset_id: str = '', search: str = ''):
    instrument_type = searchScope['instrumentType']
    region          = searchScope['region']
    delay           = searchScope['delay']
    universe        = searchScope['universe']
    if len(search) == 0:
        url_template = "https://api.worldquantbrain.com/data-fields?" +\
            f"&instrumentType={instrument_type}" +\
            f"&region={region}&delay={str(delay)}&universe={universe}&dataset.id={dataset_id}&limit=50" +\
            "&offset={x}"
        count = sess.get(url_template.format (x=0)).json()['count']
    else:
        url_template = "https://api.worldquantbrain.com/data-fields?" +\
            f"&instrumentType={instrument_type}" +\
            f"&region={region}&delay={str(delay)}&universe={universe}&limit=50" +\
            f"&search={search}" +\
            "&offset={x}"
        count = 100

    datafields_list = []
    for x in range(0, count, 50):
        datafields = sess.get (url_template. format (x=x))
        datafields_list.append (datafields. json()['results'])

    datafields_list_flat = [item for sublist in datafields_list for item in sublist]
    datafields_df        = pd.DataFrame(datafields_list_flat)
    datafields_df        = datafields_df.sample(frac=1, random_state=np.random.randint(0, 10000)).reset_index(drop=True)

    return datafields_df

def create_alpha():
    searchscope = {'region':'USA','delay':'1','universe':'TOP3000','instrumentType':'EQUITY'}
    dataset_id  = 'fundamental6'
    fundamental = get_datafields(SESS, searchscope, dataset_id)
    fundamental = fundamental[fundamental['type']=="MATRIX"]
    fundamental.head()
    company_fundamentals = fundamental['id'].values
    alpha_expressions    = []

    group_compare_op = ['group_rank','group_zscore','group_neutralize']# ......
    ts_compare_op = ['ts_rank','ts_zscore', 'ts_av_diff']
    days = [252,504]
    group = ['market', 'industry', 'subindustry', 'sector', 'densify(pv13_h_f1_sector)']

    for gco in group_compare_op:
        for tco in ts_compare_op:
            for cf in company_fundamentals:
                for day in days:
                    for grp in group:
                        alpha_expressions.append(f"{gco} ( {tco}({cf}, {day}) , {grp})")

    print(f'there are total {len(alpha_expressions)} alpha expressions')
    alpha_list = []
    for alpha_expression in alpha_expressions:
        simulation_data = {
            'type': 'REGULAR',
            'settings': {
                'instrumentType': 'EQUITY',
                'region': 'USA',
                'universe': 'TOP3000',
                'delay': 1,
                'decay': 0,
                'neutralization': 'SUBINDUSTRY',
                'truncation': 0.01,
                'pasteurization':'ON',
                'unitHandling':'VERIFY',
                'nanHandling':'ON',
                'language': 'FASTEXPR',
                'visualization': False,
                'testPeriod': 'P2Y'
                },
            'regular': alpha_expression
            }
        alpha_list.append(simulation_data)
    return alpha_list

if __name__ == "__main__":
    SESS            = global_sign_in()
    ALPHA_LIST      = create_alpha()
    ALPHA_LIST_FILE = 'alphas_pending_simulated.csv'

    with open(ALPHA_LIST_FILE, 'a', newline='') as output_file:
        dict_writer = csv.DictWriter(output_file, fieldnames=['type', 'settings', 'regular'])
        if not os.path.isfile(ALPHA_LIST_FILE):
            dict_writer.writeheader()
        dict_writer.writerows(ALPHA_LIST)
