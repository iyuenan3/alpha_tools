import logging
import time
from auth_utils import global_sign_in, setup_logging, retry_request

def submit_alpha(alpha_id):
    max_wait_time  = 600
    check_interval = 30
    elapsed_time   = 0
    base_url       = f"https://api.worldquantbrain.com/alphas/{alpha_id}"
    retry_request(SESS.post, f"{base_url}/submit")
    while elapsed_time < max_wait_time:
        result = retry_request(SESS.get, f"{base_url}")
        if result is None:
            logging.warning(f"Get Alpha {alpha_id} Status returned None. Retrying in {check_interval} seconds...")
        elif result.get("status") == 'ACTIVE':
            logging.info(f"Alpha {alpha_id} Submit SUCCEED.")
            return True
        else:
            logging.info(f"Alpha {alpha_id} status: {result.get('status', 'UNKNOWN')}. Retrying in {check_interval} seconds...")
        time.sleep(check_interval)
        elapsed_time += check_interval

    if retry_request(SESS.patch, base_url, json={"color": None}):
        logging.info(f"Alpha {alpha_id} Submit FAIL, Clear Alpha Color.")
    else:
        logging.warning(f"Alpha {alpha_id} Submit FAIL, Clear Alpha Color Fail.")
    return False

def check_alpha_submission(alpha_id):
    base_url = f"https://api.worldquantbrain.com/alphas/{alpha_id}"
    if retry_request(SESS.patch, base_url, json={"color": "YELLOW"}):
        logging.info(f"Mark Alpha {alpha_id} in YELLOW, Reset SELF_CORRELATION to PENDING.")
    else:
        logging.error(f"Mark Alpha {alpha_id} in YELLOW Fail, Skip this Alpha.")
        return False

    result = retry_request(SESS.get, f"{base_url}/check", delay=30)
    if result is None:
        logging.error(f"Get Alpha {alpha_id} IS CHECK Status Fail, Skip this Alpha.")
        return False

    checks = result["is"]["checks"]
    fail_check = [item for item in checks if item['result'] == 'FAIL']
    for item in fail_check:
        logging.info(f"Alpha {alpha_id} Check Submission FAIL Item: {item}")

    if all(check.get("result") == "PASS" for check in checks):
        if retry_request(SESS.patch, base_url, json={"color": "BLUE"}):
            logging.info(f"Alpha {alpha_id} Check Submission PASS, Mark Alpha in BLUE.")
        else:
            logging.warning(f"Alpha {alpha_id} Check Submission PASS, But Mark Alpha in BLUE Fail.")
        return True
    else:
        if retry_request(SESS.patch, base_url, json={"color": None}):
            logging.info(f"Alpha {alpha_id} Check Submission FAIL, Clear Alpha Color.")
        else:
            logging.warning(f"Alpha {alpha_id} Check Submission FAIL, Clear Alpha Color Fail.")
        return False

def get_alpha_list():
    status_filter       = "UNSUBMITTED"
    fitness_filter      = "is.fitness%3E1"
    sharpe_filter       = "is.sharpe%3E1.25"
    turnover_filter     = "is.turnover%3E0.01&is.turnover%3C0.7"
    alpha_filter        = f"status={status_filter}&{fitness_filter}&{sharpe_filter}&{turnover_filter}&order=-dateCreated&hidden=false"
    alpha_filtered_list = []
    offset              = 0
    limit               = 100
    base_url            = "http://api.worldquantbrain.com"
    while True:
        path   = f"/users/self/alphas?limit={limit}&offset={offset}&{alpha_filter}"
        url    = f"{base_url}{path}"
        result = retry_request(SESS.get, url)
        if result:
            alphas = result.get("results", [])
            alpha_filtered_list.extend(alphas)
            count   = result.get("count", 0)
            offset += limit
            if offset >= count:
                break
        else:
            raise RuntimeError(f"Request to {url} Failed.")

    alpha_nofaile_list = []
    for alpha in alpha_filtered_list:
        is_checks = alpha.get("is", {}).get("checks", None)
        if is_checks and 'FAIL' not in str(is_checks):
            alpha_nofaile_list.append(alpha)

    logging.info("+" + "="*124 + "+")
    logging.info(f"{len(alpha_filtered_list)} Alphas Passed Filter (Sharpe>1.25, Fitness>1, 70>Turnover>1).")
    logging.info(f"{len(alpha_nofaile_list)} Alphas IS CHECKS No FAIL, Waiting to Check Submission")
    logging.info("+" + "="*124 + "+")
    return alpha_nofaile_list

def get_checked_alphas():
    alpha_list          = get_alpha_list()
    total_alphas        = len(alpha_list)
    alpha_checked_list  = []
    alpha_checked_count = 0
    for index, alpha in enumerate(alpha_list, start=1):
        alpha_id = alpha.get("id")
        logging.info(f"+[{index:04d}/{total_alphas:04d}] Alpha id: {alpha_id} Start Check Submission" + "-"*72 + "+")
        if check_alpha_submission(alpha_id):
            alpha_checked_count += 1
            alpha_checked_list.append(alpha)
        logging.info(f"Currently {alpha_checked_count} Alphas PASS Check Submission.")
        logging.info("+" + "-"*124 + "+")

    logging.info("+" + "-" * 32 + "+")
    for alpha in alpha_checked_list:
        logging.info(f"| {alpha.get('id')} PASS Check Submission. |")
    logging.info("+" + "-" * 32 + "+")
    return alpha_checked_list

def get_submited_alphas():
    alpha_list           = get_alpha_list()
    total_alphas         = len(alpha_list)
    alpha_submited_list  = []
    alpha_submited_count = 0
    for index, alpha in enumerate(alpha_list, start=1):
        alpha_id = alpha.get("id")
        logging.info(f"+[{index:04d}/{total_alphas:04d}] Alpha id: {alpha_id} Start Check Submission" + "-"*72 + "+")
        if check_alpha_submission(alpha_id):
            if submit_alpha(alpha_id):
                alpha_submited_count += 1
                alpha_submited_list.append(alpha)
        logging.info(f"Currently {alpha_submited_count} Alphas Submited.")
        logging.info("+" + "-"*124 + "+")

    logging.info("+" + "-" * 19 + "+")
    for alpha in alpha_submited_list:
        logging.info(f"| {alpha.get('id')} Submited. |")
    logging.info("+" + "-" * 19 + "+")
    return alpha_submited_list

if __name__ == "__main__":
    setup_logging(log_file='check.log')
    SESS       = global_sign_in()
    get_checked_alphas()
    #get_submited_alphas()
