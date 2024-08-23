import os
import asyncio
import re

import streamlit as st
import pandas as pd

from src.clients.index_client import IndexClient
from src.clients.llm_client import LLMClient
from src.utils.loader import Loader
from src.utils.internet import search_on_baike
from src.utils.make_data import get_random_string
from src.clients.tuning_client import TuningClient
from src.services import FileStatusManager
from configuration import config as project_config


current_path = os.path.dirname(os.path.abspath(__file__)) # 工程当前目录
parent_dir = os.path.dirname(current_path)  # 上一级
default_knowledge_base_dir = os.path.join(parent_dir, "knowledge_data") # 默认联网知识的存储位置
if not os.path.exists(default_knowledge_base_dir):
    os.makedirs(default_knowledge_base_dir)

default_upload_knowledge_base_dir = os.path.join(default_knowledge_base_dir, "upload_knowledge")
if not os.path.exists(default_upload_knowledge_base_dir):
    os.makedirs(default_upload_knowledge_base_dir)

default_tuning_path = os.path.join(default_knowledge_base_dir, "tuning_data") # 微调数据存储位置
if not os.path.exists(default_tuning_path):
    os.makedirs(default_tuning_path)

default_tuning_model_path = os.path.join(default_knowledge_base_dir, "tuning_model")
if not os.path.exists(default_tuning_model_path):
    os.makedirs(default_tuning_model_path)






async def search_and_notify(search_query, output_dir, output_filename):
    # Run the async search function
    msg = await search_on_baike(search_query, output_dir, output_filename)
    return os.path.join(output_dir, output_filename), msg

    # Run the async function in the event loop
    return asyncio.run(async_search())


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


def knowledgebase_manager(index_client: IndexClient, file_client: FileStatusManager):
    st.title("知识库管理")
    # 显示所有知识库
    collections = index_client.show_collection()
    if collections:
        st.subheader("知识库列表")
        collection_name_list = [i[0] for i in collections.get('value', [])]
        collection_name_meta_data = [i[1] for i in collections.get('value', [])]
        df = pd.DataFrame({'name': collection_name_list, 'meta_data': collection_name_meta_data})
        st.dataframe(df, use_container_width=True)
    else:
        collection_name_list = []
        st.warning("没有找到任何知识库。")

    st.subheader("新增知识库")
    new_collection_name = st.text_input("请输入新知识库的名称:")
    if st.button('添加'):
        if new_collection_name:
            collection_name_rule = r'^[a-zA-Z0-9][a-zA-Z0-9_]{1,31}[a-zA-Z0-9]$'
            if not re.match(collection_name_rule, new_collection_name):
                st.warning('知识库名称不合法,长度3-32的英文字符串')
            else:
                if new_collection_name in collection_name_list:
                    st.warning(f"知识库 '{new_collection_name}' 已经存在。")
                else:
                    try:
                        index_client.create_collection(new_collection_name)
                        st.success(f"知识库 '{new_collection_name}' 已成功添加。")
                        collection_name_list.append(new_collection_name)
                    except Exception as e:
                        st.error(f"添加知识库时出错: {str(e)}")
        else:
            st.warning("请输入有效的知识库名称。")

    st.subheader("删除知识库")
    collection_to_delete = st.selectbox("选择要删除的知识库:", [''] + collection_name_list)
    if st.button('删除'):
        if collection_to_delete:
            try:
                index_client.delete_collection(collection_to_delete)
                st.success(f"知识库 '{collection_to_delete}' 已成功删除。")
                if collection_name_list:
                    collection_name_list.remove(collection_to_delete)
            except Exception as e:
                st.error(f"删除知识库时出错: {str(e)}")
        else:
            st.warning("请选择一个知识库进行删除。")

    st.subheader("知识库详情")
    collection_to_detail = st.selectbox("选择知识库:",collection_name_list)
    if st.button('查看') and collection_to_detail:
        file_list = file_client.get_collection_files(collection_to_detail)
        if file_list:
            st.write("文件列表:")
            df = pd.DataFrame({'文件': file_list, })
            st.dataframe(df, use_container_width=True)
        else:
            st.warning("该知识库下没有找到任何文件。")


