# Biotech Monitor | 基因治疗行业日报

实时追踪基因编辑、细胞治疗、ADC、GLP-1等领域的最新动态。

## 功能特性

### 监控范围

#### 今日重点 (Critical Today)
- 重大BD/并购交易 (>1亿美元)
- 临床数据读出
- 监管批准/拒绝
- 高管变动

#### 每日简报 (Daily Brief)
- 新交易汇总
- 临床进展一览
- 科研新文速递

#### 专题追踪 (Deep Dives)
- 🧬 基因编辑 (CRISPR/Base/Prime Editing)
- 🔬 细胞治疗 (CAR-T/iPSC)
- 💉 ADC 抗体偶联药物
- ⚖️ GLP-1 / 代谢
- 🎯 肿瘤免疫 IO

#### 重点公司
- 国际: Beam, Verve, Tessera, Intellia, Editas, Prime Medicine 等
- 国内: 博雅基因, 邦耀生物, 纽福斯, 百济神州 等

#### 财报提醒
- 即将发布的季度财报日期

## 技术架构

```
biotech-monitor/
├── index.html          # 主页面
├── css/
│   └── style.css       # 样式
├── js/
│   └── main.js         # 前端逻辑
├── data/
│   └── daily/          # 每日JSON数据
│       └── latest.json # 最新数据
└── scripts/
    ├── collect_pubmed.py    # PubMed文献抓取
    ├── collect_news.py      # 临床试验/新闻抓取
    └── daily_update.py      # 数据汇总
```

## 部署

### 本地运行

1. 克隆仓库
```bash
cd ~/scripts/biotech-monitor
```

2. 安装依赖
```bash
pip install requests beautifulsoup4 lxml
```

3. 运行数据抓取
```bash
python scripts/collect_pubmed.py    # 抓取PubMed文献
python scripts/collect_news.py      # 抓取公司新闻
python scripts/daily_update.py     # 汇总数据
```

4. 本地预览
```bash
# 用Python启动简单服务器
python -m http.server 8080
# 打开 http://localhost:8080
```

### GitHub Pages 自动部署

1. Fork此仓库

2. 启用GitHub Actions (已配置)

3. 设置定时任务
```yaml
# .github/workflows/daily.yml
on:
  schedule:
    - cron: '0 0 * * *'  # 每天UTC 0点运行
```

## 数据来源

- **PubMed**: 文献检索 (E-utilities API)
- **ClinicalTrials.gov**: 临床试验
- **公司公告**: 财报日期

## 自定义

### 修改公司列表
编辑 `scripts/collect_news.py` 中的 `COMPANIES` 字典

### 修改搜索关键词
编辑 `scripts/collect_pubmed.py` 中的 `SEARCH_TERMS`

### 修改主题标签
编辑 `js/main.js` 中的 `categorize_article()` 函数

## License

MIT
