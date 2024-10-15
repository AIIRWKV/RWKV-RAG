import os

if __name__ == '__main__':
    service_type = os.getenv('SERVICE_TYPE', 'service')
    if service_type == 'service':
        from service import main as service_main
        service_main()
    else:
        from client import main as client_main
        client_main()
        