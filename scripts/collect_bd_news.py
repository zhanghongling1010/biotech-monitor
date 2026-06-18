#!/usr/bin/env python3
"""
Biotech Monitor - BD交易和公司新闻抓取
从Endpoints News、BioSpace等抓取BD/M&A、临床数据、公司动态
"""
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import json
import os
import re
import time
from collections import defaultdict

# ===== 配置 =====
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

# 目标新闻源
NEWS_SOURCES = {
    'endpoints': {
        'url': 'https://endpts.com/feed/',
        'type': 'rss'
    },
    'biospace': {
        'url': 'https://www.biospace.com/rss/news/',
        'type': 'rss'
    },
    'statnews': {
        'url': 'https://www.statnews.com/feed/',
        'type': 'rss'
    }
}

# ===== 监控范围=====

# 一、头部跨国药企
BIG_PHARMA = {
    'Roche': {'ticker': 'RHHBY', 'focus': 'Pharma'},
    'Novartis': {'ticker': 'NVS', 'focus': 'Pharma'},
    'Pfizer': {'ticker': 'PFE', 'focus': 'Pharma'},
    'Merck': {'ticker': 'MRK', 'focus': 'Pharma'},
    'Eli Lilly': {'ticker': 'LLY', 'focus': 'Pharma/GLP-1'},
    'Bristol Myers Squibb': {'ticker': 'BMY', 'focus': 'Pharma'},
    'Johnson & Johnson': {'ticker': 'JNJ', 'focus': 'Pharma'},
    'AstraZeneca': {'ticker': 'AZN', 'focus': 'Pharma/IO'},
    'GlaxoSmithKline': {'ticker': 'GSK', 'focus': 'Pharma'},
    'Amgen': {'ticker': 'AMGN', 'focus': 'Pharma'},
    'Novo Nordisk': {'ticker': 'NVO', 'focus': 'Metabolic/GLP-1'},
    'Sanofi': {'ticker': 'SNY', 'focus': 'Pharma'},
    'Moderna': {'ticker': 'MRNA', 'focus': 'mRNA'},
    'Gilead Sciences': {'ticker': 'GILD', 'focus': 'Virology/Cell Therapy'},
    'Regeneron': {'ticker': 'REGN', 'focus': 'Antibodies'},
}

# 二、基因治疗/编辑公司
GENE_THERAPY = {
    'Beam Therapeutics': {'ticker': 'BEAM', 'focus': 'Base/Prime Editing'},
    'Verve Therapeutics': {'ticker': 'VERV', 'focus': 'In Vivo Gene Editing'},
    'Tessera Therapeutics': {'ticker': 'TESS', 'focus': 'Gene Writing'},
    'Intellia Therapeutics': {'ticker': 'NTLA', 'focus': 'In Vivo CRISPR'},
    'Editas Medicine': {'ticker': 'EDIT', 'focus': 'In Vivo CRISPR'},
    'CRISPR Therapeutics': {'ticker': 'CRSP', 'focus': 'Ex Vivo CRISPR'},
    'Prime Medicine': {'ticker': 'PRME', 'focus': 'Prime Editing'},
    'Sangamo Therapeutics': {'ticker': 'SGMO', 'focus': 'Zinc Finger'},
    'uniQure': {'ticker': 'QURE', 'focus': 'AAV Gene Therapy'},
    'BioMarin': {'ticker': 'BMRN', 'focus': 'AAV Gene Therapy'},
    'PTC Therapeutics': {'ticker': 'PTCT', 'focus': 'Gene Therapy'},
    'Regenxbio': {'ticker': 'RGRX', 'focus': 'AAV Vector'},
    'Arbor Biotechnologies': {'ticker': 'ARBT', 'focus': 'CRISPR'},
    'Scribe Therapeutics': {'ticker': 'SCRIBE', 'focus': 'CRISPR Delivery'},
    'Metagenomi': {'ticker': 'MGEN', 'focus': 'In Vivo Gene Editing'},
    'LogicBio': {'ticker': 'LOGC', 'focus': 'Gene Therapy'},
    'Passage Bio': {'ticker': 'PASG', 'focus': 'AAV Gene Therapy'},
}