def internet_search(index_client: IndexClient, file_client: FileStatusManager):
    """
    知识入库
    """
    if 'internet_search_random_str' not in st.session_state or  not st.session_state.internet_search_random_str:
        random_str = get_random_string(6)
        st.session_state.internet_search_random_str = random_str

    st.title("知识入库")
    st.subheader("联网搜索")
    st.markdown('<span style="font-size: 16px; color: blue;">❗ 通过关键词联网搜索知识！</span>', unsafe_allow_html=True)
    # 搜索查询输入
    search_query = st.text_input("请输入搜索关键词:", "", key="query_main")

    # 输出目录输入
    output_dir = st.text_input("请输入输出目录(:red[可更改]):", default_knowledge_base_dir, key="output_dir_main")

    # 输出文件名输入
    output_filename = st.text_input("请输入输出文件名(:red[可更改]):",
                                    "result_%s.txt" % st.session_state.internet_search_random_str,
                                    key="output_filename_main")

    # 按钮触发搜索并保存
    if st.button("搜索并保存"):
        if not search_query:
            st.error("请提供搜索关键词。")
        elif not output_dir:
            st.error("请提供输出目录。")
        else:
            try:
                if not output_filename:
                    output_filename = f'{search_query}.txt'
                filepath, msg = asyncio.run(search_and_notify(search_query, output_dir, output_filename))
                st.session_state.internet_search_random_str = output_filename
                if not msg:
                    st.success(f"搜索结果已保存到: {filepath}")
                else:
                    st.warning(msg)
            except Exception as e:
                st.error(f"发生错误: {str(e)}")

    st.subheader("知识入库")
    st.markdown('<span style="font-size: 16px; color: blue;">❗可将上面的联网搜索的结果、手动输入文本、本地文件入库,入库前请确认左边正在使用的知识库是否正确 </span>', unsafe_allow_html=True)
    # 询问用户输入payload的方式
    input_method = st.selectbox(
        "请选择知识入库方式",
        ["服务端文件", "本地上传", "手动输入"],
        index=0
    )

    if input_method == "手动输入":
        payload_input = st.text_area("请输入要入库的内容（每条文本一行），然后Ctrl+Enter", height=300)
        load_button = st.button("分割文件")
        if payload_input and load_button:
            payload_texts = payload_input.split("\n")
            for idx, chunk in enumerate(payload_texts):
                result = index_client.index_texts([chunk], collection_name=st.session_state.kb_name)
                st.write(f"文本 {idx + 1}: {result}")
    elif input_method == "服务端文件":
        st.markdown(
            '<span style="font-size: 12px; color: blue;">❗服务端文件指该知识库文件在项目部署的服务器上,如果你知道这个文件在项目部署的服务器上位置,'
            '填写到输入知识库路径输入框 </span>',
            unsafe_allow_html=True)

        input_path = st.text_input("请输入知识库路径:", key="input_path_key")
        chunk_size = st.number_input("请输入块大小（字符数）:", min_value=1, value=512, key="chunk_size_key")
        chunk_overlap = st.number_input("请输入块重叠（字符数）:", min_value=0, value=0, key="chunk_overlap_key")
        output_path = st.text_input("请输入输出目录路径(:red[可更改]):",default_knowledge_base_dir, key="output_path_key")

        # 加载按钮
        load_button = st.button("加载并分割文件")
        if load_button and input_path and output_path:
            if not os.path.exists(input_path):
                st.warning(f"知识库{input_path}不存在")
            if not os.path.exists(output_path):
                st.warning(f"{output_path}不存在")
            elif not os.path.isdir(output_path):
                st.warning(f"{output_path}不是目录")

            try:
                loader = Loader(input_path, chunk_size, chunk_overlap)
            except Exception as e:
                loader = None
                st.warning("文件加载和分割过程中出现错误:" + str(e))
            is_success = False
            if loader:
                chunks= loader.load_and_split_file(output_path)

                for idx,chunk in enumerate(chunks):
                    index_client.index_texts([chunk], collection_name=st.session_state.kb_name)
                st.success(f"文件已加载并分割完成！分割后文件路径:{loader.output_files}")
                is_success = True

            # 记录文件入库状态
            if is_success:
                for path in loader.output_files:
                    if not file_client.check_file_exists(path, st.session_state.kb_name):
                        file_client.add_file(path, st.session_state.kb_name)

        elif load_button:
            st.warning("参数不能为空。")
    elif input_method == '本地上传':
        st.markdown(
            '<span style="font-size: 12px; color: blue;">❗本地上传是指将电脑上的txt,pdf等格式的知识文件上传到服务器后，然后进行入库</span>',
            unsafe_allow_html=True)
        payload_file = st.file_uploader("请上传文件", type=["txt", "pdf"], key="payload_input")
        if 'now_upload_file' not in st.session_state:
            st.session_state.now_upload_file = ''
        if payload_file and not st.session_state.now_upload_file:
            file_name = payload_file.name
            file_name_prefix, file_ext = file_name.rsplit('.', 1)
            output_name_prefix = '%s_%s.%s' % (file_name_prefix, get_random_string(4), file_ext)
            output_path = os.path.join(default_upload_knowledge_base_dir, output_name_prefix) # 文件在服务器的位置
            with open(output_path, 'wb') as f:
                f.write(payload_file.read())
                st.success("文件已上传并保存到: %s" % output_path)
                st.session_state.now_upload_file = output_path
        if payload_file and st.session_state.now_upload_file:
            chunk_size = st.number_input("请输入块大小（字符数）:", min_value=1, value=512, key="chunk_size_key")
            chunk_overlap = st.number_input("请输入块重叠（字符数）:", min_value=1, value=8, key="chunk_overlap_key")
            load_button = st.button("加载并分割文件")
            input_path = st.session_state.now_upload_file
            if load_button:
                try:
                    loader = Loader(input_path, chunk_size, chunk_overlap)
                except Exception as e:
                    loader = None
                    st.warning("文件加载和分割过程中出现错误:" + str(e))
                is_success = False
                if loader:
                    chunks = loader.load_and_split_file(default_upload_knowledge_base_dir)

                    for idx,chunk in enumerate(chunks):
                        index_client.index_texts([chunk], collection_name=st.session_state.kb_name)
                    st.success(f"文件已加载并分割完成！分割后文件路径:{loader.output_files}")
                    is_success = True
                # 记录文件入库状态
                if is_success:
                    for path in loader.output_files:
                        if not file_client.check_file_exists(path, st.session_state.kb_name):
                            file_client.add_file(path, st.session_state.kb_name)



