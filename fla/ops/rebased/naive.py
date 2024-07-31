# -*- coding: utf-8 -*-

import torch
from einops import rearrange

from fla.ops.rebased.parallel import parallel_rebased

def naive_parallel_rebased(q, k, v, use_scale=True, use_norm=True):
    if use_scale:
        q = q * (q.shape[-1] ** -0.5)
    attn = q @ k.transpose(-2, -1)
    attn = (attn ** 2)
    attn.masked_fill_(~torch.tril(torch.ones(
        q.shape[-2], q.shape[-2], dtype=torch.bool, device=q.device)), 0)
    o = attn @ v
    if use_norm:
        z = attn.sum(-1)
        return o / (z[..., None] + 1e-6)
    else:
        return o
