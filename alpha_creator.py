import csv
import random
import pandas as pd
from auth_utils import global_sign_in

# Alpha Setting
INSTRUMENTTYPE = 'EQUITY'
REGION         = 'ASI'
UNIVERSE       = 'MINVOL1M'
DELAY          = 1
DECAY          = 6
NEUTRALIZATION = 'SUBINDUSTRY'
TRUNCATION     = 0.08
PASTEURIZATION = 'ON'
UNITHANDLING   = 'VERIFY'
NANHANDLING    = 'ON'
LANGUAGE       = 'FASTEXPR'
VISUALIZATION  = False
TESTPERIOD     = 'P2Y'

# Dataset Field
DATASET_FILED = 'fundamental6'
DATASET_TYPE  = 'MATRIX'

def get_datafields(sess, instrument_type: str, region: str, delay: int, universe: str, dataset_filed: str, search: str=''):
    if len(search) == 0:
        url_template = "https://api.worldquantbrain.com/data-fields?" +\
            f"&instrumentType={instrument_type}" +\
            f"&region={region}&delay={str(delay)}&universe={universe}&dataset.id={dataset_filed}&limit=50" +\
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
    return datafields_df

def create_alpha():
    datafields = get_datafields(SESS, instrument_type = INSTRUMENTTYPE,region=REGION, universe=UNIVERSE, delay=DELAY, dataset_filed = DATASET_FILED)
    company_datafields = datafields[datafields['type'] == DATASET_TYPE]["id"].tolist()
    alpha_expressions    = []

    group_compare_ops = ['group_rank', 'group_zscore', 'group_neutralize']
    ts_compare_ops1   = ['ts_rank', 'ts_zscore', 'ts_av_diff', 'ts_mean']
    ts_compare_ops2   = ['ts_decay_exp_window', 'ts_decay_linear']
    group_types       = ['market', 'industry', 'subindustry', 'sector']
    market_metrics    = ['adv20','cap','returns','volume','vwap']
    lookback_periods  = [60, 120, 240]

    for gco in group_compare_ops:
        for tco1 in ts_compare_ops1:
            for tco2 in ts_compare_ops2:
                for cmp_fund in company_datafields:
                    for grp in group_types:
                        # 计算分析师情绪的偏离程度
                        analyst_sentiment_deviation = f"mdl110_analyst_sentiment - {tco1}(mdl110_analyst_sentiment, 60)"
                        # 指数衰减平滑处理，强化近期情绪变化趋势
                        smoothed_sentiment_trend = f"{tco2}({analyst_sentiment_deviation}, 20)"
                        # 计算成交量的市场排名
                        volume_rank = f"rank({cmp_fund})"
                        # 计算最终信号（情绪趋势 × 成交量排名）
                        combined_signal = f"{smoothed_sentiment_trend} * {volume_rank}"
                        # 行业中性化，去除行业影响
                        alpha_expression = f"{gco}({combined_signal}, {grp})"
                        alpha_expressions.append(alpha_expression)

    print(f'there are total {len(alpha_expressions)} alpha expressions')
    alpha_list = []

    for alpha_expression in alpha_expressions:
        simulation_data = {
            'type': 'REGULAR',
            'settings': {
                'instrumentType': INSTRUMENTTYPE,
                'region': REGION,
                'universe': UNIVERSE,
                'delay': DELAY,
                'decay': DECAY,
                'neutralization': NEUTRALIZATION,
                'truncation': TRUNCATION,
                'pasteurization': PASTEURIZATION,
                'unitHandling': UNITHANDLING,
                'nanHandling': NANHANDLING,
                'language': LANGUAGE,
                'visualization': VISUALIZATION,
                'testPeriod': TESTPERIOD
            },
            'regular': alpha_expression
        }
        alpha_list.append(simulation_data)
    random.shuffle(alpha_list)
    return alpha_list

if __name__ == "__main__":
    SESS            = global_sign_in()
    ALPHA_LIST      = create_alpha()

    with open('alphas_pending_simulated.csv', 'w', newline='') as output_file:
        dict_writer = csv.DictWriter(output_file, fieldnames=['type', 'settings', 'regular'])
        dict_writer.writeheader()
        dict_writer.writerows(ALPHA_LIST)