def rag_chain(index_client: IndexClient, llm_client: LLMClient):
    # 用户输入query
    st.subheader('召回最匹配知识')
    query_input_key = "query_input_key"
    query_input = st.text_input("请输入查询", key=query_input_key)
    recall_button = st.button("召回")

    if recall_button and query_input:
        search_results = index_client.search_nearby(query_input, collection_name=st.session_state.kb_name)['value']
        documents = search_results["documents"][0]
        st.write(documents)
        cross_scores = llm_client.cross_encode([query_input for i in range(len(documents))], documents)
        st.header("Cross_score")
        st.write(cross_scores)
        max_score_index = cross_scores["value"].index(max(cross_scores["value"]))
        best_match = documents[max_score_index]
        st.header("最佳匹配")
        st.write(f"Best Match: {best_match}")
        st.session_state.best_match = best_match

    st.subheader('RWKV-RAG-CHAT')

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    instruction_input = st.chat_input("请问您有什么问题？:", key="instruction_input")
    if 'best_match' in st.session_state and instruction_input:
        with st.chat_message("user"):
            st.markdown(instruction_input)
        st.session_state.chat_messages.append({"role": "User", "content": instruction_input})
        sampling_results = llm_client.sampling_generate(instruction_input, st.session_state.best_match,
                                                        '',
                                                        token_count=50).get('value')


        st.session_state.chat_messages.append({"role": "RWKV", "content": sampling_results})
        with st.chat_message("RWKV"):
            st.write(sampling_results)
        st.session_state.best_match = f"{st.session_state.best_match},{sampling_results}"


