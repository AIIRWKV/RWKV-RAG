# coding: utf-8
"""
启动代理
我们是采用消息队列来让每个子系统进行通信
如果不理解，建议查看zmq代理模式原理
"""
import multiprocessing
import zmq

from configuration import ClientCofig

def start_proxy(frontend_url, backend_url):
    print(f'\033[91mstart proxy {frontend_url} {backend_url}\033[0m')
    context = zmq.Context()
    frontend = context.socket(zmq.ROUTER)
    frontend.bind(frontend_url)
    backend = context.socket(zmq.DEALER)
    backend.bind(backend_url)
    zmq.proxy(frontend, backend)


def start_service_proxy():
    project_config = ClientCofig('etc/ragq.yml')
    config = project_config.config
    for service_name, service_config in config.items():
        if 'front_end' in service_config and 'back_end' in service_config:
            backend_url = service_config["back_end"]["protocol"] + "://" + service_config["back_end"]["host"] + ":" + str(
                service_config["back_end"]["port"])
            frontend_url = service_config["front_end"]["protocol"] + "://" + service_config["front_end"]["host"] + ":" + str(
                service_config["front_end"]["port"])
            print(
                f"\033[91mStarting service {service_name}_service with backend url {backend_url} and frontend url {frontend_url}\033[0m")
            multiprocessing.Process(target=start_proxy, args=(frontend_url, backend_url)).start()
            print(f"\033[91mService {service_name}_service started\033[0m")


if __name__ == '__main__':
    start_service_proxy()