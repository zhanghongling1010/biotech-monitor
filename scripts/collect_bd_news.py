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

# 完整翻译字典（短语优先）
TRANSLATIONS = {
    # 完整短语
    'strategic partnership': '战略合作',
    'T cell engagers': 'T细胞衔接器',
    'T cell engager': 'T细胞衔接器',
    'phase 3 trial': 'III期临床试验',
    'phase 2 trial': 'II期临床试验',
    'phase 1 trial': 'I期临床试验',
    'phase 3 study': 'III期临床研究',
    'phase 2 study': 'II期临床研究',
    'phase 1 study': 'I期临床研究',
    'breakthrough therapy': '突破性疗法',
    'clinical trial': '临床试验',
    'clinical data': '临床数据',
    'topline results': '主要试验结果',
    'interim analysis': '中期分析',
    'rare disease': '罕见病',
    'gene therapy': '基因治疗',
    'gene editing': '基因编辑',
    'cell therapy': '细胞治疗',
    'antibody drug conjugate': '抗体偶联药物',
    'anti-inflammatory': '抗炎',
    'manufacturing facility': '生产设施',
    'Series D': 'D轮融资',
    'Series C': 'C轮融资',
    'Series B': 'B轮融资',
    'Series A': 'A轮融资',
    'has invested': '投资',
    'invests': '投资',
    'invested': '投资',
    'boosts': '获得',
    'announced': '宣布',
    'announced plans': '公布计划',
    'expand': '扩展',
    'expansion': '扩展',
    'in China': '在中国',
    'in the Czech Republic': '在捷克共和国',
    'Czech Republic': '捷克共和国',
    # 公司名称
    'biogen': 'Biogen',
    'eli lilly': '礼来',
    'gsk': '葛兰素史克',
    'novartis': '诺华',
    'roche': '罗氏',
    'pfizer': '辉瑞',
    'merck': '默克',
    'bristol myers squibb': '百时美施贵宝',
    'johnson & johnson': '强生',
    'astrazeneca': '阿斯利康',
    'sanofi': '赛诺菲',
    'amgen': '安进',
    'regeneron': '再生元',
    'gilead': '吉利德',
    'moderna': 'Moderna',
    'vertex': '福泰制药',
    'jazz': 'Jazz制药',
    'novo nordisk': '诺和诺德',
    'abbvie': '艾伯维',
    'bayer': '拜耳',
    ' Boehringer': '勃林格殷格翰',
    ' BMS': 'BMS',
    'cellares': 'Cellares',
    'abcellera': 'AbCellera',
    'raythera': 'RayThera',
    # 技术词汇
    'car-t': 'CAR-T',
    'car t': 'CAR-T',
    'crispr': 'CRISPR',
    'base editing': '碱基编辑',
    'prime editing': '先导编辑',
    'adc': 'ADC',
    'bispecific': '双特异性抗体',
    'mrna': 'mRNA',
    'lnp': '脂质纳米颗粒',
    'glp-1': 'GLP-1',
    'pdl1': 'PD-L1',
    'pd-1': 'PD-1',
    'ctla-4': 'CTLA-4',
    # 疾病
    'cancer': '肿瘤',
    'tumor': '肿瘤',
    'oncology': '肿瘤学',
    'hemophilia': '血友病',
    'diabetes': '糖尿病',
    'obesity': '肥胖',
    'alzheimer': '阿尔茨海默病',
    'parkinson': '帕金森病',
    # 金额
    'billion': '亿美元',
    'million': '百万美元',
    '$': '美元',
    # 其他
    'acquisition': '收购',
    'acquire': '收购',
    'merger': '并购',
    'merges': '并购',
    'partnership': '合作',
    'collaboration': '合作',
    'licensing': '授权许可',
    'ipo': 'IPO上市',
    'funding': '融资',
    'raises': '融资',
    'secured': '获得',
    'secures': '获得',
    'milestone': '里程碑',
    'upfront': '预付款',
    'approval': '批准',
    'approved': '获批',
    'rejected': '被拒',
    'discontinues': '终止',
    'terminates': '终止',
    'pipeline': '研发管线',
    'drug candidate': '候选药物',
    'clinical stage': '临床阶段',
    'preclinical': '临床前',
    'phase': '期临床',
    'patient': '患者',
    'patients': '患者',
    'study': '研究',
    'studies': '研究',
    'trial': '试验',
    'trials': '试验',
    'data': '数据',
    'results': '结果',
    'efficacy': '有效性',
    'safety': '安全性',
    'secures': '获得',
    'expands': '扩展',
    'expansion': '扩展',
    'biotech': '生物技术公司',
    'biotechnology': '生物技术',
    'pharma': '制药',
    'pharmaceutical': '制药',
    'deal': '交易',
    'options': '期权',
    'receives': '获得',
    'receive': '获得',
    'to acquire': '收购',
    'to purchase': '收购',
    'raises': '融资',
    'raise': '融资',
}

