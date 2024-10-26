#coding:utf-8
import os

import wandb

from src.services import AbstractServiceWorker
from src.tools import Jsonl2Binidx, shell_command

class WandbManager:
    """
    wandb管理
    """
    # TODO 后续加缓存

    def __init__(self):
        self.api = None
        self.username = ''
    def user_name(self):
        if self.username:
            return self.username
        try:
            if self.api is None:
                self.api = wandb.Api()
            self.username = self.api.viewer.username
            return self.username
        except:
            return ''


    def login(self, api_key):
        try:
            wandb.login(key=api_key, relogin=True)
        except Exception as e:
            return '登录失败:' + str(e)
        self.api = wandb.Api()
        return '登录成功'


    def add_project(self, project_name):
        try:
            if self.api is None:
                self.api = wandb.Api()
            entity = self.api.viewer.entity
            self.api.create_project(project_name, entity)
            return '添加成功'
        except Exception as e:
            return '添加失败:' + str(e)

    def list_project(self):
        try:
            if self.api is None:
                self.api = wandb.Api()
            projects = self.api.projects()
            project_names =[project.name for project in projects]
            return project_names
        except Exception as e:
            return []



class ServiceWorker(AbstractServiceWorker):
    def init_with_config(self, config):
        print(config, 'tttt')
        self.jsonl_path = config.get('jsonl_path')
        self.output_path = config.get('output_path')
        self.n_epoch = config.get('n_epoch', 3)
        self.context_len = 1024

        self.load_model = config.get('model_path')
        self.proj_dir = config.get('project_dir')
        self.data_file = config.get('data_file')
        self.wandb_manager = WandbManager()

    def cmd_make_data(self, cmd: dict):
        jsonl_file = cmd.get('jsonl_file') or self.jsonl_path
        context_len = cmd.get('context_len') or self.context_len
        output_path = cmd.get('output_path') or self.output_path
        n_epoch = cmd.get('n_epoch') or self.n_epoch
        is_str = cmd.get('is_str')

        if not is_str and not os.path.exists(jsonl_file):
            raise FileNotFoundError(f"{jsonl_file} not found")
        if not os.path.exists(output_path):
            raise NotADirectoryError(f"{output_path} not found")

        obj = Jsonl2Binidx(jsonl_file=jsonl_file, n_epoch=n_epoch,
                           output_path=output_path, context_len=context_len,
                           is_str=is_str)
        obj.run()
        return obj.output_file_name_prefix

    def cmd_tuning_config(self, cmd: dict):
        """
        tuning 服务配置
        """
        return self.service_config

    def cmd_wandb(self, cmd: dict):
        return self.wandb_manager.user_name()

    def cmd_wandb_login(self, cmd: dict):
        api_key = cmd.get('api_key')
        return self.wandb_manager.login(api_key)

    def cmd_wandb_add_project(self, cmd: dict):
        project_name = cmd.get('project_name')
        return self.wandb_manager.add_project(project_name)

    def cmd_wandb_list_project(self, cmd: dict):
        return self.wandb_manager.list_project()

    def cmd_lora(self, cmd: dict):
        load_model = cmd.get('load_model') or self.load_model
        proj_dir = cmd.get('proj_dir') or self.proj_dir
        data_file = cmd.get('data_file') or self.data_file
        if not load_model:
            raise ValueError("load_model is required")
        if not proj_dir:
            raise ValueError("proj_dir is required")
        if not data_file:
            raise ValueError("data_file is required")
        if not os.path.exists(load_model):
            raise FileNotFoundError(f"{load_model} not exists")
        if not os.path.exists(proj_dir):
            raise NotADirectoryError(f"{proj_dir} not exists")
        if not os.path.exists(data_file + '.idx'):
            raise FileNotFoundError(f"{data_file}.idx/bin not exists")
        quant = cmd.get('quant', 'nf4')
        n_layer = cmd.get('n_layer', 24)
        n_embd = cmd.get('n_embd', 2048)
        ctx_len = cmd.get('ctx_len', 1024)
        data_type = cmd.get('data_type', 'binidx')
        epoch_save = cmd.get('epoch_save', 1)
        vocab_size = cmd.get('vocab_size', 65536)
        epoch_begin = cmd.get('epoch_begin', 0)
        pre_ffn = cmd.get('pre_ffn', 0)
        head_qk = cmd.get('head_qk', 0)
        beta1 = cmd.get('beta1', 0.9)
        beta2 = cmd.get('beta2', 0.99)
        adam_eps = cmd.get('adam_eps', 1e-8)
        my_testing = cmd.get('my_testing', 'x060')
        strategy = cmd.get('strategy', 'deepspeed_stage_1')
        wandb = cmd.get('wandb', '')
        dataload = cmd.get('dataload', 'pad')
        lora_r = cmd.get('lora_r', 64)
        lora_alpha = cmd.get('lora_alpha', 128)
        micro_bsz = cmd.get('micro_bsz', 8)
        epoch_steps = cmd.get('epoch_steps', 1000)
        epoch_count = cmd.get('epoch_count', 20)
        lr_init = cmd.get('lr_init', 5e-5)
        lr_final = cmd.get('lr_final', 5e-5)
        warmup_steps = cmd.get('warmup_steps', 0)
        accelerator = cmd.get('accelerator', 'gpu')
        devices = cmd.get('devices', 1)
        precision = cmd.get('precision', 'bf16')
        grad_cp = cmd.get('grad_cp', 1)
        lora_dropout = cmd.get('lora_dropout', 0.01)
        lora_parts = cmd.get('lora_parts', 'att,ffn,time,ln')
        command = (f'python3 tuning_train.py --load_model {load_model} --proj_dir {proj_dir} '
                   f'--data_file {data_file} --data_type {data_type} --vocab_size {vocab_size} --ctx_len {ctx_len} '
                   f'--epoch_steps {epoch_steps}  --epoch_count {epoch_count} --epoch_begin {epoch_begin} '
                   f'--epoch_save {epoch_save} --micro_bsz {micro_bsz} --n_layer {n_layer} --n_embd {n_embd} '
                   f'--pre_ffn {pre_ffn} --head_qk {head_qk}   --lr_init {lr_init} --lr_final {lr_final}  '
                   f'--warmup_steps {warmup_steps} --beta1 {beta1} --beta2 {beta2} --adam_eps {adam_eps} '
                   f'--accelerator {accelerator} --devices {devices} --precision {precision} '
                   f'--strategy {strategy} --grad_cp {grad_cp}  --my_testing {my_testing} --lora '
                   f'--lora_r {lora_r} --lora_alpha {lora_alpha} --lora_dropout {lora_dropout} '
                   f'--lora_parts={lora_parts} --dataload {dataload} --loss_mask pad --quant {quant} '
                   f'--wandb {wandb}')

        try:
            code = shell_command(command, True)
        except Exception as e:
            return str(e)
        return code

    def cmd_state_tuning(self, cmd: dict):
        load_model = cmd.get('load_model') or self.load_model
        proj_dir = cmd.get('proj_dir') or self.proj_dir
        data_file = cmd.get('data_file') or self.data_file
        if not load_model:
            raise ValueError("load_model is required")
        if not proj_dir:
            raise ValueError("proj_dir is required")
        if not data_file:
            raise ValueError("data_file is required")
        if not os.path.exists(load_model):
            raise FileNotFoundError(f"{load_model} not exists")
        if not os.path.exists(proj_dir):
            raise NotADirectoryError(f"{proj_dir} not exists")
        if not os.path.exists(data_file + '.idx'):
            raise FileNotFoundError(f"{data_file}.idx/bin not exists")
        quant = cmd.get('quant', 'nf4')
        n_layer = cmd.get('n_layer', 24)
        n_embd = cmd.get('n_embd', 2048)
        ctx_len = cmd.get('ctx_len', 1024)
        data_type = cmd.get('data_type', 'binidx')
        epoch_save = cmd.get('epoch_save', 1)
        vocab_size = cmd.get('vocab_size', 65536)
        epoch_begin = cmd.get('epoch_begin', 0)
        pre_ffn = cmd.get('pre_ffn', 0)
        head_qk = cmd.get('head_qk', 0)
        beta1 = cmd.get('beta1', 0.9)
        beta2 = cmd.get('beta2', 0.99)
        adam_eps = cmd.get('adam_eps', 1e-8)
        my_testing = cmd.get('my_testing', 'x060')
        strategy = cmd.get('strategy', 'deepspeed_stage_1')
        wandb = cmd.get('wandb', '')

        micro_bsz = cmd.get('micro_bsz', 1)
        epoch_steps = cmd.get('epoch_steps', 800)
        epoch_count = cmd.get('epoch_count', 10)
        lr_init = cmd.get('lr_init', 1)
        lr_final = cmd.get('lr_final', 1e-2)
        warmup_steps = cmd.get('warmup_steps', 10)
        dataload = cmd.get('dataload', 'pad')
        accelerator = cmd.get('accelerator', 'gpu')
        devices = cmd.get('devices', 1)
        precision = cmd.get('precision', 'bf16')
        grad_cp = cmd.get('grad_cp', 1)
        command = (f'python3 tuning_train.py --load_model {load_model} --proj_dir {proj_dir} '
                   f'--data_file {data_file} --data_type {data_type} --vocab_size {vocab_size} --ctx_len {ctx_len} '
                   f'--epoch_steps {epoch_steps}  --epoch_count {epoch_count} --epoch_begin {epoch_begin} '
                   f'--epoch_save {epoch_save} --micro_bsz {micro_bsz} --n_layer {n_layer} --n_embd {n_embd} '
                   f'--pre_ffn {pre_ffn} --head_qk {head_qk}   --lr_init {lr_init} --lr_final {lr_final} '
                   f'--warmup_steps {warmup_steps} --beta1 {beta1} --beta2 {beta2} --adam_eps {adam_eps} '
                   f'--accelerator {accelerator} --devices {devices} --precision {precision} '
                   f'--strategy {strategy} --grad_cp {grad_cp}  --my_testing {my_testing}  '
                   f'--dataload {dataload}  --quant {quant} --train_type "state" '
                   f'--wandb {wandb}')

        try:
            code = shell_command(command, True)
        except Exception as e:
            return str(e)
        return code

    def cmd_pissa(self, cmd: dict):
        load_model = cmd.get('load_model') or self.load_model
        proj_dir = cmd.get('proj_dir') or self.proj_dir
        data_file = cmd.get('data_file') or self.data_file
        if not load_model:
            raise ValueError("load_model is required")
        if not proj_dir:
            raise ValueError("proj_dir is required")
        if not data_file:
            raise ValueError("data_file is required")
        if not os.path.exists(load_model):
            raise FileNotFoundError(f"{load_model} not exists")
        if not os.path.exists(proj_dir):
            raise NotADirectoryError(f"{proj_dir} not exists")
        if not os.path.exists(data_file + '.idx'):
            raise FileNotFoundError(f"{data_file}.idx/bin not exists")
        n_layer = cmd.get('n_layer', 24)
        n_embd = cmd.get('n_embd', 2048)
        ctx_len = cmd.get('ctx_len', 1024)
        data_type = cmd.get('data_type', 'binidx')
        epoch_save = cmd.get('epoch_save', 1)
        vocab_size = cmd.get('vocab_size', 65536)
        epoch_begin = cmd.get('epoch_begin', 0)
        pre_ffn = cmd.get('pre_ffn', 0)
        head_qk = cmd.get('head_qk', 0)
        beta1 = cmd.get('beta1', 0.9)
        beta2 = cmd.get('beta2', 0.99)
        adam_eps = cmd.get('adam_eps', 1e-8)
        my_testing = cmd.get('my_testing', 'x060')
        strategy = cmd.get('strategy', 'deepspeed_stage_1')
        wandb = cmd.get('wandb', '')
        svd_niter = cmd.get('svd_niter', 4)
        lora_r = cmd.get('lora_r', 64)
        micro_bsz = cmd.get('micro_bsz', 8)
        epoch_steps = cmd.get('epoch_steps', 1000)
        epoch_count = cmd.get('epoch_count', 1)
        lr_init = cmd.get('lr_init', 5e-5)
        lr_final = cmd.get('lr_final', 5e-5)
        warmup_steps = cmd.get('warmup_steps', 0)
        accelerator = cmd.get('accelerator', 'gpu')
        precision = cmd.get('precision', 'bf16')
        grad_cp = cmd.get('grad_cp', 1)
        devices = cmd.get('devices', 1)
        lora_alpha = cmd.get('lora_alpha', 128)
        lora_dropout = cmd.get('lora_dropout', 0.01)
        lora_parts = cmd.get('lora_parts', 'att,ffn,time,ln')
        dataload = cmd.get('dataload', 'pad')
        command = (
            f'python3 tuning_train.py  --load_model {load_model} --proj_dir {proj_dir} --data_file {data_file} '
            f'--data_type {data_type} --vocab_size {vocab_size} --ctx_len {ctx_len} '
            f'--epoch_steps {epoch_steps} --epoch_count {epoch_count} --epoch_begin {epoch_begin} '
            f'--epoch_save {epoch_save} --micro_bsz {micro_bsz} --n_layer {n_layer} --n_embd {n_embd} '
            f'--pre_ffn {pre_ffn} --head_qk {head_qk} --lr_init {lr_init} --lr_final {lr_final} '
            f'--warmup_steps {warmup_steps} --beta1 {beta1} --beta2 {beta2} --adam_eps {adam_eps} '
            f'--accelerator {accelerator} --devices {devices} --precision {precision} '
            f'--strategy {strategy} --grad_cp {grad_cp} --my_testing {my_testing} --lora --lora_r {lora_r} '
            f'--lora_alpha {lora_alpha} --lora_dropout {lora_dropout} --lora_parts={lora_parts} --PISSA '
            f'--svd_niter {svd_niter} --dataload {dataload} --wandb {wandb}  ')


        try:
            code = shell_command(command, True)
        except Exception as e:
            return str(e)
        return code

    def process(self, cmd: dict):
        cmd_name = cmd.get('cmd', '').lower()
        function_name = f'cmd_{cmd_name}'
        if hasattr(self, function_name) and callable(getattr(self, function_name)):
            return getattr(self, function_name)(cmd)
        return ServiceWorker.UNSUPPORTED_COMMAND