import importlib
import os
import multiprocessing
import sys
import argparse

#from src.services import *
from src.services import public_service_workers
from src.services import AbstractServiceWorker
from configuration import LLMServiceConfig, IndexServiceConfig



def start_process(service_cls: "AbstractServiceWorker", backend_url: str,config: dict):
    service_instance = service_cls(backend_url,config)
    print(f"\033[93mStarting service worker {service_cls} with backend url {backend_url} at process {os.getpid()}\033[0m")
    service_instance.run()


def start_service(service_cls :"AbstractServiceWorker", config:dict):
    name = service_cls.__name__
    back_end = config.get("back_end", {})
    protocol = back_end.get("protocol","tcp")
    host = back_end.get("host","0.0.0.0")
    port = back_end.get("port", '')
    backend_url = f"{protocol}://{host}:{port}"
    start_process(service_cls, backend_url, config)
    print(f"\033[91mService {name} started\033[0m")


def main(service_name:str = None):
    services = public_service_workers.keys()
    if service_name:
        if service_name not in services:
            print(f"Service {service_name} not found, service_name must be one of {services}")
            return
        services = [service_name]

    print(f"Starting services {services}")
    for service_module_name in services:
        if service_module_name == 'llm_service':
            config_service = LLMServiceConfig(f'etc/{service_module_name}_config.yml').config
        elif service_module_name == 'index_service':
            config_service = IndexServiceConfig(f'etc/{service_module_name}_config.yml').config
        # elif service == 'tuning_service':
        #     config_service = TuningServiceConfig(f'etc/{service}_config.yml').config
        else:
            continue
        print(f"Starting service {service_module_name}")
        # 类字符串名称
        class_name = public_service_workers.get(service_module_name, None)
        module = importlib.import_module(f'src.services.{service_module_name}')  # 判断服务“类” 有没有导入成功
        service_cls = getattr(module, class_name)
        if service_cls:
            start_service(service_cls, config_service)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='RWKV-RAG-Service')
    parser.add_argument('--service_name', nargs='?', help='Service name',default=None)
    args = parser.parse_args()
    service_name = args.service_name
    if not service_name:
        service_name = os.environ.get('RWKV-RAG-SERVICE-NAME', None)
    main(service_name)