# 三、ADC药物公司
ADC_COMPANIES = {
    'Seagen': {'ticker': 'SGEN', 'focus': 'ADC'},
    'ImmunoGen': {'ticker': 'IMGN', 'focus': 'ADC'},
    'Daiichi Sankyo': {'ticker': 'DSEEY', 'focus': 'ADC'},
    'AstraZeneca': {'ticker': 'AZN', 'focus': 'ADC'},
    'Roche': {'ticker': 'RHHBY', 'focus': 'ADC'},
    'Pfizer': {'ticker': 'PFE', 'focus': 'ADC'},
    'ADC Therapeutics': {'ticker': 'ADCT', 'focus': 'ADC'},
    'Mersana': {'ticker': 'MRSN', 'focus': 'ADC'},
    'Sutro Biopharma': {'ticker': 'STRO', 'focus': 'ADC'},
    '吉利德': {'ticker': 'GILD', 'focus': 'ADC'},
}

# 四、GLP-1/代谢药物公司
GLP1_COMPANIES = {
    'Novo Nordisk': {'ticker': 'NVO', 'focus': 'GLP-1'},
    'Eli Lilly': {'ticker': 'LLY', 'focus': 'GLP-1'},
    'Structure Therapeutics': {'ticker': 'GPCR', 'focus': 'GLP-1'},
    'Veritas': {'ticker': 'MRNA', 'focus': 'mRNA/Metabolic'},
    'Siolta Therapeutics': {'focus': 'Microbiome'},
    'Axsome': {'ticker': 'AXSM', 'focus': 'CNS/Metabolic'},
}

# 五、细胞治疗/CAR-T
CELL_THERAPY = {
    'Novartis': {'ticker': 'NVS', 'focus': 'CAR-T'},
    'Gilead Sciences': {'ticker': 'GILD', 'focus': 'CAR-T (Yescarta)'},
    'Bristol Myers Squibb': {'ticker': 'BMY', 'focus': 'CAR-T'},
    'Johnson & Johnson': {'ticker': 'JNJ', 'focus': 'CAR-T'},
    'Legend Biotech': {'ticker': 'LEGN', 'focus': 'CAR-T'},
    'CARsgen Therapeutics': {'ticker': 'CAR', 'focus': 'CAR-T'},
    'Allogene': {'ticker': 'ALLO', 'focus': 'Allogeneic CAR-T'},
    'Celyad Oncology': {'ticker': 'CYAD', 'focus': 'CAR-T'},
    'Autolus': {'ticker': 'AUTL', 'focus': 'CAR-T'},
}

# 六、肿瘤免疫/IO
IO_COMPANIES = {
    'Merck': {'ticker': 'MRK', 'focus': 'Keytruda/IO'},
    'Bristol Myers Squibb': {'ticker': 'BMY', 'focus': 'Opdivo/IO'},
    'Roche': {'ticker': 'RHHBY', 'focus': 'Tecentriq/IO'},
    'AstraZeneca': {'ticker': 'AZN', 'focus': 'Imfinzi/IO'},
    'Pfizer': {'ticker': 'PFE', 'focus': 'IO'},
    'Regeneron': {'ticker': 'REGN', 'focus': 'Libtayo/IO'},
    'BeiGene': {'ticker': 'BGNE', 'focus': 'IO'},
    'Innovent Biologics': {'ticker': '1801.HK', 'focus': 'IO'},
}

# 七、国内头部 biotech
CHINA_BIOTECH = {
    '百济神州': {'code': '688235', 'focus': 'IO/Cell Therapy'},
    '君实生物': {'code': '688180', 'focus': 'IO/Antibody'},
    '信达生物': {'code': '1801.HK', 'focus': 'IO/Antibody'},
    '恒瑞医药': {'code': '600276', 'focus': 'Pharma'},
    '翰森制药': {'code': '3692.HK', 'focus': 'Pharma'},
    '和黄医药': {'code': '0013.HK', 'focus': 'Pharma'},
    '荣昌生物': {'code': '688331', 'focus': 'ADC'},
    '博雅基因': {'code': '688265', 'focus': 'Gene Editing'},
    '邦耀生物': {'code': '688321', 'focus': 'Gene Editing'},
    '纽福斯': {'code': '688222', 'focus': 'Gene Therapy'},
    '信念医药': {'code': '301047', 'focus': 'AAV Gene Therapy'},
    '科济药业': {'code': '2171.HK', 'focus': 'CAR-T'},
    '传奇生物': {'code': 'LEGN', 'focus': 'CAR-T'},
    '驯鹿生物': {'focus': 'CAR-T'},
    '复星凯特': {'focus': 'CAR-T'},
    '药明巨诺': {'code': '2126.HK', 'focus': 'CAR-T'},
}

