import requests
import json
import time
import logging
from requests.auth import HTTPBasicAuth

def retry_request(method, url, max_retries=10, timeout=300, delay=5, **kwargs):
    """
    通用的重试逻辑。
    如果请求失败则进行重试，超时后重新登录。
    如果重新登录超过 max_retries，则报错终止脚本。

    :param method     : 请求方法 (e.g., SESS.get, SESS.patch)
    :param url        : 请求的目标地址
    :param max_retries: 最大重新登录次数
    :param timeout    : 每次重试的超时时间
    :param delay      : 两次请求的间隔时间
    :param kwargs     : 请求参数 (e.g., json, headers)
    """
    retry_count = 0
    start_time  = time.time()
    while retry_count <= max_retries:
        try:
            response = method(url, **kwargs)
            response.raise_for_status()
            result = response.json()
            return result
        except Exception as e:
            elapsed_time = time.time() - start_time
            if elapsed_time < timeout:
                logging.warning(f"Request to {url} failed. Retrying after {delay} seconds... Elapsed time: {elapsed_time:.2f}s.")
                time.sleep(delay)
            else:
                if retry_count < max_retries:
                    logging.warning(f"Timeout reached. Attempting re-login... (Retry count: {retry_count + 1})")
                    global SESS
                    SESS = global_sign_in()
                    start_time = time.time()
                    retry_count += 1
                else:
                    logging.error(f"Request to {url} failed after {max_retries} re-login attempts.")
                    return None
                    #raise RuntimeError(f"Request to {url} failed after {max_retries} re-login attempts.") from e

def setup_logging(level=logging.INFO, log_file='app.log', log_to_file=True):
    """
    设置日志配置，默认输出到控制台和文件，可选择关闭文件输出。
    :param level: 日志级别，默认为 INFO
    :param log_file: 日志文件路径，默认为 'app.log'
    :param log_to_file: 是否将日志输出到文件，默认为 True
    """
    handlers = [logging.StreamHandler()]
    if log_to_file:
        handlers.append(logging.FileHandler(log_file, mode='w'))
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=handlers
    )

def global_sign_in():
    credential_file = 'brain_credential.txt'
    with open(credential_file) as f:
        username,password = json.load(f)

    sess       = requests.Session()
    sess.auth  = HTTPBasicAuth(username,password)
    timeout    = 300
    start_time = time.time()
    while True:
        try:
            response = sess.post('https://api.worldquantbrain.com/authentication')
            response.raise_for_status()
            break
        except:
            elapsed_time = time.time() - start_time
            print("Connection down, trying to login again...")
            if elapsed_time >= timeout:
                print(f"{username} login Failed, returning None.")
                return None
            time.sleep(15)
    id = response.json().get("user").get("id")
    print(f"{id} Login to BRAIN successfully.")
    return sess

if __name__ == "__main__":
    SESS = global_sign_in()
