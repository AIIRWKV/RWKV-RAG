# coding: utf-8
"""
部署模式指引
"""
import streamlit as st

import yaml


# 设置页面的全局CSS样式
def set_page_style():
    st.markdown(
        """
        <style>
        /* 调整侧边栏的样式 */
        .st-Sidebar {
            position: absolute; /* 绝对定位 */
            left: 0; /* 左侧对齐 */
            top: 0; /* 上侧对齐 */
            height: 100%; /* 占满整个视口高度 */
            padding: 20px; /* 内边距 */
            box-sizing: border-box; /* 边框计算在宽度内 */
        }
        /* 调整主内容区域的样式 */
        .st-App {
            margin-left: 250px; /* 为侧边栏留出空间 */
        }
        </style>
        """,
        unsafe_allow_html=True)

def singe_node_deployment_manager():
    """
    单点普通部署
    """
    st.markdown("#### 1. 准备工作")
    st.markdown('检查系统是否具备一下条件：\n - 已安装Python3.10\n  - 已安装Python环境管理工具\n - 已安装pip工具\n - 已安装NVIDIA驱动 \n - 已安装CUDA(12.1+) [参照](https://developer.nvidia.com/cuda-downloads) ')

    st.markdown("#### 2. 安装依赖")
    st.markdown('下载项目代码后，进入项目目录(**后续描述没特殊说明都是在该路径下执行命令**)。如果需要隔离运行环境，可以创建一个虚拟环境，然后激活环境后，再执行如下命令安装依赖：')
    st.markdown("```bash\n"
                "pip install -r requirements.txt\n"
                "```")
    st.markdown("#### 3. 启动LLM服务")
    st.markdown("##### 设置配置")
    st.warning('对应的配置文件 etc/llm_service_config.yml, 点击保存后会更新该配置文件的配置参数')
    base_model_path = st.text_input("基底模型路径(推荐使用[RWKV6 7BB模型](https://huggingface.co/BlinkDL/rwkv-6-world/blob/main/RWKV-x060-World-7B-v2.1-20240507-ctx4096.pth)):", key="base_model_path")
    embedding_path = st.text_input("Embedding模型路径(推荐使用[BGEM3 Embedding 模型](https://huggingface.co/BAAI/bge-m3)):", key="embedding_path")
    reranker_path = st.text_input("Reranker模型路径(推荐使用[BGEM3 重排序模型](https://huggingface.co/BAAI/bge-reranker-v2-m3)):", key="reranker_path")
    state_path = st.text_input("状态文件路径(选填):", key="state_path")

    if st.button("保存", key="save_llm_config") and base_model_path and embedding_path and reranker_path:
        with open('etc/llm_service_config.yml', 'r') as f:
            try:
                config = yaml.safe_load(f)
            except yaml.YAMLError as exc:
                raise ValueError(f"Invalid config file")
            config['base_model_path'] = base_model_path
            config['embedding_path'] = embedding_path
            config['reranker_path'] = reranker_path
            if state_path:
                config['state_path'] = state_path
        with open('etc/llm_service_config.yml', 'w') as f:
            yaml.dump(config, f)
        st.markdown("执行如下命令\n  ```bash\n"
                        "python3 service.py --service_name llm_service \n"
                        "```")

    st.markdown("#### 4. 启动Index服务")
    st.markdown("##### 设置配置")
    st.warning('对应的配置文件 etc/index_service_config.yml, 点击保存后会更新该配置文件的配置参数 \n 该服务会启动向量数据库chromaDB进程')
    chroma_path = st.text_input(
        "chromaDB数据存储目录(确保目录存在):",
        key="chroma_path")
    chroma_port = st.text_input("chromaDB对外提供服务端口(确保端口没有被其它进程占用):", key="chroma_port", value='9998')

    if st.button("保存", key="save_index_config") and chroma_path and chroma_port:
        with open('etc/index_service_config.yml', 'r') as f:
            try:
                config = yaml.safe_load(f)
            except yaml.YAMLError as exc:
                raise ValueError(f"Invalid config file")
            config['chroma_path'] = chroma_path
            config['chroma_port'] = chroma_port
        with open('etc/index_service_config.yml', 'w') as f:
            yaml.dump(config, f)
        st.markdown("执行如下命令\n  ```bash\n"
                    "python3 service.py --service_name index_service \n"
                    "```")

    st.markdown("#### 5. 启动Client服务")

    st.markdown("##### 启动代理服务")
    st.warning(
        '对应的配置文件 etc/ragq.yml, 点击保存后会更新该配置文件的配置参数 \n - RWKV-RAG是基于ZMQ消息队列的异步架构，支持单机部署，'
        '也支持集群部署。采用了ZMQ的代理模式，如果你对该部分技术不了解建议查看ZMQ相关文档。代理模式的前后端服务的监控端口建议使用默认值，'
        '如果你对这块技术很了解可执行修改配置文件。')
    with open('etc/ragq.yml', 'r') as f:
        try:
            client_config = yaml.safe_load(f)
        except yaml.YAMLError as exc:
            raise ValueError(f"Invalid config file")
    llm_config_front = client_config['llm']['front_end']
    llm_config_backend = client_config['llm']['back_end']
    st.markdown(f"###### LLM服务前后端代理监控服务详情：\n "
                f"- 前端: {llm_config_front['protocol']}://{llm_config_front['host']}:{llm_config_front['port']} \n "
                f"- 后端: {llm_config_backend['protocol']}://{llm_config_backend['host']}:{llm_config_backend['port']}")

    llm_config_front = client_config['index']['front_end']
    llm_config_backend = client_config['index']['back_end']
    st.markdown(f"###### Index服务前后端代理监控服务详情：\n "
                f"- 前端: {llm_config_front['protocol']}://{llm_config_front['host']}:{llm_config_front['port']} \n "
                f"- 后端: {llm_config_backend['protocol']}://{llm_config_backend['host']}:{llm_config_backend['port']}")

    st.markdown("执行如下命令\n  ```bash\n"
                "python3 proxy.py \n"
                "```")

    st.markdown("##### 启动Client服务")
    st.markdown("###### 设置配置")

    knowledge_base_path = st.text_input(
        "知识库文件存储目录(即上传或在线搜索知识文件存放位置，确保目录存在):",
        key="knowledge_base_path")
    sqlite_db_path = st.text_input("后端服务SqLite3数据库路径(确保路径存在，示例：/home/rwkv/RWKV-RAG-Data/files_services.db):", key="sqlite_db_path")

    if st.button("保存", key="save_ragq") and knowledge_base_path and sqlite_db_path:
        client_config['knowledge_base_path'] = knowledge_base_path
        client_config['sqlite_db_path'] = sqlite_db_path
        with open('etc/ragq.yml', 'w') as f:
            yaml.dump(config, f)
        st.markdown("执行如下命令\n  ```bash\n"
                    "streamlit run client.py \n"
                    "```")

    st.warning("###### Note：\n 如果了解了RWKV-RAG的系统架构设计原理，完成单机部署后，后续的Docker部署或者集群部署都能很容易理解。")


def main():
    # 初始化客户端

    tabs_title = ["单机部署", "Docker单机部署", "Docker集群部署"]


    set_page_style()

    with st.sidebar:
        st.header("RWKV-RAG部署指引")
        st.write('\n')
        # 创建垂直排列的标签页
        app_scenario = st.radio('', tabs_title)

        st.write('\n')
        st.markdown("""
        <hr style="border: 1px solid #CCCCCC; margin-top: 20px; margin-bottom: 20px;">
        """, unsafe_allow_html=True)
        st.write('\n')



    if app_scenario == tabs_title[0]:
       singe_node_deployment_manager()



if __name__ == "__main__":

    main()