def jsonl2binidx_manager(client: TuningClient):
    """
    数据转换
    """

    st.subheader("准备微调数据")
    epoch = st.number_input("Epoch:", min_value=1, value=3, key='tuning_epoch', max_value=10)
    context_len = st.number_input("Context Length:", min_value=1, value=1024, key='tuning_context_len', )
    # 输出路径
    output_dir = st.text_input("输出文件路径:", default_tuning_path, key="output_dir")
    # 询问用户输入payload的方式
    input_method = st.selectbox(
        "请选择输入数据格式",
        ["本地上传", "手动输入"],
        index=0
    )
    payload_input = None
    if input_method == "手动输入":
        payload_input = st.text_area(
            "请输入payload内容（每条文本一行，格式参照https://rwkv.cn/RWKV-Fine-Tuning/FT-Dateset)", height=220)
    else:
        payload_file = st.file_uploader("请上传文件(:red[格式参照]https://rwkv.cn/RWKV-Fine-Tuning/FT-Dateset)",
                                        type=["jsonl"], key="payload_input",
                                        )
        if payload_file:
            payload_input = payload_file.read().decode("utf-8", errors='ignore')
    if st.button("提交") and payload_input:
        binidx_path = client.jsonl2binidx(payload_input, epoch, output_dir, context_len, is_str=True)
        st.write(binidx_path)
        st.markdown('<span style="font-size: 12px; color: blue;">❗ 返回的路径值可作为模型微调训练数据集的路径</span>', unsafe_allow_html=True)

def wandb_manager(client: TuningClient):
    """
    wandb 管理
    """
    st.subheader('wandb管理')
    username_dict = client.wandb_info()
    username = username_dict.get('value', '')
    username = username or '暂未登录'
    st.markdown('<span style="font-size: 19x; font-weight: bold;">当前用户</span>', unsafe_allow_html=True)
    st.markdown(f"{username}" , unsafe_allow_html=True)

    st.markdown('<span style="font-size: 19x; font-weight: bold;">登录</span>', unsafe_allow_html=True)
    st.markdown(f"输入api key,点击登录即可完成账号登录", unsafe_allow_html=True)
    api_key = st.text_input("请输入wandb api key:", key="api_key")
    if st.button("登录") and api_key:
        resp = client.wandb_login(api_key)
        if str(resp.get('code')) == '200':
            st.success(resp.get('value', ''))
        else:
            st.warning(resp.get('value', ''))
    st.markdown('<span style="font-size: 19x; font-weight: bold;">添加项目</span>', unsafe_allow_html=True)
    project_name = st.text_input("请输入wandb项目名:", key="project_name")
    if st.button("添加") and project_name:
        resp = client.wandb_add_project(project_name)
        if str(resp.get('code')) == '200':
            st.success(resp.get('value', ''))
        else:
            st.warning(resp.get('value', ''))

