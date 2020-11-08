import concurrent.futures
import os
import traceback

import requests
from flask import Flask, request
from flask_apscheduler import APScheduler
from requests.exceptions import MissingSchema
from user_agent import generate_user_agent

from services.proxy_provider import ProxyProviderService
from utils import log

logger = log.setup_console_logger(os.path.basename(__file__))

app = Flask(__name__)

scheduler = APScheduler()

JOBS = {
    "JOB_1": "FREE-PROXY-LIST.net",
    "JOB_2": "PROXY_SCAN.io",
    "JOB_3": "GITHUB.com"
}


@app.route('/')
def welcome():
    return f'proxy server is running on: {app.config.get("PORT")}', 200


@app.route("/random/proxy")
def get_random_proxy():
    pps = ProxyProviderService.get_instance()
    proxy = pps.get_single_proxy()
    return proxy if proxy is not None else "the server is busy. try again later.", 503


@app.route("/<path:url>", methods=["GET"])
def proxy(url):
    attempts = 0
    while attempts <= 20:
        user_agent = generate_user_agent()
        used_proxy = ProxyProviderService.get_instance().get_single_proxy()
        try:
            if used_proxy is None:
                raise ValueError("no proxy available")
            if attempts == 20:
                r = requests.request("GET", url, params=request.args, stream=True, headers={'user-agent': user_agent}, timeout=1)
                logger.info(f"attempt number {attempts + 1} - request will be performed with user-agent:{generate_user_agent()} and HOST-IP")
            else:
                r = requests.request("GET", url, params=request.args, stream=True, headers={'user-agent': user_agent}, proxies=used_proxy, timeout=1)
                logger.info(f"attempt number {attempts + 1} - request will be performed with user-agent:{generate_user_agent()} and ip:{used_proxy}")

            return r.content, 200
        except MissingSchema:
            logger.warning(f"no schema supplied. value was {used_proxy}")
            return f"Invalid URL '{url}{request.args}': No schema supplied. Perhaps you meant http://{url}{request.args}?", 400
        except ValueError:
            return f"cannot connect to {url}. no proxy available", 500
        except Exception as e:
            logger.warning(f"an error has occurred. {e}")
            ProxyProviderService.get_instance().check_again(used_proxy["https"].replace("https://", ""))
            attempts += 1

    return f"cannot connect to {url}{request.args}. {attempts} attempts were made.", 500


@scheduler.task('interval', id=JOBS["JOB_1"], seconds=400, misfire_grace_time=1)
def run_job_1():
    ProxyProviderService.get_instance().scrape_proxies_from_free_proxy_list()


@scheduler.task('interval', id=JOBS["JOB_2"], seconds=400, misfire_grace_time=1)
def run_job_2():
    ProxyProviderService.get_instance().scrape_proxies_from_proxy_scan()


@scheduler.task('interval', id=JOBS["JOB_3"], seconds=400, misfire_grace_time=1)
def run_job_3():
    ProxyProviderService.get_instance().scrape_proxies_from_github()


def set_global_exception_handler(app):
    @app.errorhandler(Exception)
    def unhandled_exception(e):
        response = dict()
        error_message = traceback.format_exc()
        app.logger.error("Caught Exception: {}".format(error_message))  # or whatever utils you use
        response["errorMessage"] = error_message
        return response, 500


def search_proxies():
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        executor.submit(run_job_1)
        executor.submit(run_job_2)
        executor.submit(run_job_3)


def run_server():
    # config app
    app.config.from_pyfile("server_config.cfg")

    # schedule jobs
    # schedule example: https://github.com/viniciuschiele/flask-apscheduler/blob/master/examples/decorated.py
    scheduler.init_app(app)
    scheduler.start()

    # start the flask server
    set_global_exception_handler(app)

    search_proxies()
    app.run(host='0.0.0.0', port=f"{app.config.get('PORT')}")


if __name__ == '__main__':
    run_server()
