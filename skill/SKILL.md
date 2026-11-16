---
name: pf-pay-repo
version: 1.0.0
description: pf_pay 仓库：18 个文件，主语言Python 9，JSON 1
trigger_conditions:
  - 需要理解、修改或排障 pf_pay 的代码
  - 在 pf_pay 里定位入口、数据表、对外契约或构建方式
---

# pf_pay 仓库技能

> 由仓库实际内容生成的骨架（README/目录/模型定义/契约/构建脚本逐项取证）。新增判断与坑位请直接在下面对应小节补充。

## 定位

**pf_pay**

a payment module for platform business

- 远端：`https://github.com/yumoqing/pf_pay.git`
- 默认分支：`main`（共 2 个提交）
- 最近提交：2026-11-03 `12d3952` feat: 微信支付 H5/Native 通道 + payment_log + 支付回调 dspy，移除旧 weixin_pay
- 规模：18 个文件；Python 9，JSON 1

## 目录结构

- `pf_pay/` — Python 包源码（模块本体）（8 个文件）
- `conf/` — 配置（`config.json`；密码为 AES 密文）（3 个文件）
- `wwwroot/` — 前端页面与 `.dspy` 契约（服务端渲染入口）（2 个文件）
- `models/` — 表定义（`models/*.json`，DDL/表结构唯一源）（1 个文件）
- 根文件：`.gitignore`、`README.md`、`requirements.txt`、`setup.py`

## 对外契约（`.dspy`，2 个）

- `wwwroot/alipay/recharge_callback/`：1 个 — index.dspy
- `wwwroot/wxpay/recharge_callback/`：1 个 — index.dspy

## 注册入口

- `pf_pay/init.py` → `load_pf_pay()`
- `pf_pay/wechat_pay_h5.py` → `load_public_key_from_file()`、`load_private_key_from_file()`、`load_private_key()`

## 代码入口（顶层 Python）

- `setup.py`
- `pf_pay/ali_pay.py` — config:{
- `pf_pay/init.py`
- `pf_pay/payment_log.py`
- `pf_pay/paypal_pay.py`
- `pf_pay/version.py`
- `pf_pay/wechat_pay_h5.py`
- `pf_pay/weixin_native_pay.py` — def __init__(self):

## 构建与运行

- `setup.py`：`pf_pay` v?，依赖 0 项
- `requirements.txt`：2 项（paypalrestsdk、python-alipay-sdk）
- Python 包 `pf_pay/`：`__init__.py`、`ali_pay.py`、`init.py`、`payment_log.py`、`paypal_pay.py`、`version.py`、`wechat_pay_h5.py`、`weixin_native_pay.py`

## 建议阅读顺序

1. `README.md`
2. `models/`
3. `pf_pay/init.py`
4. `wwwroot/`