def tuning_manager(client: TuningClient, app_scenario):
    """
    模型微调
    """
    st.subheader("模型微调")
    st.markdown(
        '<span style="font-size: 16px; color: blue;">❗不同的底座RWKV模型参数不同,具体参照<a href="https://rwkv.cn/RWKV-Fine-Tuning/Full-ft-Simple#%E8%B0%83%E6%95%B4-n_layer-%E5%92%8C-n_embd-%E5%8F%82%E6%95%B0">RWKV微调参数调整 </a></span>',
        unsafe_allow_html=True)

    tuning_type = st.selectbox("微调算法:", ["state"], index=0)
    proj_dir = st.text_input("训练日志和训练得到的文件输出路径:", default_tuning_model_path, key="proj_dir")
    data_file = st.text_input("训练数据集的路径:(:red[路径中不需要带 bin 和 idx 后缀，仅需文件名称])", "", key="data_file")
    load_model = st.session_state.base_model_path
    wandb_project = client.wandb_list_project().get('value', []) or []
    my_wandb = st.selectbox("wandb:", [''] + wandb_project, index=0)

    epoch_count = st.number_input("总训练轮次:", min_value=1, value=3, key="epoch_count")
    epoch_steps = st.number_input("每个训练轮次的步数:", min_value=1, value=800,
                                  key="epoch_steps")
    accelerator = st.selectbox("加速器类型:", ["gpu"], key="accelerator")
    precision = st.selectbox("训练精度:", ["fp32", "tf32", "fp16", "bf16"], key="precision", index=3)
    quant = st.selectbox("量化参数:", ['nf4'], key="quant")
    n_layer = st.number_input("n_layer:", min_value=1, value=24, key="n_layer")
    n_embd = st.number_input("n_embd:", min_value=1, value=2048, key="n_embd")
    ctx_len = st.number_input("上下文长度:", min_value=1, value=1024, key="ctx_len")
    data_type = st.selectbox("训练语料的文件格式:", ['binidx'], key="data_type")
    epoch_save = st.number_input("保存一次模型所间隔的训练轮次:", min_value=1, value=1, key="epoch_save")
    vocab_size = st.number_input("词表大小:", min_value=1, value=65536, key="vocab_size")
    epoch_begin = st.number_input("初始训练轮次:", min_value=0, value=0, key="epoch_begin")
    pre_ffn = 0
    head_qk = 0
    beta1 = st.number_input("Adam优化器的beta1参数:", min_value=0.0, value=0.9, key="beta1")
    beta2 = st.number_input("Adam优化器的beta2参数:", min_value=0.0, value=0.99, key="beta2")
    adam_eps = st.number_input("Adam优化器的epsilon 参数:", min_value=0.0, value=1e-8, key="adam_eps", step=1e-8, format="%f")
    my_testing = st.selectbox("训练的RWKV模型版本:", ["x060"], key="my_testing", index=0)
    strategy = st.selectbox("lightning训练策略参数:", ["deepspeed_stage_1"], key="strategy")
    devices = st.number_input("训练时显卡数量:", min_value=1, value=1, key="devices")
    dataload = "pad"
    grad_cp = st.selectbox("梯度累积步数:", [0, 1], key="grad_cp", index=1)

    if tuning_type == 'state':
        micro_bsz = st.number_input("micro_bsz:", min_value=1, value=1, key="micro_bsz")
        lr_init = st.number_input("初始学习率:", min_value=0.0, value=1.0, key="lr_init")
        lr_final = st.number_input("最终学习率:", min_value=0.0, value=1e-2, key="lr_final")
        warmup_steps = st.number_input("预热步骤数:", min_value=0, value=10, key="warmup_steps")
    elif tuning_type == 'pissa':
        svd_niter = 4
        lora_r = st.number_input("LoRA微调rank参数:", min_value=1, value=64, key="lora_r")
        micro_bsz = st.number_input("micro_bsz:", min_value=1, value=8, key="micro_bsz")
        lr_init = st.number_input("初始学习率:", min_value=0.0, value=5e-5, key="lr_init", step=1e-5, format="%f")
        lr_final = st.number_input("最终学习率:", min_value=0.0, value=5e-5, key="lr_final", step=1e-5, format="%f")
        lora_load = st.text_input("LoRA文件路径:", "rwkv-0", key="lora_load")
        lora_alpha = st.number_input("Lora_alpha参数:", min_value=1, value=128, key="lora_alpha")
        lora_dropout = st.number_input("LoRA微调的丢弃率:", min_value=0.0, value=0.01, key="lora_dropout")
        lora_parts = st.text_input("LoRA微调影响的范围:", "att,ffn,time,ln", key="lora_parts")
    else:
        lora_r = st.number_input("LoRA微调rank参数:", min_value=1, value=64, key="lora_r")
        micro_bsz = st.number_input("micro_bsz:", min_value=1, value=8, key="micro_bsz")
        lr_init = st.number_input("初始学习率:", min_value=0.0, value=5e-5, key="lr_init")
        lr_final = st.number_input("最终学习率:", min_value=0.0, value=5e-5, key="lr_final", step=1e-5, format="%f")
        lora_alpha = st.number_input("Lora_alpha参数:", min_value=1, value=128, key="lora_alpha")
        warmup_steps = st.number_input("预热步骤数:", min_value=0, value=0, key="warmup_steps")
        lora_load = st.text_input("LoRA文件路径:", "rwkv-0", key="lora_load", disabled=True)
        lora_dropout = st.number_input("LoRA微调的丢弃率:", min_value=0.0, value=0.01, key="lora_dropout")
        lora_parts = st.text_input("LoRA微调影响的范围:", "att,ffn,time,ln", key="lora_parts")

    if st.button("开始"):
        if not proj_dir or not data_file:
            st.warning("输出路径和训练数据集的路径不能为空")
            return
        if tuning_type == 'state':
            client.state_tuning_train(
                load_model=load_model, proj_dir=proj_dir, data_file=data_file, data_type=data_type,
                vocab_size=vocab_size, ctx_len=ctx_len, epoch_steps=epoch_steps,
                epoch_count=epoch_count, epoch_begin=epoch_begin, epoch_save=epoch_save,
                micro_bsz=micro_bsz, n_layer=n_layer, n_embd=n_embd, pre_ffn=pre_ffn,
                head_qk=head_qk, lr_init=lr_init, lr_final=lr_final, warmup_steps=warmup_steps,
                beta1=beta1, beta2=beta2, adam_eps=adam_eps,
                accelerator=accelerator, devices=devices, precision=precision, strategy=strategy,
                grad_cp=grad_cp, my_testing=my_testing,
                train_type='state', dataload=dataload, quant=quant, wandb=my_wandb)
        elif tuning_type == 'pissa':
            client.pissa_train(load_model=load_model, proj_dir=proj_dir, data_file=data_file,
                               data_type=data_type,
                               vocab_size=vocab_size, ctx_len=ctx_len, epoch_steps=epoch_steps,
                               epoch_count=epoch_count, epoch_begin=epoch_begin, epoch_save=epoch_save,
                               micro_bsz=micro_bsz, n_layer=n_layer, n_embd=n_embd, pre_ffn=pre_ffn,
                               head_qk=head_qk, lr_init=lr_init, lr_final=lr_final, warmup_steps=warmup_steps,
                               beta1=beta1, beta2=beta2, adam_eps=adam_eps, accelerator=accelerator,
                               devices=devices, precision=precision, strategy=strategy, my_testing=my_testing,
                               lora_load=lora_load, lora=True, lora_r=lora_r, lora_alpha=lora_alpha,
                               lora_dropout=lora_dropout, lora_parts=lora_parts, PISSA=True, svd_niter=svd_niter,
                               grad_cp=grad_cp, dataload=dataload, quant=quant, wandb=my_wandb)
        else:
            client.lora_train(load_model=load_model, proj_dir=proj_dir, data_file=data_file, data_type=data_type,
                              vocab_size=vocab_size, ctx_len=ctx_len, epoch_steps=epoch_steps,
                              epoch_count=epoch_count, epoch_begin=epoch_begin, epoch_save=epoch_save,
                              micro_bsz=micro_bsz, n_layer=n_layer, n_embd=n_embd, pre_ffn=pre_ffn,
                              head_qk=head_qk, lr_init=lr_init, lr_final=lr_final, warmup_steps=warmup_steps,
                              beta1=beta1, beta2=beta2, adam_eps=adam_eps, accelerator=accelerator, devices=devices,
                              precision=precision, strategy=strategy, grad_cp=grad_cp, my_testing=my_testing,
                              lora_load=lora_load, lora=True, lora_r=lora_r, lora_alpha=lora_alpha,
                              lora_dropout=lora_dropout, lora_parts=lora_parts, wandb=my_wandb)


