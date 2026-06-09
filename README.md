# zpp - CLI 工具，带有 WebUI 的大模型对话工具

一个命令行工具，提供 Web 界面与大语言模型进行交互，支持 RAG (检索增强生成)。

## 环境配置

本项目使用 `zptest` 虚拟环境进行开发。

### 创建虚拟环境

```bash
# 使用 venv 创建虚拟环境
python -m venv zptest

# 或使用 conda 创建虚拟环境
conda create -n zptest python=3.10
```

### 激活虚拟环境

```bash
# macOS/Linux (venv)
source zptest/bin/activate

# Windows (venv)
zptest\Scripts\activate

# conda
conda activate zptest
```

### 退出虚拟环境

```bash
# venv
deactivate

# conda
conda deactivate
```

### 删除虚拟环境

```bash
# venv - 直接删除文件夹
rm -rf zptest

# conda
conda remove -n zptest --all
```

## 安装

```bash
# 安装 zpp 命令（开发模式）
pip install -e .
```

## 使用方法

### 启动 WebUI

```bash
zpp webui
```

这将自动启动 Web 服务器并在浏览器中打开界面。

### 命令选项

- `--port`: 指定端口号（默认：5000）
- `--host`: 指定主机地址（默认：127.0.0.1）
- `--no-browser`: 不自动打开浏览器

示例：
```bash
zpp webui --port 8080 --host 0.0.0.0
```

### 查看配置

```bash
zpp config
```

### 初始化知识库 (RAG)

```bash
# 初始化知识库
zpp init

# 指定知识库目录
zpp init --dir /path/to/knowledge

# 显示详细信息
zpp init -v
```

### 搜索知识库

```bash
zpp search "你的问题"
```

### 清空知识库

```bash
zpp clear
```

## 功能说明

### RAG (检索增强生成)

zpp 支持 RAG 功能，可以将知识文件向量化存储，在对话时自动检索相关内容：

1. **添加知识文件** - 将 `.txt`, `.md`, `.json` 等文件放入 `zpp/knowlage/` 目录
2. **初始化知识库** - 运行 `zpp init` 创建向量数据库
3. **智能对话** - 对话时自动检索相关知识并带给大模型

### 对话功能

- 在对话页面底部输入消息
- 按回车键或点击发送按钮发送消息
- 消息会发送给配置的大模型，并显示回复

### 模型配置

- **API Key**: 大模型的 API 密钥
- **模型**: 指定使用的模型名称（如 gpt-3.5-turbo, gpt-4 等）
- **API 接口地址**: 模型 API 的请求地址

配置信息保存在 `~/.zpp/config.json` 文件中。

## 支持的 API

默认支持 OpenAI 格式的 API，可以配置兼容的第三方服务。
