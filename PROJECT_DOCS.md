# Biotech Monitor - 项目完整文档

> 最后更新: 2026-06-21

## 项目概述

Biotech Monitor 是一个生物医药行业动态追踪网站，监控以下领域：
- **基因编辑** (Gene Editing): CRISPR、碱基编辑、先导编辑
- **细胞治疗** (Cell Therapy): CAR-T、CAR-NK、iPSC
- **ADC** (Antibody-Drug Conjugates)
- **GLP-1** (代谢疾病药物)
- **肿瘤免疫** (IO)

## 网站架构

```
biotech-monitor/
├── index.html              # 主页面
├── css/
│   └── style.css          # 样式表
├── js/
│   └── main.js            # 前端逻辑（数据加载、渲染、AI分析）
├── data/
│   └── daily/             # JSON数据
│       ├── latest.json    # 最新完整数据
│       ├── summary.json   # 摘要版
│       ├── news_latest.json
│       └── company_latest.json
├── scripts/
│   ├── collect_pubmed.py  # PubMed论文抓取
│   ├── collect_bd_news.py # BD新闻抓取
│   └── daily_update.py    # 数据汇总+排序
├── proxy.py                # AI API本地代理（解决CORS）
├── auto_update.sh          # 自动化脚本
└── logs/                   # 运行日志
```

## 数据流

```
[PubMed API] ──┐
               ├──→ [collect scripts] ──→ [JSON files] ──→ [Website]
[RSS Feeds] ───┘                              ↑
                                            auto_update.sh
                                            (crontab 7:00)
```

## 自动更新机制

**Crontab 配置**：
```bash
0 7 * * * /bin/bash /Users/nnn_nice/scripts/biotech-monitor/auto_update.sh
```

**自动更新脚本执行流程**：
1. `python3 scripts/collect_pubmed.py` - 抓取近7天PubMed论文
2. `python3 scripts/collect_bd_news.py` - 抓取BD交易/临床/监管新闻
3. `python3 scripts/daily_update.py` - 合并数据并**按日期倒序排序**
4. `git add && commit && push` - 推送到GitHub
5. 网站前端每5分钟自动重新加载JSON

**手动运行**：
```bash
bash /Users/nnn_nice/scripts/biotech-monitor/auto_update.sh
```

## AI 深度解读功能

**工作原理**：
- 用户点击详情 → 前端检测是否有缓存（localStorage）
- 无缓存：调用AI生成 → 缓存到localStorage → 渲染
- 有缓存：直接渲染（秒开）

**API 配置**：
- **模型**: MiniMax-M3
- **API 端点**: https://api.minimax.chat/v1/chat/completions
- **本地代理**: http://localhost:3000（解决浏览器CORS问题）

**支持解读的内容类型**：
- 科研论文（PMID）→ 研究背景、实验设计、关键数据、机制
- BD交易 → 交易概况、战略意义、行业影响、风险提示
- 临床进展 → 临床概况、数据解读、竞争格局、上市前景
- 公司详情 → 整合相关BD/临床/论文/财报

**启动代理**：
```bash
cd /Users/nnn_nice/scripts/biotech-monitor
python3 proxy.py
```

## 关键设计决策

### 1. 数据按日期倒序排序
- 用户最关心的是最新进展
- `daily_update.py` 中的 `sort_by_date_desc()` 函数统一处理

### 2. AI 分析缓存机制
- 避免重复 API 调用（节省成本+速度）
- 缓存 key: `biotech_analysis_<pmid或title+date>`
- 存储位置: 浏览器 localStorage

### 3. 前端使用 localStorage 缓存
- 同一内容二次查看秒开
- 不依赖后端服务

### 4. 静态网站 + JSON 数据
- 部署在 GitHub Pages（免费、稳定）
- 无需服务器，零运维成本

## 常见问题排查

### 网站不更新
1. 检查 crontab: `crontab -l | grep biotech`
2. 查看日志: `tail logs/auto_update_*.log`
3. 手动运行: `bash auto_update.sh`

### AI 解读失败
1. 检查代理是否运行: `curl http://localhost:3000/health`
2. 重启代理: `lsof -ti :3000 | xargs kill -9; python3 proxy.py &`

### GitHub 推送失败
- 网络问题时会失败，日志会记录
- 下次运行时会自动重试

## 后续优化方向

- [ ] 添加新闻聚合到邮箱/飞书
- [ ] AI 分析结果持久化到服务端
- [ ] 添加更多公司监控
- [ ] 接入更多数据源（SEC文件、ClinicalTrials.gov）
- [ ] 移动端适配优化
- [ ] 多语言支持（英文版）

## 关键技术细节

### PubMed 抓取（collect_pubmed.py）
- 搜索最近7天的论文
- 5个分类：gene_editing, cell_therapy, adc, glp1, io
- 每个分类最多30篇
- 重点公司额外抓取（20篇）

### 论文摘要生成
- 提取研究背景、实验设计、关键数据、机制
- 100+ 模式匹配：疾病、表型、脑区、信号通路
- 量化数据提取（如 "<2%", "78倍"等）

### CORS 解决方案
- 浏览器不能直接调用 MiniMax API（CORS）
- 本地 Flask 代理（端口3000）作为中间层
- 代理自动添加 CORS headers

## 联系与维护

- **GitHub**: https://github.com/zhanghongling1010/biotech-monitor
- **本地目录**: /Users/nnn_nice/scripts/biotech-monitor
- **日志目录**: /Users/nnn_nice/scripts/biotech-monitor/logs

## 版本历史

- **v3.0 (2026-06-21)**: AI深度解读（论文/BD/临床/公司）、倒序排序、自动更新
- **v2.0 (2026-06)**: 多源数据集成、Daily brief渲染
- **v1.0 (2026-05)**: 基础数据展示