def base_model_manager(file_client: FileStatusManager):
    st.title("模型管理")
    st.subheader("基底模型列表")
    base_model_list  = file_client.get_base_model_list()
    if base_model_list:
        names = []
        paths = []
        statuss = []
        create_times = []
        for line in base_model_list:
            names.append(line[0])
            paths.append(line[1])
            statuss.append('上线' if line[2] == 1 else '下线')
            create_times.append(line[3])
        df = pd.DataFrame({'名称': names, '路径': paths, '状态': statuss, '创建时间': create_times})
        st.dataframe(df, use_container_width=True)
    else:
        names = ['default']
        st.warning("没有找到基底模型。请先添加基底模型")

    st.subheader("新增基底模型")
    new_base_model_name = st.text_input("请输入基底模型的名称(唯一):", key='new_base_model_name')
    new_base_model_path = st.text_input("请输入基底模型的路径:", key='new_base_model_path')

    if st.button('添加'):
        if new_base_model_name:
           if not 3 <= len(new_base_model_name) <= 64:
               st.warning("基底模型的名称长度必须在3到64个字符之间。")
        else:
            st.warning("请输入基底模型名称。")
        if new_base_model_path:
            if not os.path.exists(new_base_model_path):
                st.warning("基底模型的路径不存在。")
        else:
            st.warning("请输入基底模型路径。")

        code= file_client.add_base_model(new_base_model_name, new_base_model_path)
        if code == 0:
            st.warning(f"基底模型{new_base_model_name}已存在")
        else:
            st.success("基底模型添加成功。")
    st.subheader('修改基底模型')
    change_base_model_name = st.selectbox("请选择基底模型:", [''] + names, key='change_base_model_name')
    change_base_model_path = st.text_input("请输入基底模型的路径:", key='change_base_model_path')
    if st.button('修改') and change_base_model_name and change_base_model_path:
        file_client.change_base_model(change_base_model_name, change_base_model_path)
        st.success("基底模型修改成功。")

    st.subheader("激活基底模型")
    st.markdown(
        '<span style="font-size: 16px; color: blue;">状态是上线的基底模型才能使用</span>',
        unsafe_allow_html=True)
    active_base_model_name = st.selectbox("请选择基底模型:", [''] + names, key='active_base_model_name')
    if st.button('激活') and active_base_model_name:
        file_client.active_base_model(active_base_model_name)
        st.success("基底模型激活成功。")

    st.subheader("下线基底模型")
    offline_base_model_name = st.selectbox("请选择基底模型:", [''] + names, key='offline_base_model_name')
    if offline_base_model_name == 'default':
        st.warning("default 模型不能下线，可以通过修改default模型的路径来实现你的需求。")
    if st.button('下线') and offline_base_model_name:
        file_client.offline_base_model(offline_base_model_name)
        st.success("基底模型下线成功。")


