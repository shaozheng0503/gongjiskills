"""内置镜像模板库

所有模板都来自共绩算力管理中台的**预制镜像**（admin.didisuanli.cn 后台），
已在平台镜像仓库（harbor.suanleme.cn）预缓存，拉取快、开箱即用。

模板按用途分类。Agent 和用户可以先 `gongji images --category <cat>` 看同类镜像，
再 `gongji deploy --template <name>` 一键部署。

字段说明：
    image (必填) : Docker 镜像地址
    category     : 分类 key（见 CATEGORIES）
    description  : 简要说明（中文）
    port         : 默认暴露端口，多个用逗号分隔
    gpu          : 推荐 GPU 型号关键词（如 4090 / H20）
    gpu_count    : 推荐 GPU 卡数（整数）
    env          : 环境变量字符串（KEY=val KEY2=val2）
    start_cmd    : 容器启动命令
    start_args   : 启动参数，list[str] 或 str
    docs         : 平台文档链接
    note         : 备注（硬件要求等）
"""

CATEGORIES: dict[str, str] = {
    "llm": "大语言模型推理",
    "multimodal": "多模态视觉",
    "image-gen": "文生图",
    "image-edit": "图像编辑/人像",
    "video": "视频生成",
    "3d": "3D 重建",
    "audio": "语音合成/识别",
    "music": "音乐生成",
    "ocr": "文档解析/OCR",
    "dev": "训练/开发环境",
    "tools": "工具类",
}


