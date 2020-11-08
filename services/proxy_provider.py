import concurrent.futures
import os
import random
import base64
import time

import requests
from bs4 import BeautifulSoup

from utils import log

logger = log.setup_console_logger(os.path.basename(__file__))


class ProxyProviderService:
    __instance = None

    @staticmethod
    def get_instance():
        """ Static access method. """
        if ProxyProviderService.__instance is None:
            ProxyProviderService()
        return ProxyProviderService.__instance

    def __init__(self):
        self.checked_proxy_list = []
        """ Virtually private constructor. """
        if ProxyProviderService.__instance is not None:
            raise Exception("This class is a singleton!")
        else:
            ProxyProviderService.__instance = self

    def scrape_proxies_from_free_proxy_list(self):
        url = "https://free-proxy-list.net"
        result = []
        logger.info(f"starting collecting proxies from: {url}")
        try:
            r = requests.get(url)
            soup = BeautifulSoup(r.content, 'html.parser')
            proxy_list = soup.find("div", {"class": "modal-body"}).text
            result = proxy_list.splitlines()[3:]
        except Exception as e:
            logger.error(f"there is a problem with '{url}'. {e}")
        self.check_proxies(result)

    def scrape_proxies_from_proxy_scan(self):
        urls = ['https://www.proxyscan.io/download?type=http', 'https://www.proxyscan.io/download?type=https']
        logger.info(f"starting collecting proxies from: {urls}")
        result = []
        for url in urls:
            try:
                response = requests.get(url)
                data = response.text
                result.extend(data.splitlines())
            except Exception as e:
                logger.error(f"there is a problem with '{url}'. {e}")
        self.check_proxies(result)

    def scrape_proxies_from_github(self):
        urls = ["https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
                "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt"]
        result = []
        logger.info(f"starting collecting proxies from: {urls}")
        for url in urls:
            try:
                r = requests.get(url)
                soup = BeautifulSoup(r.content, 'html.parser')
                result = soup.text.splitlines()
            except Exception as e:
                logger.error(f"there is a problem with '{url}'. {e}")
        self.check_proxies(result)

    def scrape_proxies_from_free_proxy(self):
        urls = ["http://free-proxy.cz/en/proxylist/country/DE/all/ping/all"]
        result = []
        logger.info(f"starting collecting proxies from: {urls}")
        import re
        pattern = r'"([A-Za-z0-9_\./\\-]*)"'

        for url in urls:
            try:
                r = requests.get(url)
                soup = BeautifulSoup(r.content, 'html.parser')
                rows = soup.find("table", {"id": "proxy_list"}).find("tbody").find_all("tr")
                for row in rows:
                    script = str(row.find("script")).replace('type="text/javascript"', "")
                    try:
                        # logger.debug(re.search(pattern, script).group())
                        match = re.search(pattern, script)
                        if match:
                            decoded_ip = base64.b64decode(match.group()).decode('ascii')
                            if decoded_ip:
                                logger.debug(decoded_ip)
                                logger.debug(f"{decoded_ip}:{row.find_all('td')[1].text}")
                                result.append(f"{decoded_ip}:{row.find_all('td')[1].text}")
                    except Exception as e:
                        logger.error(e)
            except Exception as e:
                logger.error(f"there is a problem with '{url}'. {e}")
        self.check_proxies(result)

    def check_proxy(self, proxy):
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36'}
        try:
            # https://httpbin.org/ip doesnt block anything
            r = requests.get('https://httpbin.org/ip', headers=headers, proxies={"http": f"http://{proxy}", "https": f"https://{proxy}"}, timeout=2)
            logger.debug(f"{r.json()}, {r.status_code}, -  working")
            self.checked_proxy_list.append(proxy)
        except Exception as e:
            logger.debug(f"{proxy} - not working ")
            if proxy in self.checked_proxy_list:
                self.checked_proxy_list = [i for i in self.checked_proxy_list if i != proxy]

    def check_proxies(self, result):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.map(self.check_proxy, result)
            executor.shutdown(wait=True)  # wait for all threads
            self.remove_duplicates()

    def get_single_proxy(self):
        if len(self.checked_proxy_list) > 0:
            endpoint = random.choice(self.checked_proxy_list)
            return {'http': f"http://{endpoint}", 'https': f"https://{endpoint}"}
        else:
            return None

    def remove_duplicates(self):
        logger.info(f"start removing proxy duplicate. current quantity: {len(self.checked_proxy_list)}")
        self.checked_proxy_list = list(set(self.checked_proxy_list))
        logger.info(f"end removing proxy duplicates. current quantity {len(self.checked_proxy_list)}")

    def check_again(self, proxy):
        self.check_proxy(proxy)
        # self.remove_duplicates()


if __name__ == "__main__":
    start_time = time.time()

    instance = ProxyProviderService.get_instance()

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        executor.submit(instance.scrape_proxies_from_proxy_scan)
        executor.submit(instance.scrape_proxies_from_free_proxy_list)
        executor.submit(instance.scrape_proxies_from_github)
        executor.shutdown(wait=True)  # wait for all threads

        # ProxyProviderService.get_instance().scrape_proxies_from_proxy_scan()
        # ProxyProviderService.get_instance().scrape_proxies_from_free_proxy_list()
        # ProxyProviderService.get_instance().scrape_proxies_from_github()

        elapsed_time = time.time() - start_time
        logger.info(f"time needed: {time.strftime('%H:%M:%S', time.gmtime(elapsed_time))}")

    # ProxyProviderService.get_instance().scrape_proxies_from_free_proxy()
