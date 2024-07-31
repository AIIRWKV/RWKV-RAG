# -*- coding: utf-8 -*-

import torch
import torch.nn.functional as F

from fla.ops.gla.recurrent_fuse import fused_recurrent_gla


def ceildiv(a, b):
    return -(a // -b)


def naive_recurrent_gla(
    q,
    k,
    v,
    gk,
    initial_state=None,
    output_final_state=False,
    causal=True
):
    orig_dtype = q.dtype
    q, k, v, gk = map(lambda x: x.float(), (q, k, v, gk))
    batch_size, n_heads, seq_len, d_head_k = q.shape
    _, _, _, d_head_v = v.shape
    h = torch.zeros(batch_size, n_heads, d_head_k, d_head_v, dtype=torch.float32, device=q.device)
    o = torch.zeros_like(v)
    scale = d_head_k ** -0.5

    if initial_state is not None:
        h += initial_state

    for i in range(seq_len):
        q_i = q[:, :, i, :] * scale
        k_i = k[:, :, i]
        v_i = v[:, :, i, :]
        gk_i = gk[:, :, i].exp()
        kv_i = k_i[..., None] * v_i[..., None, :]
        h = h * gk_i[..., None] + kv_i
        o_i = (q_i[..., None] * h).sum(-2)
        o[:, :, i] = o_i

    if causal:
        return o.to(orig_dtype), h
    else:
        o_reverse = torch.zeros_like(v)
        h = torch.zeros(batch_size, n_heads, d_head_k, d_head_v, dtype=torch.float32, device=q.device)
        for i in range(seq_len-1, -1, -1):
            q_i = q[:, :, i, :] * scale
            k_i = k[:, :, i]
            v_i = v[:, :, i, :]
            gk_i = gk[:, :, i].exp()
            kv_i = k_i[..., None] * v_i[..., None, :]
            h = h * gk_i[..., None] + kv_i
            o_i = (q_i[..., None] * h).sum(-2)
            o_reverse[:, :, i] = o_i

        return o, o_reverse

