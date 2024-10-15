import os
import multiprocessing
import sys

import zmq

from configuration import config
from src.services import *
from src.services import public_service_workers

def start_proxy(frontend_url, backend_url):
    print(f'\033[91mstart proxy {frontend_url} {backend_url}\033[0m')
    context = zmq.Context()
    frontend = context.socket(zmq.ROUTER)
    frontend.bind(frontend_url)
    backend = context.socket(zmq.DEALER)
    backend.bind(backend_url)
    zmq.proxy(frontend, backend)


def start_process(service_cls: AbstractServiceWorker, backend_url: str,config: dict):
    service_instance = service_cls(backend_url,config)
    print(f"\033[93mStarting service worker {service_cls} with backend url {backend_url} at process {os.getpid()}\033[0m")
    service_instance.run()


def start_service(service_cls :AbstractServiceWorker, config: dict):
    name = service_cls.__name__
    backend_url = config["back_end"]["protocol"] + "://" + config["back_end"]["host"] + ":" + str(config["back_end"]["port"])
    frontend_url = config["front_end"]["protocol"] + "://" + config["front_end"]["host"] + ":" + str(config["front_end"]["port"])
    print(f"\033[91mStarting service {name} with backend url {backend_url} and frontend url {frontend_url}\033[0m")
    num_workers = config.get("num_workers",1) or 1
    spawn_method = config.get("spawn_method","fork")
    multiprocessing.set_start_method(spawn_method, force=True)
    print(f'\033[91mStarting {num_workers} workers\033[0m')
    for i in range(num_workers):
       multiprocessing.Process(target=start_process, args=(service_cls,backend_url,config)).start()
    print(f'\033[91mstart proxy {frontend_url} {backend_url}\033[0m')
    multiprocessing.Process(target=start_proxy, args=(frontend_url,backend_url)).start()
    print(f"\033[91mService {name} started\033[0m")


def main():
    services = config.config.keys()
    print(f"Starting services {services}")
    current_module = sys.modules[__name__]
    for service in services:
        if config.config[service]["enabled"]:
            config_service = config.config[service]
            print(f"Starting service {service}")
            service_module_name = config_service["service_module"]
            # 类字符串名称
            class_name = public_service_workers.get(service_module_name, None)
            service_cls = getattr(current_module, class_name, None)  # 判断服务“类” 有没有导入成功
            if service_cls:
                is_init_once = hasattr(service_cls, "init_once")
                if is_init_once:
                    print(f"Init once for {service_module_name}")
                    service_cls.init_once(config_service)

                start_service(service_cls, config_service)


if __name__ == "__main__":
    main()