# 合并所有公司关键词
ALL_COMPANIES = {}
for d in [BIG_PHARMA, GENE_THERAPY, ADC_COMPANIES, GLP1_COMPANIES, CELL_THERAPY, IO_COMPANIES, CHINA_BIOTECH]:
    ALL_COMPANIES.update(d)

# BD交易关键词
DEAL_KEYWORDS = [
    'partnership', 'collaboration', 'deal', 'acquisition', 'merger',
    'licensing', 'strategic', 'billion', 'million', 'option',
    '达成合作', '收购', '并购', '授权', '引进', 'BD'
]

# 临床数据关键词
CLINICAL_KEYWORDS = [
    'phase 1', 'phase 2', 'phase 3', 'clinical trial',
    'data readout', 'topline results', 'interim analysis',
    '有效性', '安全性', '临床数据', '试验结果'
]

# 监管关键词
REGULATORY_KEYWORDS = [
    'fda approval', 'ema approval', 'nmpa approval', 'cleared',
    'approved', 'rejected', 'breakthrough therapy',
    '获批', '批准', '拒绝', '优先审评'
]

# 中文翻译映射
TRANSLATIONS = {
    # 交易类型
    'strategic partnership': '达成战略合作',
    'partnership': '合作',
    'collaboration': '合作',
    'acquisition': '收购',
    'merger': '并购',
    'licensing deal': '授权许可交易',
    'licensing': '授权',
    'deal': '交易',
    # 融资
    'raises': '完成融资',
    'raises $': '完成',
    'million in': '融资金额',
    'billion in': '融资金额',
    'ipo': 'IPO上市',
    'series a': 'A轮',
    'series b': 'B轮',
    'series c': 'C轮',
    'funding': '融资',
    # 临床阶段
    'phase 3': 'III期临床',
    'phase 2': 'II期临床',
    'phase 1': 'I期临床',
    'clinical trial': '临床试验',
    'data readout': '数据公布',
    'topline results': '主要结果',
    'interim analysis': '中期分析',
    # 监管
    'fda approval': 'FDA批准',
    'ema approval': 'EMA批准',
    'receives approval': '获得批准',
    'approved': '获批',
    'rejected': '被拒/拒绝',
    'breakthrough therapy': '突破性疗法',
    # 公司类型
    'biotech': '生物科技公司',
    'biopharmaceutical': '生物制药公司',
    'pharmaceutical': '制药公司',
    # 技术
    'car-t': 'CAR-T细胞疗法',
    'car t': 'CAR-T',
    'gene therapy': '基因疗法',
    'gene editing': '基因编辑',
    'crispr': 'CRISPR',
    'base editing': '碱基编辑',
    'prime editing': '先导编辑',
    'adc': '抗体偶联药物',
    'bispecific': '双特异性抗体',
    'mrna': 'mRNA',
    'lnp': '脂质纳米颗粒',
    'glp-1': 'GLP-1',
    # 疾病
    'cancer': '肿瘤',
    'tumor': '肿瘤',
    'oncology': '肿瘤',
    'rare disease': '罕见病',
    'hemophilia': '血友病',
    'diabetes': '糖尿病',
    'obesity': '肥胖',
    # 金额
    'billion': '亿美元',
    'million': '万美元',
    # 其他
    'therapy': '疗法',
    'treatment': '治疗',
    'drug candidate': '候选药物',
    'drug': '药物',
    'patient': '患者',
    'study': '研究',
    'trial': '试验',
    'results': '结果',
    'data': '数据',
    'update': '更新',
    'stops': '停止',
    'terminates': '终止',
    'anti-inflammatory': '抗炎',
    ' T cell engagers': 'T细胞衔接器',
}

def translate_to_chinese(text):
    """将英文关键词翻译为中文"""
    if not text:
        return ''
    result = text

    # 按关键词长度排序（优先匹配长词）
    sorted_keywords = sorted(TRANSLATIONS.keys(), key=len, reverse=True)
    for kw in sorted_keywords:
        # 替换时不使用单词边界，直接替换（长词优先）
        result = result.replace(kw, TRANSLATIONS[kw])
        result = result.replace(kw.capitalize(), TRANSLATIONS[kw])
        result = result.replace(kw.upper(), TRANSLATIONS[kw])

    # 后处理：修复一些常见问题
    result = result.replace('T 细胞', 'T细胞')
    result = result.replace('细胞era', 'Cellera')  # 还原被误翻的公司名
    result = result.replace('Biotech 生物', 'Biotech/生物')

    return result