def main():
    # 初始化客户端

    tabs_title = ["模型管理", "知识库管理", "知识入库", "模型微调", "知识问答"]
    tabs_title_enabled = [project_config.config.get('index', {}).get('enabled'),
                          project_config.config.get('index', {}).get('enabled'),
                          project_config.config.get('tuning', {}).get('enabled'),
                          project_config.config.get('llm', {}).get('enabled')]

    index_client = IndexClient("tcp://localhost:7783")
    file_status_manager = FileStatusManager(project_config.config.get('index', {}).get('sqlite_db_path'))


    set_page_style()

    with st.sidebar:
        st.header("RWKV RAGQ")
        st.write('\n')
        # 创建垂直排列的标签页
        app_scenario = st.radio('', tabs_title)

        st.write('\n')
        st.markdown("""
        <hr style="border: 1px solid #CCCCCC; margin-top: 20px; margin-bottom: 20px;">
        """, unsafe_allow_html=True)
        st.write('\n')

        # 当前知识库
        collections = index_client.show_collection()
        if collections:
            collection_name_list = [i[0] for i in collections.get('value', [])]
        else:
            collection_name_list = []
        base_model_list = file_status_manager.get_base_model_list(just_name=True)
        # if st.session_state.get('kb_name'):
        #     print('ttddddddd')
        #     for i, j in enumerate(collection_name_list):
        #         if j == st.session_state.kb_name:
        #            _index = i
        # else:
        #     _index = 0
       # print(st.session_state)
        st.session_state.kb_name = st.selectbox("正在使用的知识库", collection_name_list, )
        st.session_state.base_model_path = st.selectbox('基底RWKV模型', base_model_list)
        st.session_state.state_file_path = st.selectbox("记忆状态", [project_config.default_state_path])
    if app_scenario == tabs_title[0]:
        base_model_manager(file_status_manager)
    elif app_scenario == tabs_title[1]:
        if tabs_title_enabled[0]:
            knowledgebase_manager(index_client, file_status_manager)
        else:
            st.write("配置文件里没开启该功能")
    elif app_scenario == tabs_title[2]:
        if tabs_title_enabled[1]:
            internet_search(index_client, file_status_manager)
        else:
            st.write("配置文件里没开启该功能")
    elif app_scenario == tabs_title[3]:
        # 在这里添加微调选项卡的内容
        if tabs_title_enabled[2]:
            st.title("模型微调")
            tuning_client = TuningClient('tcp://localhost:7787')
            jsonl2binidx_manager(tuning_client)
            wandb_manager(tuning_client)
            tuning_manager(tuning_client, app_scenario, )
        else:
            st.write("配置文件里没开启该功能")
    else:
        if tabs_title_enabled[4]:
            st.title("知识问答")
            llm_client = LLMClient("tcp://localhost:7781")
            rag_chain(index_client, llm_client)
        else:
            st.write("配置文件里没开启该功能")


if __name__ == "__main__":
    main()
