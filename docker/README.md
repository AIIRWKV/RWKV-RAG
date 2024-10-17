# RWKV-RAG Docker部署

本教程不包含docker和NVIDIA驱动程序安装教程，如果没有安装请提前安装，具体安装方法请参照官方文档

> [!WARNING]  
> 
> 目前只支持在单个宿主机上部署，不支持集群部署。后续会支持集群部署，LLM Service（**大模型生成服务**） 、Index Service（**数据索引及检索服务**）和 Tuning Service（**一键微调服务**）每一个服务都可以docker单独部署。

## 1. NVIDIA Container Toolkit
如果你还没有安装 NVIDIA Container Toolkit，你可以按照以下步骤进行安装：
```shell
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update
sudo apt-get install -y nvidia-docker2
```
安装完成后，重启docker
```shell
sudo systemctl restart docker
```


## 2. Chromadb Docker 部署
```shell
sudo docker pull chromadb/chroma
sudo docker run -d --rm --name chromadb_service -p 9999:8000 -v /home/rwkv/Data/chroma:/chroma/chroma -e IS_PERSISTENT=TRUE -e ANONYMIZED_TELEMETRY=TRUE chromadb/chroma:latest
```
> [!TIP]  
> - chromadb/chroma镜像使用的是8000端口，而ragq.yml配置的chroma_port是9999(可自行修改)，所以需要将chromadb的端口映射到9999,这样可以通过宿主机的9999端口访问chromadb服务。如果能正常访问，说明部署成功。
> - -v /home/rwkv/Data/chroma:/chroma/chroma 是将宿主机的/home/rwkv/Data/chroma目录挂载到chromadb的/chroma/chroma目录下，当容器删除时，数据不会丢失。这个需要根据你的实际情况自行修改(**此文档中涉及到的宿主机目录可根据自己服务器情况自行修改，下同**)。


## 3. RWKV-RAG Service Docker 部署
#### 构建镜像
下载项目代码docker目录，cd到该目录下，构建镜像
```shell
sudo docker build -f DockerfileService -t rwkv_rag_service:latest .
```
#### 下载模型文件
参照项目文档**模型下载**部分，将下载好的模型统一放在宿主机的/home/rwkv/models目录下，我们通过挂载的模式将模型文件挂载到容器中

#### 启动容器

```shell
sudo docker run -it --gpus all --name rwkv_rag_service -p 7781:7781 -p 7782:7782 -p 7783:7783 -p 7784:7784 -p 7788:7788 -p 7787:7787  -v /home/rwkv/models:/root/model -v /home/rwkv/Data:/root/data -v /home/rwkv/docker/ragq_service.yml:/root/RWKV-RAG/ragq.yml  rwkv_rag_service:latest
```

运行容器参数含义：
###### --gpus all
允许容器访问所有可用的GPU
###### -v /home/rwkv/docker/ragq_service.yml:/root/RWKV-RAG/ragq.yml
将宿主机的/home/rwkv/docker/ragq_service.yml文件挂载到容器的/root/RWKV-RAG/ragq.yml文件下，用于覆盖容器里项目的配置文件ragq.yml，便于管理配置文件。 <br>
配置文件模板参照项目docker/ragq_service.yml。需要说明的是host**必须**是**0.0.0.0**,不能是127.0.0.1、localhost或者宿主机的IP地址，否则RWKV-RAG Client Docker服务有可能访问不了RWKV-RAG Service Docker服务
###### -v /home/rwkv/models:/root/model
将宿主机的/home/rwkv/models目录挂载到容器的/root/model目录下
###### -v /home/rwkv/Data:/root/data
将宿主机的/home/rwkv/Data目录挂载到容器的/root/data目录下，容器中产生的文件会保存到该目录下,包括RWKV-RAG Client Docker服务也是存储到宿主机的/home/rwkv/Data目录下
###### -p 7781:7781等
ragq_service.yml配置的端口都需要对外暴露，否则无法访问

> [!WARNING]  
> 
> - 镜像构建完后占用空间21GB左右，请预留足够的存储空间
> 


## 4. RWKV-RAG Client Docker 部署
#### 构建镜像
```shell
sudo docker build -f DockerfileClient -t rwkv_rag_client:latest .
```

#### 启动容器
```shell
sudo docker run -it  --name rwkv_rag_client -p 8501:8501  -v /home/rwkv/Data:/root/data -v /home/rwkv/models:/root/model -v /home/rwkv/Data/ragq_client.yml:/root/RWKV-RAG/ragq.yml   rwkv_rag_client:latest
```

运行容器参数含义：
###### -v /home/rwkv/docker/ragq_client.yml:/root/RWKV-RAG/ragq.yml
将宿主机的/home/rwkv/docker/ragq_client.yml文件挂载到容器的/root/RWKV-RAG/ragq.yml文件下，用于覆盖容器里项目的配置文件ragq.yml，便于管理配置文件。 <br>
配置文件模板参照项目docker/ragq_cliente.yml。需要说明的是host必须是宿主机的IP地址，否则RWKV-RAG Client Docker服务有可能访问不了RWKV-RAG Service Docker服务
###### -v /home/rwkv/models:/root/model
将宿主机的/home/rwkv/models目录挂载到容器的/root/model目录下,该服务涉及到模型管理慕课，也会检测模型文件，所有需要将宿主机模型存储路径挂载到容器中
###### -v /home/rwkv/Data:/root/data
将宿主机的/home/rwkv/Data目录挂载到容器的/root/data目录下，可能需要读取RWKV-RAG Service Docker服务产生的数据
###### -v /home/rwkv/Data/knowledge_data:/root/knowledge_data
将宿主机的/home/rwkv/Data/knowledge_data目录挂载到容器的/root/knowledge_data目录下，该服务涉及到知识库管理，需要将知识库文件挂载到容器中
###### -p 8501:8501
提供对外访问端口