def generate_chinese_summary(item):
    """为新闻生成详细的中文摘要"""
    title = item.get('title', '')
    desc = item.get('description', '')[:500]
    text = title + ' ' + desc
    text_lower = text.lower()

    # 翻译标题
    cn_title = translate_to_chinese(title)

    # 生成详细的中文摘要
    summary_parts = []

    # 1. 判断交易类型并详细描述
    if any(k in text_lower for k in ['acquisition', 'merger', 'acquire']):
        # 提取买方和卖方
        if 'biogen' in text_lower:
            summary_parts.append('Biogen达成收购交易')
        elif 'eli lilly' in text_lower or 'lilly' in text_lower:
            summary_parts.append('Eli Lilly达成收购交易')
        elif 'gsk' in text_lower:
            summary_parts.append('GSK达成收购交易')
        elif 'novartis' in text_lower:
            summary_parts.append('Novartis达成收购交易')
        elif 'roche' in text_lower:
            summary_parts.append('Roche达成收购交易')
        elif 'pfizer' in text_lower:
            summary_parts.append('Pfizer达成收购交易')
        elif 'merck' in text_lower:
            summary_parts.append('Merck达成收购交易')
        else:
            summary_parts.append('某大型药企达成收购交易')

        # 提取金额
        import re
        billion_match = re.search(r'\$?(\d+\.?\d*)\s*billion', text_lower)
        million_match = re.search(r'\$?(\d+\.?\d*)\s*million', text_lower)
        if billion_match:
            summary_parts.append(f'交易金额约{billion_match.group(1)}亿美元')
        elif million_match:
            summary_parts.append(f'交易金额约{million_match.group(1)}百万美元')

    elif any(k in text_lower for k in ['partnership', 'collaboration']):
        if 'up to' in text_lower:
            import re
            amount_match = re.search(r'up to \$?(\d+\.?\d*)\s*(billion|million)', text_lower)
            if amount_match:
                amount = float(amount_match.group(1))
                unit = '亿' if amount_match.group(2) == 'billion' else '百万'
                summary_parts.append(f'战略合作、潜在交易金额最高达{amount}{unit}美元')
            else:
                summary_parts.append('达成战略合作')
        else:
            summary_parts.append('达成战略合作')

    elif any(k in text_lower for k in ['raises', 'ipo', 'funding', 'series a', 'series b', 'series c']):
        import re
        if 'raises' in text_lower or 'raised' in text_lower:
            amount_match = re.search(r'\$?(\d+\.?\d*)\s*(billion|million)', text_lower)
            if amount_match:
                amount = float(amount_match.group(1))
                unit = '亿' if amount_match.group(2) == 'billion' else '百万'
                summary_parts.append(f'完成{amount}{unit}美元融资')
        if 'ipo' in text_lower:
            summary_parts.append('进行IPO上市')

    elif any(k in text_lower for k in ['phase 3', 'phase 2', 'phase 1']):
        phase_map = {'phase 3': 'III', 'phase 2': 'II', 'phase 1': 'I'}
        for p, cn in phase_map.items():
            if p in text_lower:
                summary_parts.append(f'推进{cn}期临床试验')
                break
        if 'data' in text_lower or 'results' in text_lower:
            summary_parts.append('发布临床数据')

    elif any(k in text_lower for k in ['approval', 'approved', 'fda', 'ema', 'cleared']):
        summary_parts.append('获得监管机构批准')

    elif any(k in text_lower for k in ['data readout', 'topline results', 'interim analysis']):
        summary_parts.append('公布临床试验数据')

    elif any(k in text_lower for k in ['stops', 'terminates', 'discontinues']):
        summary_parts.append('临床试验终止')

    elif any(k in text_lower for k in ['anti-inflammatory', 'inflammatory']):
        summary_parts.append('涉及抗炎治疗领域')

    # 2. 提取涉及的公司
    companies = item.get('companies', [])
    if companies:
        summary_parts.append(f'涉及公司: {", ".join(companies[:3])}')

    # 3. 提取关键信息
    if 'milestone' in text_lower:
        summary_parts.append('包含里程碑付款')
    if 'upfront' in text_lower:
        summary_parts.append('有预付款')
    if 'rare disease' in text_lower or 'orphan' in text_lower:
        summary_parts.append('罕见病领域')

    cn_summary = '；'.join(summary_parts) if summary_parts else translate_to_chinese(desc[:150])

    return cn_summary, cn_title, translate_to_chinese(desc[:300])

