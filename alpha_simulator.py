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
    def __init__(self, max_concurrent: int, alpha_list_file: str):
        self.max_concurrent = max_concurrent
        self.alpha_list_file = alpha_list_file
        self.alphas_simulated = 'alphas_simulated.csv'
        self.active_simulations = []
        self.session = global_sign_in()
        self.sim_queue_ls = []
        self.batch_num_per_queue = max_concurrent * 2

    def read_alphas_from_csv_in_batches(self):
        alphas = []
        temp_file_name = self.alpha_list_file + '.tmp'

        with open(self.alpha_list_file, 'r') as file, open(temp_file_name, 'w', newline='') as temp_file:
            reader = csv.DictReader(file)
            fieldnames = reader.fieldnames
            writer = csv.DictWriter(temp_file, fieldnames=fieldnames)
            writer.writeheader()

            for _ in range(self.batch_num_per_queue):
                row = next(reader, None)
                if not row:
                    break

                if 'settings' in row:
                    try:
                        row['settings'] = ast.literal_eval(row['settings']) if isinstance(row['settings'], str) else row['settings']
                    except (ValueError, SyntaxError):
                        logging.error(f"Error evaluating settings: {row['settings']}")
                        continue
                alphas.append(row)

            writer.writerows(reader)

        os.replace(temp_file_name, self.alpha_list_file)
        return alphas

    def simulate_alpha(self, alpha):
        for attempt in range(36):
            try:
                response = self.session.post('https://api.worldquantbrain.com/simulations', json=alpha)
                response.raise_for_status()
                if "Location" in response.headers:
                    logging.info(f"Alpha location retrieved successfully: {response.headers['Location']}")
                    return response.headers['Location']
            except requests.exceptions.RequestException as e:
                logging.error(f"Simulation request error: {e}. Retrying in 5s...")
                time.sleep(5)

        logging.error("Simulation request failed after multiple attempts, re-logging in.")
        self.session = global_sign_in()
        return None

    def load_new_alpha_and_simulate(self):
        if not self.sim_queue_ls:
            self.sim_queue_ls = self.read_alphas_from_csv_in_batches()

        if len(self.active_simulations) >= self.max_concurrent:
            logging.info(f"Max concurrent simulations reached ({self.max_concurrent}). Waiting 2s...")
            time.sleep(2)
            return

        if self.sim_queue_ls:
            alpha = self.sim_queue_ls.pop(0)
            logging.info(f"Simulating alpha: {alpha['regular']} with settings: {alpha['settings']}")
            location_url = self.simulate_alpha(alpha)
            if location_url:
                self.active_simulations.append(location_url)
        else:
            logging.info("No more alphas available in the queue.")

    def check_simulation_progress(self, url):
        try:
            response = self.session.get(url)
            response.raise_for_status()
            if response.headers.get("Retry-After", 0) == 0:
                alpha_id = response.json().get("alpha")
                return self.session.get(f"https://api.worldquantbrain.com/alphas/{alpha_id}").json() if alpha_id else response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching simulation progress: {e}")
            self.session = global_sign_in()
        return None

    def check_simulation_status(self):
        if not self.active_simulations:
            logging.info("No active simulations.")
            return

        pending_simulations = []

        with open(self.alphas_simulated, 'a+', newline='') as file:
            file.seek(0, os.SEEK_END)
            is_empty = file.tell() == 0
            writer = csv.DictWriter(file, fieldnames=["id", "regular"])
            if is_empty:
                writer.writeheader()

            for sim_url in self.active_simulations:
                result = self.check_simulation_progress(sim_url)
                if result:
                    logging.info(f"Alpha id: {result.get('id')} finished with status: {result.get('status')}")
                    writer.writerow({"id": result.get("id"), "regular": result.get("regular")})
                else:
                    pending_simulations.append(sim_url)

        self.active_simulations = pending_simulations
        logging.info(f"{len(self.active_simulations)} simulations still in progress.")

    def manage_simulations(self):
        try:
            while True:
                self.check_simulation_status()
                self.load_new_alpha_and_simulate()
                time.sleep(3)
        except KeyboardInterrupt:
            logging.info("Ctrl+C detected. Waiting for active simulations to finish before exiting...")
            self.finish_active_simulations()
            logging.info("All active simulations processed. Exiting safely.")

    def finish_active_simulations(self):
        while self.active_simulations:
            self.check_simulation_status()
            logging.info(f"Waiting for {len(self.active_simulations)} active simulations to complete...")
            time.sleep(3)

if __name__ == "__main__":
    setup_logging(log_file='simulation.log', log_to_file=True, log_to_console=False)
    logging.info(f"Current time in Eastern: {datetime.now(timezone('US/Eastern')).strftime('%Y-%m-%d %H:%M:%S')}")
    simulator = AlphaSimulator(max_concurrent=10, alpha_list_file='alphas_pending_simulated.csv')
    simulator.manage_simulations()