def smart_translate(text):
    """智能翻译：优先匹配长词组，然后处理单词"""
    if not text:
        return ''
    result = text

    # 先处理HTML标签和特殊字符
    result = result.replace('<[^>]+>', '')
    result = result.replace('&amp;', '&')
    result = result.replace('&quot;', '"')
    result = result.replace('\n', ' ')
    result = result.replace('\r', ' ')

    # 按长度降序排列关键词，优先匹配最长词
    sorted_items = sorted(TRANSLATIONS.items(), key=lambda x: len(x[0]), reverse=True)
    for eng, cn in sorted_items:
        # 大小写不敏感替换
        pattern = eng
        result = result.replace(pattern, cn)
        result = result.replace(pattern.upper(), cn)
        result = result.replace(pattern.capitalize(), cn)

    # 清理多余空格
    while '  ' in result:
        result = result.replace('  ', ' ')

    # 修复常见问题
    result = result.replace('Biotech 生物', 'Biotech公司')
    result = result.replace('亿美元万美元', '亿美元')
    result = result.replace('百万美元万美元', '百万美元')

    return result.strip()

def translate_sentence(sentence):
    """翻译单个句子"""
    sentence = sentence.strip()
    if not sentence:
        return ''

    # 如果句子很短或几乎没有可翻译的词，直接返回原文
    if len(sentence.split()) < 3:
        return smart_translate(sentence)

    # 智能翻译
    translated = smart_translate(sentence)

    # 修复不流畅的地方
    translated = translated.replace('Biogen宣布收购Biogen', 'Biogen')

    return translated