def fetch_rss(url, source_name):
    """抓取RSS源"""
    print(f"  [{source_name}] 抓取RSS...")
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        content = response.content

        # 先尝试标准XML解析
        items = []
        try:
            root = ET.fromstring(content)
            items = parse_rss_items(root, source_name)
        except ET.ParseError:
            # XML解析失败，尝试用BeautifulSoup处理
            print(f"    XML解析失败，尝试HTML解析...")
            items = parse_rss_html(content, source_name)

        print(f"    获取 {len(items)} 条")
        return items
    except Exception as e:
        print(f"    错误: {e}")
        return []

def parse_rss_items(root, source_name):
    """解析RSS/Atom XML"""
    items = []

    # 尝试RSS格式
    for item in root.findall('.//item'):
        title = ''.join(t.text or '' for t in item.findall('title'))
        link = ''.join(l.text or '' for l in item.findall('link'))
        description = ''.join(d.text or '' for d in item.findall('description'))
        pub_date = ''.join(p.text or '' for p in item.findall('pubDate'))
        description = re.sub(r'<[^>]+>', '', description)[:300]

        items.append({
            'title': title.strip(),
            'link': link.strip(),
            'description': description.strip(),
            'pub_date': pub_date.strip(),
            'source': source_name
        })

    # 尝试Atom格式
    if not items:
        for entry in root.findall('.//entry'):
            title = ''.join(t.text or '' for t in entry.findall('title'))
            link = ''
            for l in entry.findall('link'):
                if l.get('rel') == 'alternate' or l.get('type') == 'text/html':
                    link = l.get('href', '')
            content = ''.join(c.text or '' for c in entry.findall('content'))
            content = re.sub(r'<[^>]+>', '', content)[:300]
            pub_date = ''.join(p.text or '' for p in entry.findall('published'))

            items.append({
                'title': title.strip(),
                'link': link.strip(),
                'description': content.strip(),
                'pub_date': pub_date.strip(),
                'source': source_name
            })

    return items

def parse_rss_html(content, source_name):
    """用BeautifulSoup解析损坏的XML"""
    items = []
    soup = BeautifulSoup(content, 'lxml')

    # 尝试找item或entry
    for item in soup.find_all(['item', 'entry']):
        title_elem = item.find(['title', 'dc:title'], recursive=True)
        title = title_elem.text if title_elem else ''

        link_elem = item.find(['link'], recursive=True)
        link = link_elem.get('href', '') or link_elem.text if link_elem else ''

        desc_elem = item.find(['description', 'summary', 'content', 'dc:description'], recursive=True)
        desc = desc_elem.text if desc_elem else ''
        desc = re.sub(r'<[^>]+>', '', desc)[:300]

        date_elem = item.find(['pubDate', 'published', 'updated', 'dc:date'], recursive=True)
        pub_date = date_elem.text if date_elem else ''

        items.append({
            'title': title.strip(),
            'link': link.strip(),
            'description': desc.strip(),
            'pub_date': pub_date.strip(),
            'source': source_name
        })

    return items

def classify_news(item):
    """对新闻进行分类"""
    text = (item.get('title', '') + ' ' + item.get('description', '')).lower()

    categories = []
    mentioned_companies = []

    # 检测公司（匹配所有分类）
    for company_name, info in ALL_COMPANIES.items():
        if company_name.lower() in text:
            ticker = info.get('ticker') or info.get('code') or company_name
            if ticker not in mentioned_companies:
                mentioned_companies.append(ticker)

    # 检测BD交易
    is_deal = any(kw in text for kw in DEAL_KEYWORDS)
    if is_deal:
        categories.append('deal')

    # 检测临床数据
    is_clinical = any(kw in text for kw in CLINICAL_KEYWORDS)
    if is_clinical:
        categories.append('clinical')

    # 检测监管
    is_regulatory = any(kw in text for kw in REGULATORY_KEYWORDS)
    if is_regulatory:
        categories.append('regulatory')

    # 重要性判断
    priority = 'normal'
    critical_keywords = ['acquisition', 'merger', 'fda approval', 'breakthrough', 'phase 3', 'billion', 'receives approval']
    if any(kw in text for kw in critical_keywords):
        priority = 'critical'

    # 公司类型标签
    company_type = None
    for company_name, info in ALL_COMPANIES.items():
        if company_name.lower() in text:
            company_type = info.get('focus', '')
            break

    return {
        'categories': categories,
        'companies': mentioned_companies,
        'priority': priority,
        'date': item.get('pub_date', ''),
        'company_type': company_type
    }

