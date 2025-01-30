import logging
import time
import csv
import requests
import os
import ast
from datetime import datetime
from pytz import timezone
from auth_utils import global_sign_in, setup_logging

class AlphaSimulator:
    def __init__(self, max_concurrent: int, alpha_list_file:str):
        """
        初始化 AlphaSimulator 类。

        :param max_concurrent     : 最大并发数
        :param alpha_list_file    : Alpha 列表文件路径
        :param alphas_simulated   : 已完成 Simulate 的 Alphas 保存文件
        :param alphas_queue       : 等待队列中的 Alphas 保存文件
        :param active_simulations : 正在 Simulate 的 Alpha location url
        :param session            : 登入窗口
        :param sim_queue_ls       : 等待队列中的 Alphas
        :param batch_num_per_queue: 每个队列的批次数量
        """
        self.max_concurrent      = max_concurrent
        self.alpha_list_file     = alpha_list_file
        self.alphas_simulated    = 'alphas_simulated.csv'
        self.alphas_queue        = 'alphas_simulate_queue.csv'
        self.active_simulations  = []
        self.session             = self.sign_in()
        self.sim_queue_ls        = []
        self.batch_num_per_queue = max_concurrent * 2

    def sign_in(self):
        session = global_sign_in()
        logging.info("Login to BRAIN successfully.")
        return session

    def read_alphas_from_csv_in_batches(self, batch_num_per_queue):
        '''
        1. 打开 alpha_list_file 文件
        2. 取出 batch_num_per_queue 个 alpha，放入列表变量 alphas
        3. 取出后覆写 alpha_list_file 文件
        4. 把取出的 alphas，写到 alphas_queue 文件中，方便随时监控排队中的 alpha
        5. 返回列表变量 alphas
        '''
        alphas = []
        temp_file_name = self.alpha_list_file + '.tmp'
        with open(self.alpha_list_file, 'r') as file, open(temp_file_name, 'w', newline='') as temp_file:
            reader     = csv.DictReader(file)
            fieldnames = reader.fieldnames
            writer     = csv.DictWriter(temp_file, fieldnames=fieldnames)
            writer.writeheader()
            for _ in range(batch_num_per_queue):
                try:
                    row = next(reader)
                    if 'settings' in row:
                        if isinstance(row['settings'], str):
                            try:
                                row['settings'] = ast.literal_eval(row['settings'])
                            except (ValueError, SyntaxError):
                                logging.error(f"Error evaluating settings: {row['settings']}")
                        elif isinstance(row['settings'], dict):
                            pass
                        else:
                            logging.error(f"Unexpected type for settings: {type(row['settings'])}")
                    alphas.append(row)
                except StopIteration:
                    break
            for remaining_row in reader:
                writer.writerow(remaining_row)
        os.replace(temp_file_name, self.alpha_list_file)
        if alphas:
            with open(self.alphas_queue, 'w', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=alphas[0].keys())
                if file.tell() == 0:
                    writer.writeheader()
                writer.writerows(alphas)
        return alphas

    def simulate_alpha(self, alpha):
        count = 0
        while True:
            try:
                response = self.session.post('https://api.worldquantbrain.com/simulations', json=alpha)
                response.raise_for_status()
                if "Location" in response.headers:
                    logging.info("Alpha location retrieved successfully.")
                    logging.info(f"Location: {response.headers['Location']}")
                    return response.headers['Location']
            except requests.exceptions.RequestException as e:
                logging.error(f"Error in sending simulation request: {e}")
                if count > 35:
                    self.session = self.sign_in()
                    logging.error("Error occurred too many times, skipping this alpha and re-logging in.")
                    break
                logging.error("Error in sending simulation request. Retrying after 5s...")
                time.sleep(5)
                count += 1
        logging.error(f"Simulation request failed after {count} attempts.")
        return None

    def load_new_alpha_and_simulate(self):
        if len(self.sim_queue_ls) < 1:
            self.sim_queue_ls = self.read_alphas_from_csv_in_batches(self.batch_num_per_queue)
        if len(self.active_simulations) >= self.max_concurrent:
            logging.info(f"Max concurrent simulations reached ({self.max_concurrent}). Waiting 2 seconds")
            time.sleep(2)
            return
        logging.info('Loading new alpha...')
        try:
            alpha = self.sim_queue_ls.pop(0)
            logging.info(f"Starting simulation for alpha: {alpha['regular']} with settings: {alpha['settings']}")
            location_url = self.simulate_alpha(alpha)
            if location_url:
                self.active_simulations.append(location_url)
        except IndexError:
            logging.info("No more alphas available in the queue.")

    def check_simulation_progress(self, simulation_progress_url):
        try:
            simulation_progress = self.session.get(simulation_progress_url)
            simulation_progress.raise_for_status()
            if simulation_progress.headers.get("Retry-After", 0) == 0:
                alpha_id = simulation_progress.json().get("alpha")
                if alpha_id:
                    alpha_response = self.session.get(f"https://api.worldquantbrain.com/alphas/{alpha_id}")
                    alpha_response.raise_for_status()
                    return alpha_response.json()
                else:
                    return simulation_progress.json()
            else:
                return None
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching simulation progress: {e}")
            self.session = self.sign_in()
            return None

    def check_simulation_status(self):
        count = 0
        if len(self.active_simulations) == 0:
            logging.info("No one is in active simulation now")
            return None
        for sim_url in self.active_simulations:
            sim_progress = self.check_simulation_progress(sim_url)
            if sim_progress is None:
                count += 1
                continue
            alpha_id  = sim_progress.get("id")
            status    = sim_progress.get("status")
            logging.info(f"Alpha id: {alpha_id} ended with status: {status}. Removing from active list.")
            self.active_simulations.remove(sim_url)
            with open(self.alphas_simulated, 'a', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=sim_progress.keys())
                writer.writerow(sim_progress)
        logging.info(f"Total {count} simulations are in process for account.")

    def manage_simulations(self):
        while True:
            self.check_simulation_status()
            self.load_new_alpha_and_simulate()
            time.sleep(3)

if __name__ == "__main__":
    setup_logging(log_file='simulation.log')
    logging.info("Current time in Eastern is %s" % datetime.now(timezone('US/Eastern')).strftime('%Y-%m-%d'))

    ALPHA_PENDING_SIMULATED = 'alphas_pending_simulated.csv'
    MAX_CONCURRENT          = 10
    simulator               = AlphaSimulator(MAX_CONCURRENT, ALPHA_PENDING_SIMULATED)
    simulator.manage_simulations()