def generate_chinese_summary(item):
    """为新闻生成详细的中文摘要 - 结构化展示交易信息"""
    title = item.get('title', '')
    desc = item.get('description', '')
    text = (title + ' ' + desc).lower()
    import re

    # ===== 交易类型识别 =====
    deal_type = ''
    if any(k in text for k in ['acquisition', 'merger', 'acquire', 'will pay']):
        deal_type = '收购/并购'
    elif any(k in text for k in ['partnership', 'collaboration', 'turns to']):
        deal_type = '战略合作'
    elif any(k in text for k in ['raises', 'series', 'boosts', 'secures', 'funded', 'investment']):
        deal_type = '融资'
    elif any(k in text for k in ['expands', 'expansion', 'invested', 'manufacturing', 'facility']):
        deal_type = '业务扩展'
    elif any(k in text for k in ['phase', 'clinical trial']):
        deal_type = '临床试验'
    elif any(k in text for k in ['approval', 'approved', 'fda', 'ema']):
        deal_type = '监管批准'
    elif any(k in text for k in ['stops', 'terminates', 'discontinues']):
        deal_type = '试验终止'

    # ===== 交易详情 =====
    details = []

    # 并购/收购
    if deal_type == '收购/并购':
        acquirer = ''
        acquired = ''
        amount = ''

        # 识别收购方
        company_list = {
            'biogen': '百健(Biogen)', 'eli lilly': '礼来', 'gsk': '葛兰素史克',
            'novartis': '诺华', 'roche': '罗氏', 'pfizer': '辉瑞', 'merck': '默克',
            'bristol myers squibb': '百时美施贵宝', 'johnson & johnson': '强生',
            'astrazeneca': '阿斯利康', 'sanofi': '赛诺菲', 'amgen': '安进',
            'regeneron': '再生元', 'gilead': '吉利德', 'moderna': 'Moderna',
            'vertex': '福泰制药', 'abbvie': '艾伯维', 'bayer': '拜耳'
        }
        for eng, cn in company_list.items():
            if eng in text:
                acquirer = cn
                break

        # 识别被收购方
        if 'raythera' in text:
            acquired = '生物技术公司RayThera（位于圣迭戈）'
        elif 'abcellera' in text:
            acquired = '抗体开发公司AbCellera'
        elif 'cellares' in text:
            acquired = '细胞疗法公司Cellares'
        else:
            acquired = '某生物技术公司'

        # 提取金额
        amount_match = re.search(r'\$?(\d+\.?\d*)\s*(billion|million)', text)
        if amount_match:
            val = float(amount_match.group(1))
            unit = '亿' if amount_match.group(2) == 'billion' else '百万'
            amount = f'{val}{unit}美元'

        # 识别领域
        field = ''
        if 'anti-inflammatory' in text or 'inflammatory' in text:
            field = '抗炎药物'
        elif 't cell engagers' in text or 'tce' in text:
            field = 'T细胞衔接器'
        elif 'gene editing' in text or 'crispr' in text:
            field = '基因编辑技术'
        elif 'cell therapy' in text or 'car-t' in text:
            field = '细胞治疗'

        # 构建详情
        if acquirer:
            details.append(f'{acquirer}将以最高{amount}收购{acquired}')
        if field:
            details.append(f'主要看中其{field}研发管线')
        if 'milestone' in text:
            details.append('大部分款项将根据研发里程碑支付')

    # 战略合作
    elif deal_type == '战略合作':
        partners = []
        company_list = {
            'jazz': 'Jazz制药', 'eli lilly': '礼来', 'gsk': '葛兰素史克',
            'novartis': '诺华', 'roche': '罗氏', 'pfizer': '辉瑞',
            'bristol myers squibb': '百时美施贵宝', 'astrazeneca': '阿斯利康',
            'sanofi': '赛诺菲', 'amgen': '安进', 'regeneron': '再生元'
        }
        for eng, cn in company_list.items():
            if eng in text and cn not in partners:
                partners.append(cn)

        amount_match = re.search(r'\$?(\d+\.?\d*)\s*(billion|million)', text)
        if amount_match:
            val = float(amount_match.group(1))
            unit = '亿' if amount_match.group(2) == 'billion' else '百万'
            amount = f'最高{val}{unit}美元'
        else:
            amount = '未披露'

        field = ''
        if 't cell engagers' in text:
            field = 'T细胞衔接器'
        elif 'crispr' in text or 'gene editing' in text:
            field = '基因编辑'
        elif 'adc' in text or 'antibody' in text:
            field = '抗体药物'

        if partners:
            details.append(f'{"与".join(partners)}达成{amount}美元战略合作')
        if field:
            details.append(f'合作领域：{field}')
        if '40 alliances' in text or 'partnership after partnership' in text:
            details.append('AbCellera已建立40余项生物制药合作')

    # 融资
    elif deal_type == '融资':
        company = ''
        if 'cellares' in text:
            company = '细胞疗法公司Cellares'
        elif 'novo nordisk' in text:
            company = '诺和诺德'
        elif 'moderna' in text:
            company = 'Moderna公司'

        amount_match = re.search(r'\$?(\d+\.?\d*)\s*(billion|million)', text)
        if amount_match:
            val = float(amount_match.group(1))
            unit = '亿' if amount_match.group(2) == 'billion' else '百万'
            amount = f'{val}{unit}美元'
        else:
            amount = '新一轮融资'

        round_match = re.search(r'Series\s+([A-Z])', text, re.IGNORECASE)
        round_name = f'{round_match.group(1).upper()}轮' if round_match else ''

        if company:
            if round_name:
                details.append(f'{company}完成{round_name}{amount}融资')
            else:
                details.append(f'{company}完成{amount}融资')

    # 业务扩展
    elif deal_type == '业务扩展':
        company = ''
        if 'novo nordisk' in text:
            company = '诺和诺德'
        elif 'eisai' in text:
            company = '卫材'
        elif 'siegfried' in text:
            company = 'Siegfried'

        amount_match = re.search(r'\$?(\d+\.?\d*)\s*(billion|million)', text)
        if amount_match:
            val = float(amount_match.group(1))
            unit = '亿' if amount_match.group(2) == 'billion' else '百万'
            amount = f'{val}{unit}美元'
        else:
            amount = ''

        location = ''
        if 'china' in text:
            location = '中国'
        elif 'czech' in text or 'bohumil' in text:
            location = '捷克共和国'

        if company and location and amount:
            details.append(f'{company}宣布投资{amount}在{location}扩建生产设施')
        elif company and location:
            details.append(f'{company}扩大在{location}的业务布局')
        elif company:
            details.append(f'{company}宣布业务扩展')

    # 临床试验
    elif deal_type == '临床试验':
        phase = ''
        for p in ['phase 3', 'phase 2', 'phase 1']:
            if p in text:
                phase_map = {'phase 3': 'III', 'phase 2': 'II', 'phase 1': 'I'}
                phase = phase_map[p]
                break

        company = ''
        if 'be bio' in text.replace(' ', ''):
            company = 'Be Bio'
        elif 'jazz' in text:
            company = 'Jazz制药'
        elif 'biogen' in text:
            company = 'Biogen'

        if 'stops' in text or 'terminates' in text:
            if company and phase:
                details.append(f'{company}终止其{phase}期临床试验')
            elif company:
                details.append(f'{company}终止某临床试验')
            else:
                details.append('某临床试验被终止')

            if 'hemophilia' in text:
                details.append('试验涉及血友病B基因治疗')
        elif phase:
            if company:
                details.append(f'{company}推进{phase}期临床试验')
            else:
                details.append(f'有药物正在推进{phase}期临床试验')

    # ===== 战略意义 =====
    significance = []

    if deal_type == '收购/并购':
        if 'secretive' in text or 'little about its pipeline' in text:
            significance.append('目标公司较为低调，管线信息披露有限')
        significance.append('收购方借此扩展其研发管线')
    elif deal_type == '战略合作':
        significance.append('有助于加速创新药物开发')
    elif deal_type == '融资':
        significance.append('表明投资者对该公司技术平台的信心')
    elif deal_type == '业务扩展':
        significance.append('显示公司对市场需求前景的看好')
    elif deal_type == '临床试验终止':
        significance.append('可能影响公司后续管线进展')

    # ===== 组装完整详情 =====
    result_parts = []
    if deal_type:
        result_parts.append(f'【交易类型】{deal_type}')

    if details:
        result_parts.append('【交易详情】' + '；'.join(details))

    if significance:
        result_parts.append('【战略意义】' + '；'.join(significance))

    cn_desc = '\n'.join(result_parts)

    # 标题保持英文
    cn_title = title

    # 简短摘要（用于列表预览）
    short_summary = cn_desc[:200].replace('\n', '；') + '...' if len(cn_desc) > 200 else cn_desc.replace('\n', '；')

    return short_summary, cn_title, cn_desc

