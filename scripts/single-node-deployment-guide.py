# coding: utf-8
"""
单机部署模式指引
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
    st.markdown('下载项目代码后，进入项目目录。如果需要隔离运行环境，可以创建一个虚拟环境，然后激活环境后，再执行如下命令安装依赖：')
    st.markdown("```bash\n"
                "pip install -r requirements.txt\n"
                "```")
    st.markdown("#### 3. 启动LLM服务")
    st.markdown("##### 设置配置")
    base_model_path = st.text_input("基底模型路径:", key="base_model_path")
    embedding_path = st.text_input("Embedding模型路径:", key="embedding_path")
    reranker_path = st.text_input("Reranker模型路径:", key="reranker_path")
    state_path = st.text_input("状态文件路径(选填):", key="state_path")

    if st.button("保存") and base_model_path and embedding_path and reranker_path:
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
        st.markdown("```执行如下命令\n  bash\n"
                        "python3 service.py --service_name llm_service \n"
                        "```")





def main():
    # 初始化客户端

    tabs_title = ["普通部署", "Docker部署"]


    set_page_style()

    with st.sidebar:
        st.header("RWKV-RAG单节点部署指引")
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
