import argparse
from auth_utils import global_sign_in, setup_logging, retry_request

parser = argparse.ArgumentParser()
parser.add_argument("alpha_id", type=str)

args = parser.parse_args()
setup_logging(log_to_file=False)
SESS = global_sign_in()
url = f"https://api.worldquantbrain.com/alphas/{args.alpha_id}"
result = retry_request(SESS.get, f"{url}")
print(result)