def generate_paper_summary(paper):
    """为论文生成中文摘要"""
    title = paper.get('title', '')
    abstract = paper.get('abstract', '')

    # 翻译标题
    cn_title = smart_translate(title)

    # 翻译摘要
    if abstract:
        sentences = []
        import re
        parts = re.split(r'([.;,])', abstract)

        current = ''
        for i, part in enumerate(parts):
            if i % 2 == 0:
                current = part.strip()
            else:
                if current:
                    sentences.append(current + part)
                current = ''

        if current:
            sentences.append(current)

        cn_sentences = [translate_sentence(s) for s in sentences if len(s) > 10]
        cn_abstract = '。'.join(cn_sentences)
        if not cn_abstract.endswith('。'):
            cn_abstract += '。'
    else:
        cn_abstract = ''

    # 生成研究概要
    cn_title_lower = cn_title.lower()
    summary_parts = []

    if 'crispr' in cn_title_lower or 'gene editing' in cn_title_lower:
        summary_parts.append('基因编辑技术研究')
    elif 'car-t' in cn_title_lower or 'cell therapy' in cn_title_lower:
        summary_parts.append('细胞治疗研究')
    elif 'adc' in cn_title_lower or 'antibody' in cn_title_lower:
        summary_parts.append('抗体药物研究')
    elif 'glp-1' in cn_title_lower or 'diabetes' in cn_title_lower:
        summary_parts.append('代谢疾病研究')
    elif 'pd-1' in cn_title_lower or 'immunotherapy' in cn_title_lower:
        summary_parts.append('肿瘤免疫研究')

    if paper.get('journal'):
        summary_parts.append(f"发表在{paper['journal']}")

    cn_summary = '；'.join(summary_parts) if summary_parts else cn_title

    return cn_title, cn_abstract, cn_summary

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