def filter_relevant(items, days_back=3):
    """过滤相关内容（整个生物医药行业）"""
    relevant_keywords = [
        # 治疗技术
        'gene therapy', 'gene editing', 'crispr', 'base editing', 'prime editing',
        'cell therapy', 'car-t', 'car t', 'adc', 'antibody drug conjugate',
        'bispecific', 'monoclonal antibody', 'mrna', 'lnp',
        'glp-1', 'wegovy', 'ozempic', 'mounjaro', 'tirzepatide',
        # 疾病领域
        'oncology', 'cancer', 'tumor', 'immunotherapy', 'io combo',
        'rare disease', 'orphan drug', 'genetic disease',
        'diabetes', 'obesity', 'metabolic',
        'neurology', 'alzheimer', 'parkinson',
        # 公司名称（大型药企和 biotech）
        'roche', 'novartis', 'pfizer', 'merck', 'lilly', 'bms', 'jnj',
        'astrazeneca', 'gsk', 'amgen', 'sanofi', 'gilead', 'regeneron',
        'novo nordisk', 'moderna', 'biogen', 'vertex',
        'beam', 'verve', 'intellia', 'editas', 'crispr therapeutics',
        'prme', 'ntla', 'edit', 'crsp', 'uniqure', 'biomarin',
        'seagen', 'immunozen', 'legend biotech', 'carsgen', '百济', '君实',
        # 商业模式
        'partnership', 'licensing deal', 'acquisition', 'merger', 'collaboration',
        'billion dollar', 'phase 3 trial', 'fda approval', 'ema approval',
        # 国内关键词
        '创新药', '生物医药', 'ADC', 'GLP', '细胞治疗', '基因治疗', '肿瘤免疫'
    ]

    filtered = []
    for item in items:
        text = (item.get('title', '') + ' ' + item.get('description', '')).lower()
        if any(kw in text for kw in relevant_keywords):
            filtered.append(item)

    return filtered

def collect_all_news():
    """收集所有新闻"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始抓取新闻...")

    all_items = []

    for source_name, config in NEWS_SOURCES.items():
        if config['type'] == 'rss':
            items = fetch_rss(config['url'], source_name)
            all_items.extend(items)
        time.sleep(1)  # 避免请求过快

    print(f"\n总共获取 {len(all_items)} 条原始新闻")

    # 过滤相关内容
    relevant_items = filter_relevant(all_items)
    print(f"过滤后 {len(relevant_items)} 条相关")

    # 分类
    classified = []
    for item in relevant_items:
        classification = classify_news(item)
        if classification['categories']:  # 只保留有明确分类的
            item.update(classification)
            # 添加中文翻译
            cn_summary, cn_title, cn_desc = generate_chinese_summary(item)
            item['title_cn'] = cn_title
            item['description_cn'] = cn_summary
            classified.append(item)

    return classified

def save_data(news_items, output_dir):
    """保存数据"""
    os.makedirs(output_dir, exist_ok=True)

    today = datetime.now().strftime('%Y-%m-%d')
    today_file = os.path.join(output_dir, f'news_{today}.json')

    data = {
        'timestamp': datetime.now().isoformat(),
        'items': news_items,
        'summary': {
            'total': len(news_items),
            'deals': len([i for i in news_items if 'deal' in i.get('categories', [])]),
            'clinical': len([i for i in news_items if 'clinical' in i.get('categories', [])]),
            'regulatory': len([i for i in news_items if 'regulatory' in i.get('categories', [])]),
        }
    }

    with open(today_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # 更新latest
    latest_file = os.path.join(output_dir, 'news_latest.json')
    with open(latest_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n数据已保存: {today_file}")
    return data

def main():
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'daily')
    news_items = collect_all_news()
    data = save_data(news_items, output_dir)

    print(f"\n统计:")
    print(f"  BD交易: {data['summary']['deals']}")
    print(f"  临床进展: {data['summary']['clinical']}")
    print(f"  监管动态: {data['summary']['regulatory']}")
    print("\n完成!")

if __name__ == '__main__':
    main()