BUILTIN_TEMPLATES: dict[str, dict] = {
    # ══════════════════════ LLM ══════════════════════
    # `vllm` / `ollama` 映射到平台预制镜像，短名便于记忆
    "vllm": {
        "image": "harbor.suanleme.cn/public-hub/vllm-openai:v0.19.0-copy",
        "category": "llm",
        "description": "平台预制 vLLM，默认启动 Qwen3-8B-FP8（可用 --start-cmd 覆盖）",
        "port": "8000",
        "gpu": "4090",
        "env": "VLLM_USE_MODELSCOPE=true",
        "start_cmd": "/bin/bash",
        "start_args": ["-c", "vllm serve Qwen/Qwen3-8B-FP8 --max-model-len 16K --max-num-seqs 2"],
        "docs": "https://www.gongjiyun.com/docs/flexible-deployment/pre-fabricated-services/lpp2wq1gmiskmqkvf3ycpwxvnhf/",
    },
    "ollama": {
        "image": "harbor.suanleme.cn/public-hub/ollama:2025-10-30-rc1",
        "category": "llm",
        "description": "平台预制 Ollama（需自行 pull 模型）",
        "port": "11434",
        "gpu": "4090",
        "docs": "https://www.gongjiyun.com/docs/flexible-deployment/pre-fabricated-services/l5qnwltyeiumluk7hbqcucofnsr/",
    },
    "qwen3.5-0.8b": {
        "image": "harbor.suanleme.cn/public-hub/vllm-openai:v2026-3-5-nightly",
        "category": "llm",
        "description": "Qwen3.5-0.8B 超轻量 LLM（边缘/低延时场景）",
        "port": "8000",
        "gpu": "4090",
        "env": "VLLM_USE_MODELSCOPE=true",
        "start_cmd": "/bin/bash",
        "start_args": [
            "-c",
            "vllm serve Qwen/Qwen3.5-0.8B --max-model-len 131072 --max-num-seqs 64 "
            "--gpu-memory-utilization 0.90 "
            "--override-generation-config '{\"thinking_budget\": 0}'",
        ],
    },
    "qwen3.5-9b": {
        "image": "harbor.suanleme.cn/public-hub/qwen35-9b:v0.17.0-rc1",
        "category": "llm",
        "description": "Qwen3.5-9B vLLM 推理，OpenAI 兼容",
        "port": "8000",
        "gpu": "4090",
        "start_cmd": "bash",
        "start_args": [
            "-c",
            "vllm serve Qwen/Qwen3.5-9B --max-model-len 32k --max-num-seqs 32 "
            "--gpu-memory-utilization 0.95 --max-cudagraph-capture-size 32",
        ],
    },
    "qwen3.5-9b-claude": {
        "image": "harbor.suanleme.cn/public-hub/vllm-openai:v2026-3-5-nightly",
        "category": "llm",
        "description": "Qwen3.5-9B 蒸馏 Claude 4.6 Opus 推理能力的融合模型",
        "port": "8000",
        "gpu": "4090",
        "gpu_count": 1,
        "env": "VLLM_USE_MODELSCOPE=true",
        "start_cmd": "/bin/bash",
        "start_args": [
            "-c",
            "vllm serve Jackrong/Qwen3.5-9B-Claude-4.6-Opus-Reasoning-Distilled "
            "--host 0.0.0.0 --port 8000 --served-model-name qwopus_9b "
            "--tensor-parallel-size 1 --trust-remote-code "
            "--gpu-memory-utilization 0.90 --max-model-len 4096 --max-num-seqs 8 "
            "--dtype auto --generation-config vllm --reasoning-parser qwen3 "
            "--tokenizer Qwen/Qwen3.5-27B",
        ],
        "note": "推荐单卡 4090",
    },
    "qwen3.5-27b": {
        "image": "harbor.suanleme.cn/public-hub/vllm-openai:v2026-3-5-nightly",
        "category": "llm",
        "description": "Qwen3.5-27B 阿里 270 亿参数稠密多模态，26 万上下文",
        "port": "8000",
        "gpu": "4090",
        "gpu_count": 8,
        "env": "VLLM_USE_MODELSCOPE=true",
        "start_cmd": "/bin/bash",
        "start_args": [
            "-c",
            "vllm serve Qwen/Qwen3.5-27B --port 8000 --tensor-parallel-size 8 "
            "--max-model-len 262144 --reasoning-parser qwen3 "
            "--enable-auto-tool-choice --tool-call-parser qwen3_coder",
        ],
        "note": "建议 4×4090 或 8×4090",
    },
    "qwen3.5-27b-claude-gguf": {
        "image": "harbor.suanleme.cn/public-hub/vllm-openai:v2026-3-5-nightly",
        "category": "llm",
        "description": "Qwen3.5-27B 蒸馏 Claude 4.6 Opus 推理能力的 GGUF 量化版",
        "gpu": "4090",
        "gpu_count": 4,
        "env": "VLLM_USE_MODELSCOPE=true PYTORCH_ALLOC_CONF=expandable_segments:True",
        "start_cmd": "/bin/bash",
        "start_args": [
            "-c",
            "vllm serve Jackrong/Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled-v2 "
            "--host 0.0.0.0 --port 8000 --served-model-name qwopus_27b "
            "--tensor-parallel-size 4 --trust-remote-code "
            "--gpu-memory-utilization 0.80 --max-model-len 4096 --max-num-seqs 8 "
            "--dtype auto --generation-config vllm --reasoning-parser qwen3 "
            "--tokenizer Qwen/Qwen3.5-27B",
        ],
        "note": "推荐 4×4090",
    },
    "qwen3-30b-webui": {
        "image": "harbor.suanleme.cn/public-hub/qwen3-32b:20250711",
        "category": "llm",
        "description": "Ollama + Open WebUI，内置 Qwen3-30B-A3B 模型",
        "port": "11434",
        "gpu": "4090",
        "gpu_count": 1,
        "note": "建议单卡 4090",
    },
    "minicpm-4-8b": {
        "image": "harbor.suanleme.cn/public-hub/minicpm4-8b:latest",
        "category": "llm",
        "description": "面壁智能 MiniCPM 4-8B 端侧大模型（基于 Ollama）",
        "port": "11434",
        "gpu": "4090",
        "gpu_count": 1,
        "env": "OLLAMA_HOST=0.0.0.0 OLLAMA_ORIGINS=*",
        "docs": "https://www.gongjiyun.com/docs/flexible-deployment/pre-fabricated-services/xdpswcng2ilsbtkgbzwcrejlnia/",
    },
    "gpt-oss-20b": {
        "image": "harbor.suanleme.cn/public-hub/gpt-oss-20b:sglang",
        "category": "llm",
        "description": "OpenAI GPT-OSS-20B 开源模型，稀疏激活",
        "port": "30000",
        "gpu": "4090",
        "docs": "https://www.gongjiyun.com/docs/flexible-deployment/pre-fabricated-services/jyrkwxxmhi1t68ktdancqk6hnfb/",
    },

    # ══════════════════════ 多模态视觉 ══════════════════════
    "qwen3-8b-vl": {
        "image": "harbor.suanleme.cn/public-hub/vllm-openai:qwen3-8b-vl-20251031103919358",
        "category": "multimodal",
        "description": "Qwen3-VL-8B 视觉语言模型，长上下文 + 视频理解",
        "port": "8000",
        "gpu": "4090",
        "start_cmd": "/bin/sh",
        "start_args": [
            "-c",
            "vllm serve Qwen/Qwen3-VL-8B-Instruct-FP8 --max-model-len 32K --max-num-seqs 4 "
            "--limit-mm-per-prompt '{\"image\":4,\"video\":0}' --mm-processor-cache-gb 0",
        ],
        "docs": "https://www.gongjiyun.com/docs/flexible-deployment/pre-fabricated-services/ycggwebvtiknjgkkrhyc0qpmn3c/",
    },
    "minicpm-o-4.5": {
        "image": "harbor.suanleme.cn/public-hub/minicpm-o-4_5:2.0.0",
        "category": "multimodal",
        "description": "MiniCPM-o4.5 端侧多模态，图/视频/文/音输入，文本+语音输出",
        "port": "8006",
        "gpu": "4090",
    },
    "hunyuan-image-3": {
        "image": "harbor.suanleme.cn/public-hub/hunyuanimage3:v1.0.0",
        "category": "multimodal",
        "description": "腾讯 HunyuanImage-3 原生多模态，文生图 + 图生图",
        "port": "30000",
        "gpu": "H20",
        "gpu_count": 8,
        "note": "需 8 张 ≥80G 显存，推荐 8×H20",
    },

    # ══════════════════════ 文生图 ══════════════════════
    "qwen-image": {
        "image": "harbor.suanleme.cn/public-hub/comfyui-qwen-image:8steps-loras-20251010124623105",
        "category": "image-gen",
        "description": "阿里 Qwen-Image 文生图基础模型，MMDiT 架构 20B，文字渲染强",
        "port": "3000,8188",
        "gpu": "4090",
        "docs": "https://www.gongjiyun.com/docs/flexible-deployment/pre-fabricated-services/m0fpwrltaixdvpki9ebcljlcnqf/",
    },
    "qwen-image-2512": {
        "image": "harbor.suanleme.cn/public-hub/qwen-image-2512:v1.2-20260211152453201",
        "category": "image-gen",
        "description": "Qwen-Image 12 月更新版，画面更真实、细节更精致",
        "port": "8188,3000",
        "gpu": "4090",
    },
    "z-image": {
        "image": "harbor.suanleme.cn/public-hub/z-image:0.11.0-20260129113314700",
        "category": "image-gen",
        "description": "Z-Image 完整容量 Transformer，风格覆盖广、提示词精准",
        "port": "8188,3000",
        "gpu": "4090",
        "docs": "https://www.gongjiyun.com/docs/flexible-deployment/pre-fabricated-services/xsafwp2fkiysw3kygxzct3f4nwd/",
    },
    "z-image-turbo": {
        "image": "harbor.suanleme.cn/public-hub/z_image_turbo:1.0.0-20251128100853041",
        "category": "image-gen",
        "description": "Z-Image Turbo 8 NFEs 亚秒级推理，16GB 消费卡可跑",
        "port": "8188,3000",
        "gpu": "4090",
        "docs": "https://www.gongjiyun.com/docs/flexible-deployment/pre-fabricated-services/hdwgwf9ueiri8vkhum0couxpnlg/",
    },
    "flux2-dev": {
        "image": "harbor.suanleme.cn/public-hub/flux2:2.0.1-20251130010929605",
        "category": "image-gen",
        "description": "FLUX.2 [dev] 多参考图角色/风格一致，400 万像素图像编辑",
        "port": "8188,3000",
        "gpu": "4090",
        "docs": "https://www.gongjiyun.com/docs/flexible-deployment/pre-fabricated-services/oabhwoxwlitte3kofdlcpoawnre/",
    },
    "flux1-krea": {
        "image": "harbor.suanleme.cn/public-hub/comfyui-krea:0.2",
        "category": "image-gen",
        "description": "FLUX.1 Krea [dev] 克服 AI 味，更真实多样输出",
        "port": "3000,8188",
        "gpu": "4090",
        "docs": "https://www.gongjiyun.com/docs/flexible-deployment/pre-fabricated-services/geliwpy6dif5vukpvgncyne0nsc/",
    },
    "flux1-dev-comfyui": {
        "image": "harbor.suanleme.cn/public-hub/comfyui-flux:0.5",
        "category": "image-gen",
        "description": "Flux.1-dev ComfyUI 服务（网页 8188 单节点，生产 3000 多节点）",
        "port": "3000,8188",
        "gpu": "4090",
        "gpu_count": 1,
        "docs": "https://www.gongjiyun.com/docs/flexible-deployment/pre-fabricated-services/ykjzwpbbmibaajkwkfpcb11jnce/",
    },
    "sd3.5-comfyui": {
        "image": "harbor.suanleme.cn/public-hub/comfyui-sd:v3.5-1",
        "category": "image-gen",
        "description": "SD 3.5 large ComfyUI，内置工作流",
        "port": "3000,8188",
        "gpu": "4090",
        "gpu_count": 1,
        "docs": "https://www.gongjiyun.com/docs/flexible-deployment/pre-fabricated-services/y0qjw1tg3iddv8k3gqkctc1xn4d/",
    },
    "sd2.1-webui": {
        "image": "harbor.suanleme.cn/public-hub/lightcloud/sd-webui:hsz12111834-20251211183550518",
        "category": "image-gen",
        "description": "SD 2.1 文生图 WebUI（单节点）",
        "port": "7860",
        "gpu": "4090",
        "gpu_count": 1,
        "docs": "https://www.gongjiyun.com/docs/flexible-deployment/pre-fabricated-services/rllmwjekqiadi4khxftcqwzrnhc/",
    },
    # `sd-webui` 短名映射到 SD 1.5（最常用）
    "sd-webui": {
        "image": "harbor.suanleme.cn/public-hub/stable-diffusion-webui:v1",
        "category": "image-gen",
        "description": "SD 1.5 文生图 WebUI（单节点，`sd-webui` 短名）",
        "port": "7860",
        "gpu": "4090",
        "gpu_count": 1,
        "docs": "https://www.gongjiyun.com/docs/flexible-deployment/pre-fabricated-services/yjqiw6trbihsw9klma1co5monpf/",
    },

    # ══════════════════════ 图像编辑/人像 ══════════════════════
    "qwen-image-layered": {
        "image": "harbor.suanleme.cn/public-hub/qwen-image-layered:1.2",
        "category": "image-edit",
        "description": "Qwen-Image-Layered RGBA 分层编辑，类 PS 图层级",
        "port": "7869",
        "gpu": "5090",
        "note": "建议 5090 及以上",
        "docs": "https://www.gongjiyun.com/docs/flexible-deployment/pre-fabricated-services/jhbuwtlsoivrsmkilqucp0uun3b/",
    },
    "qwen-image-edit": {
        "image": "harbor.suanleme.cn/public-hub/comfyui-qwen-image-edit:0.2.2",
        "category": "image-edit",
        "description": "Qwen-Image-Edit 通义图像编辑（修改/增强/修复）",
        "port": "3000,8188",
        "gpu": "4090",
        "docs": "https://www.gongjiyun.com/docs/flexible-deployment/pre-fabricated-services/etwcwf29nijubcko8hycufkvnxg/",
    },
    "flux1-kontext": {
        "image": "harbor.suanleme.cn/public-hub/comfyui-kontext:0.3",
        "category": "image-edit",
        "description": "Flux.1 Kontext 黑森林图像编辑，角色一致/局部编辑",
        "port": "3000,8188",
        "gpu": "4090",
        "docs": "https://www.gongjiyun.com/docs/flexible-deployment/pre-fabricated-services/vsy1wrm8nizlsvkqwjucvjapn2b/",
    },
    "comfyui-facefusion": {
        "image": "harbor.suanleme.cn/public-hub/comfyui-facefusio-api:invisiblekk-298b5307-7f5d-4c83-9c55-1be3e0191574",
        "category": "image-edit",
        "description": "ComfyUI 节点封装 FaceFusion，支持 API 调用",
        "port": "3000,8188",
        "gpu": "4090",
        "docs": "https://www.gongjiyun.com/docs/flexible-deployment/pre-fabricated-services/bv6dwthf5ispsjkyfnicmepwn1f/",
    },
    "facefusion": {
        "image": "harbor.suanleme.cn/public-hub/facefusion:0.1.0",
        "category": "image-edit",
        "description": "开源人脸融合工具，换脸/表情迁移",
        "port": "7860",
        "gpu": "4090",
        "docs": "https://www.gongjiyun.com/docs/flexible-deployment/pre-fabricated-services/lrgcwc6wuijywzkwasychtzbnec/",
    },
    "codeformer": {
        "image": "harbor.suanleme.cn/public-hub/codeformer:070718",
        "category": "image-edit",
        "description": "CodeFormer 图像清晰度提升、去马赛克",
        "port": "7860",
        "gpu": "4090",
        "docs": "https://www.gongjiyun.com/docs/flexible-deployment/pre-fabricated-services/npk7wmkvwiw0stkhqzdcppw4npf/",
    },
    "hunyuan-portrait": {
        "image": "harbor.suanleme.cn/public-hub/hyportrait:070714",
        "category": "image-edit",
        "description": "HunyuanPortrait 肖像表情/姿势动画",
        "port": "8089",
        "gpu": "4090",
        "docs": "https://www.gongjiyun.com/docs/flexible-deployment/pre-fabricated-services/wwy8wp8w6i3obkkvwolc5gzbntd/",
    },
    "hivision-idphotos": {
        "image": "harbor.suanleme.cn/public-hub/hivision_idphotos:latest",
        "category": "image-edit",
        "description": "HivisionIDPhotos AI 证件照生成",
        "port": "7860,8080",
        "gpu": "4090",
        "env": "share=True",
        "docs": "https://www.gongjiyun.com/docs/flexible-deployment/pre-fabricated-services/gnfiw9tghi44hpkcetccxr0wnqh/",
    },

    # ══════════════════════ 视频生成 ══════════════════════
    "wan2.2-i2v": {
        "image": "harbor.suanleme.cn/public-hub/wan2.2-14b:4steps-loras-20251009183959113",
        "category": "video",
        "description": "Wan2.2-I2V-14B 通义万相 MoE 图生视频，电影级质感",
        "port": "3000,8188",
        "gpu": "4090",
    },
    "wan2.2": {
        "image": "harbor.suanleme.cn/public-hub/wan-2.2:0.2",
        "category": "video",
        "description": "WAN 2.2 全球首个 MoE 视频生成，270 亿参数",
        "port": "3000,8188",
        "gpu": "4090",
        "docs": "https://www.gongjiyun.com/docs/flexible-deployment/pre-fabricated-services/vndvwtwy6ihh2skqz7vcsmxrnsy/",
    },
    "framepack-f1": {
        "image": "harbor.suanleme.cn/public-hub/framepack:0.4-f1",
        "category": "video",
        "description": "FramePack-F1 图生视频高清输出（单节点）",
        "port": "7860",
        "gpu": "4090",
        "gpu_count": 1,
        "env": "HF_ENDPOINT=https://hf-mirror.com",
        "docs": "https://www.gongjiyun.com/docs/flexible-deployment/pre-fabricated-services/h03bwgkgjifejjkwklccf6tpnmd/",
    },

    # ══════════════════════ 3D 重建 ══════════════════════
    "hunyuan-world-mirror": {
        "image": "harbor.suanleme.cn/public-hub/hunyuanworld-mirror:0.3.8",
        "category": "3d",
        "description": "HunyuanWorld-Mirror 腾讯 3D 重建，多视图/视频秒级生成 3D 场景",
        "port": "7860",
        "gpu": "4090",
        "gpu_count": 1,
        "docs": "https://www.gongjiyun.com/docs/flexible-deployment/pre-fabricated-services/kuxjwpidlizeqgk0ce6c6cs8nzg/",
    },

    # ══════════════════════ 语音合成/识别 ══════════════════════
    "indextts": {
        "image": "harbor.suanleme.cn/public-hub/index-tts:0.3.0",
        "category": "audio",
        "description": "IndexTTS B 站开源 TTS，中英高质量、零样本声音克隆",
        "port": "7860",
        "gpu": "4090",
        "start_cmd": "/bin/bash",
        "start_args": [
            "-c",
            "GRADIO_ROOT_PATH=$(echo \"$HOSTNAME\" | sed -E 's,^(([^-]+-){3}).*,https://\\17860.550c.cloud,') "
            ".venv/bin/python webui.py",
        ],
        "docs": "https://www.gongjiyun.com/docs/flexible-deployment/pre-fabricated-services/rdaaw9nuuizgnjk6gomct5m7nmf/",
    },
    "funasr": {
        "image": "harbor.suanleme.cn/public-hub/funasr-online-server:V070117",
        "category": "audio",
        "description": "FunASR 语音识别：ASR/VAD/标点/说话人分类",
        "port": "10095",
        "gpu": "4090",
        "docs": "https://www.gongjiyun.com/docs/flexible-deployment/pre-fabricated-services/u2f3wvacwiqxdgk1vpqc1ptdnpe/",
    },
    "cosyvoice": {
        "image": "harbor.suanleme.cn/public-hub/cosyvoice:v2.0.0",
        "category": "audio",
        "description": "CosyVoice 近真人自然语音 TTS（单节点）",
        "port": "7860",
        "gpu": "4090",
        "docs": "https://www.gongjiyun.com/docs/flexible-deployment/pre-fabricated-services/ehh3wzfijipwrckp1kpchuzbnqh/",
    },
    "whisper": {
        "image": "harbor.suanleme.cn/public-hub/openai-whisper-asr-webservice:v1.8.2-gpu",
        "category": "audio",
        "description": "OpenAI Whisper 人类水准 ASR，生产可用",
        "port": "9000",
        "gpu": "4090",
        "gpu_count": 1,
        "docs": "https://www.gongjiyun.com/docs/flexible-deployment/pre-fabricated-services/sjgkwdocbijmrlkppnkc9foxndb/",
    },

    # ══════════════════════ 音乐生成 ══════════════════════
    "acestep-1.5": {
        "image": "harbor.suanleme.cn/community-hub/vm/pytorch271-cuda128-ubuntu2204:acestep1.5-20260205172411051",
        "category": "music",
        "description": "ACE-Step 1.5 音乐生成 + 开发环境（Jupyter/code-server 集成）",
        "port": "8888,62661,7860,8001",
        "gpu": "4090",
        "docs": "https://www.gongjiyun.com/docs/flexible-deployment/pre-fabricated-services/ndoswjtzbi7xwmk7f6zc72otnte/",
    },
    "acestep": {
        "image": "harbor.suanleme.cn/public-hub/acestep:1.0",
        "category": "music",
        "description": "ACE-Step 音乐生成基础模型（单节点）",
        "port": "7865",
        "gpu": "4090",
        "env": "bf16=True torch_compile=True overlapped_decode=True",
        "docs": "https://www.gongjiyun.com/docs/flexible-deployment/pre-fabricated-services/ruqpwt63nifwm6klfitccvmanqc/",
    },

    # ══════════════════════ 文档解析/OCR ══════════════════════
    "paddleocr-vl": {
        "image": "harbor.suanleme.cn/public-hub/paddlepaddle/paddlex-genai-vllm-server:hsz202510291601-20251029160827276",
        "category": "ocr",
        "description": "PaddleOCR-VL-0.9B 百度超轻量文档解析视觉-语言模型",
        "port": "8080",
        "gpu": "4090",
        "docs": "https://www.gongjiyun.com/docs/flexible-deployment/pre-fabricated-services/of4gwols0irt84kc5atc7yfhnbh/",
    },
    "mineru": {
        "image": "harbor.suanleme.cn/public-hub/mineru:0.1.3",
        "category": "ocr",
        "description": "MinerU 2.5 PDF→Markdown/JSON，含布局检测/公式/表格",
        "port": "8000,7860",
        "gpu": "4090",
        "env": "USE_API=false",
        "docs": "https://www.gongjiyun.com/docs/flexible-deployment/pre-fabricated-services/phrywztvniedlkknimdcy601nld/",
    },

    # ══════════════════════ 训练/开发环境 ══════════════════════
    "ubuntu2404": {
        "image": "harbor.suanleme.cn/public-hub/ubuntu2404-base:2025-12-11-rc1",
        "category": "dev",
        "description": "Ubuntu 24.04 基础镜像，内置 Jupyter(8888) + code-server(62661)",
        "port": "8888,62661,8000,8001,8002",
        "gpu": "4090",
    },
    # `jupyter` 短名映射到 Ubuntu2404（含 Jupyter 服务）
    "jupyter": {
        "image": "harbor.suanleme.cn/public-hub/ubuntu2404-base:2025-12-11-rc1",
        "category": "dev",
        "description": "Ubuntu 24.04 + Jupyter Notebook（`jupyter` 短名，同 ubuntu2404）",
        "port": "8888,62661",
        "gpu": "4090",
    },
    "llama-factory": {
        "image": "harbor.suanleme.cn/public-hub/ddn-k8s/docker.io/opencsghq/llama-factory:hsz202511161954-20251116103636754",
        "category": "dev",
        "description": "LLaMA Factory 无代码微调平台（支持上百种模型）",
        "port": "7860,8000",
        "gpu": "4090",
    },

    # ══════════════════════ 工具类 ══════════════════════
    "dailyhot": {
        "image": "harbor.suanleme.cn/public-hub/dailyhot:1.0",
        "category": "tools",
        "description": "DailyHot 全网多平台热榜聚合（Web + API）",
        "port": "6688,80",
        "docs": "https://www.gongjiyun.com/docs/flexible-deployment/pre-fabricated-services/bxgbwq5w4igq2qkg1kuce4j8neb/",
    },
}


def group_by_category(templates: dict) -> dict[str, list[tuple[str, dict]]]:
    """把模板按 category 分组，返回 {category_key: [(name, tmpl), ...]}

    未指定分类的模板放在 "_uncategorized"。
    """
    groups: dict[str, list[tuple[str, dict]]] = {}
    for name, tmpl in templates.items():
        cat = tmpl.get("category") or "_uncategorized"
        groups.setdefault(cat, []).append((name, tmpl))
    for cat in groups:
        groups[cat].sort(key=lambda x: x[0])
    return groups
