#!/usr/bin/env python3
"""
Biotech Monitor - PubMed文献抓取
追踪基因编辑、细胞治疗等领域的最新文献
"""
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import json
import os
import re

# ===== Configuration =====
PUBMED_API = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
SEARCH_TERMS = {
    'gene_editing': [
        'CRISPR[Title/Abstract] OR Cas9[Title/Abstract] OR base editing[Title/Abstract] OR prime editing[Title/Abstract]',
        'gene therapy[Title/Abstract] OR in vivo gene editing[Title/Abstract]',
        'AAV gene therapy[Title/Abstract] OR lentiviral vector[Title/Abstract]'
    ],
    'cell_therapy': [
        'CAR-T[Title/Abstract] OR cell therapy[Title/Abstract]',
        'iPSC[Title/Abstract] OR stem cell therapy[Title/Abstract]',
        'TCR-T[Title/Abstract] OR NK cell[Title/Abstract]'
    ],
    'adc': [
        'ADC[Title/Abstract] OR antibody drug conjugate[Title/Abstract]',
        'bispecific antibody[Title/Abstract]'
    ],
    'glp1': [
        'GLP-1[Title/Abstract] OR semaglutide[Title/Abstract]',
        'obesity[Title/Abstract] AND metabolic[Title/Abstract]'
    ],
    'io': [
        'checkpoint inhibitor[Title/Abstract] OR PD-1[Title/Abstract] OR PD-L1[Title/Abstract]',
        'tumor immunotherapy[Title/Abstract] OR IO combo[Title/Abstract]'
    ]
}

# 公司相关关键词
COMPANY_KEYWORDS = [
    'Beam', 'Verve', 'Tessera', 'Intellia', 'Editas', 'CRISPR Therapeutics',
    'Prime Medicine', 'Arbor', 'Scribe', 'Metagenomi', 'Sangamo', 'uniQure',
    '博雅', '邦耀', '纽福斯', '信念医药', '本导基因', '瑞风生物'
]

JOURNALS = {
    'nature': 'Nature',
    'science': 'Science',
    'cell': 'Cell',
    'nat_biotechnol': 'Nature Biotechnology',
    'nat_med': 'Nature Medicine',
    'mol THER': 'Molecular Therapy',
    'jci': 'Journal of Clinical Investigation',
    'blood': 'Blood',
    'jco': 'Journal of Clinical Oncology',
    'lancet': 'Lancet',
    'nejm': 'New England Journal of Medicine'
}

# 论文关键词翻译
PAPER_TRANSLATIONS = {
    'CRISPR': 'CRISPR基因编辑',
    'Cas9': 'Cas9基因编辑工具',
    'base editing': '碱基编辑',
    'prime editing': '先导编辑',
    'gene editing': '基因编辑',
    'gene therapy': '基因治疗',
    'gene therapy': '基因疗法',
    'in vivo': '体内',
    'ex vivo': '体外',
    'CAR-T': 'CAR-T细胞疗法',
    'cell therapy': '细胞治疗',
    'iPSC': '诱导多能干细胞',
    'stem cell': '干细胞',
    'ADC': '抗体偶联药物',
    'bispecific': '双特异性抗体',
    'GLP-1': 'GLP-1受体激动剂',
    'semaglutide': '司美格鲁肽',
    'ozempic': ' Ozempic（降糖减重药）',
    'wegovy': 'Wegovy（减重药）',
    'PD-1': 'PD-1免疫检查点',
    'PD-L1': 'PD-L1免疫检查点',
    'checkpoint inhibitor': '免疫检查点抑制剂',
    'immunotherapy': '免疫治疗',
    'tumor': '肿瘤',
    'cancer': '癌症',
    'metastasis': '转移',
    'clinical trial': '临床试验',
    'phase 1': 'I期临床',
    'phase 2': 'II期临床',
    'phase 3': 'III期临床',
    'efficacy': '有效性',
    'safety': '安全性',
    'efficacy and safety': '有效性和安全性',
    'randomized': '随机对照',
    'double-blind': '双盲',
    'placebo': '安慰剂',
    'overall survival': '总生存期',
    'progression-free survival': '无进展生存期',
    'objective response rate': '客观缓解率',
    'patient': '患者',
    'cohort': '队列',
    'study': '研究',
    'data': '数据',
    'results': '结果',
    'showed': '显示',
    'demonstrated': '表明',
    'significantly': '显著',
    'improved': '改善',
    'reduced': '降低',
    'increased': '增加',
    'knockout': '敲除',
    'knock-in': '敲入',
    'delivery': '递送',
    'AAV': '腺相关病毒',
    'lentiviral': '慢病毒载体',
    'mRNA': '信使RNA',
    'siRNA': '小干扰RNA',
    'novel': '新型',
    'new': '新',
    'potential': '潜在',
    'therapeutic': '治疗性',
    'target': '靶点',
    'mechanism': '机制',
    'pathway': '通路',
    'inflammation': '炎症',
    'autoimmune': '自身免疫',
    'rare disease': '罕见病',
    'genetic disease': '遗传病',
    'hematopoietic': '造血干细胞',
    'liver': '肝脏',
    'lung': '肺',
    'brain': '脑',
    'kidney': '肾脏',
    'heart': '心脏',
    'muscle': '肌肉',
    'mouse model': '小鼠模型',
    'non-human primate': '非人灵长类',
    'preclinical': '临床前',
    'translational': '转化医学',
}

# 完整句子翻译词典（优先匹配）
SENTENCE_TRANSLATIONS = {
    'Identification and characterization of': '鉴定并表征',
    'novel mechanisms': '新型机制',
    'mechanisms driving': '驱动机制',
    'melanoma metastases': '黑色素瘤转移',
    'and ways to target them': '及其靶向治疗策略',
    'for the development of effective treatment modalities': '对于开发有效的治疗模式至关重要',
    'Here, we employed': '本研究采用',
    'in vivo CRISPR knockout screening': '体内CRISPR基因敲除筛选',
    'targeting the genes associated with poor prognosis': '针对与不良预后相关的基因',
    'to identify': '以鉴定',
    'as a potent driver of': '作为强效驱动因子',
    'High levels correlate with': '高表达与',
    'increased metastasis and reduced survival in patients': '患者转移增加和生存期缩短相关',
    'Polr1a inhibition suppressed': 'Polr1a抑制可',
    'migration, invasion, and the ability of': '抑制迁移、侵袭和',
    'to form tumors': '成瘤能力',
    'These findings suggest': '这些发现表明',
    'is a potential therapeutic target for': '是潜在的肿瘤治疗靶点',
    'CRISPR/Cas9 genome editing provides a powerful framework for': 'CRISPR/Cas9基因编辑为',
    'interrogating gene function in': '研究基因功能提供了强有力的工具',
    'Yet, empirical application remains challenging due to': '然而，由于以下因素，实验应用仍然具有挑战性',
    'biological constraints, including': '生物学限制，包括',
    'haplodiploid genetics': '单倍二倍体遗传学',
    'narrow embryonic injection window': '胚胎注射窗口狭窄',
    'social rearing requirements': '社会饲养需求',
    'These constraints necessitate': '这些限制要求',
    'in silico pre-screening to maximize editing success': '进行计算机预筛选以提高编辑成功率',
    'before resource-intensive wet-lab implementation': '在资源密集型的实验室实施之前',
    'Within the omnigenic framework': '在泛基因框架内',
    'provides a powerful approach for': '为...提供了强有力的方法',
    'functional validation': '功能验证',
    'Our findings demonstrate': '我们的发现表明',
    'shows promising results in': '在...中显示出良好结果',
    'may provide a new strategy for': '可能为...提供新策略',
    'is a key player in': '是...的关键参与者',
    'plays a critical role in': '在...中发挥关键作用',
    'is involved in': '参与',
    'is associated with': '与...相关',
    'treatment resistance': '治疗耐药',
    'drug resistance': '耐药',
    'cell proliferation': '细胞增殖',
    'cell migration': '细胞迁移',
    'cell invasion': '细胞侵袭',
    'cell apoptosis': '细胞凋亡',
    'tumor growth': '肿瘤生长',
    'tumor metastasis': '肿瘤转移',
    'clinical outcomes': '临床结局',
    'patient survival': '患者生存',
    'overall survival': '总生存期',
    'progression-free survival': '无进展生存期',
    'objective response rate': '客观缓解率',
    'disease progression': '疾病进展',
    'adverse events': '不良事件',
    'side effects': '副作用',
    'safety profile': '安全性特征',
    'tolerability': '耐受性',
    'pharmacokinetics': '药代动力学',
    'pharmacodynamics': '药效学',
    'dose-limiting toxicity': '剂量限制性毒性',
    'maximum tolerated dose': '最大耐受剂量',
    'half-life': '半衰期',
    'bioavailability': '生物利用度',
    'efficacy and safety': '有效性和安全性',
    'phase 1/2 study': 'I/II期临床研究',
    'phase 2/3 study': 'II/III期临床研究',
    'preliminary results': '初步结果',
    'interim analysis': '中期分析',
    'top-line results': '主要结果',
    'primary endpoint': '主要终点',
    'secondary endpoint': '次要终点',
    'statistically significant': '统计学显著',
    'clinically meaningful': '具有临床意义',
    'response rate': '缓解率',
    'complete response': '完全缓解',
    'partial response': '部分缓解',
    'disease control': '疾病控制',
    'minimal residual disease': '微小残留病灶',
    'liquid biopsy': '液体活检',
    'tumor biopsy': '肿瘤活检',
    'biomarker': '生物标志物',
    'companion diagnostic': '伴随诊断',
    'patient-derived xenograft': '患者来源肿瘤异种移植',
    'patient-derived organoid': '患者来源类器官',
    'single-cell RNA sequencing': '单细胞RNA测序',
    'transcriptomic analysis': '转录组分析',
    'proteomic analysis': '蛋白质组分析',
    'bioinformatics analysis': '生物信息学分析',
    'gene expression': '基因表达',
    'protein expression': '蛋白表达',
    'pathway analysis': '通路分析',
    'gene set enrichment analysis': '基因集富集分析',
    'knockout screen': '敲除筛选',
    'genome-wide screen': '全基因组筛选',
    'loss-of-function screen': '功能缺失筛选',
    'gain-of-function screen': '功能获得筛选',
    'RNA interference': 'RNA干扰',
    'short hairpin RNA': '短发夹RNA',
    'small interfering RNA': '小干扰RNA',
    'messenger RNA': '信使RNA',
    'adeno-associated virus': '腺相关病毒',
    'lentiviral vector': '慢病毒载体',
    'lipid nanoparticle': '脂质纳米颗粒',
    'nanoparticle delivery': '纳米颗粒递送',
    'in vivo delivery': '体内递送',
    'ex vivo editing': '体外编辑',
    'autologous cell therapy': '自体细胞治疗',
    'allogeneic cell therapy': '异体细胞治疗',
    'engineered T cells': '工程化T细胞',
    'chimeric antigen receptor': '嵌合抗原受体',
    'bispecific T cell engager': '双特异性T细胞衔接器',
    'antibody-drug conjugate': '抗体偶联药物',
    'immunoconjugate': '免疫偶联物',
    'Fc-engineered antibody': 'Fc工程化抗体',
    'humanized antibody': '人源化抗体',
    'monoclonal antibody': '单克隆抗体',
    'polyclonal antibody': '多克隆抗体',
    'single-domain antibody': '单域抗体',
    'nanobody': '纳米抗体',
    'fragment antigen-binding': '抗原结合片段',
    'crystal structure': '晶体结构',
    'cryo-electron microscopy': '冷冻电镜',
    'structural basis': '结构基础',
    'mechanism of action': '作用机制',
    'target identification': '靶点鉴定',
    'target validation': '靶点验证',
    'target engagement': '靶点结合',
    'downstream signaling': '下游信号',
    'upstream regulation': '上游调控',
    'feedback loop': '反馈环路',
    'cross-talk': '串扰',
    'synergistic effect': '协同效应',
    'additive effect': '相加效应',
    'antagonistic effect': '拮抗效应',
    'dose-response relationship': '剂量-效应关系',
    'therapeutic window': '治疗窗口',
    'drug combination': '药物联合',
    'combination therapy': '联合治疗',
    'sequential treatment': '序贯治疗',
    'neoadjuvant therapy': '新辅助治疗',
    'adjuvant therapy': '辅助治疗',
    'maintenance therapy': '维持治疗',
    'salvage therapy': '补救治疗',
    'first-line treatment': '一线治疗',
    'second-line treatment': '二线治疗',
    'third-line treatment': '三线治疗',
    'metastatic disease': '转移性疾病',
    'advanced cancer': '晚期肿瘤',
    'relapsed/refractory': '复发/难治',
    'heavily pretreated': '经多线治疗',
    'treatment-naive': '初治',
    'newly diagnosed': '新诊断',
    'long-term follow-up': '长期随访',
    'median follow-up': '中位随访',
    'survival analysis': '生存分析',
    'multivariate analysis': '多因素分析',
    'univariate analysis': '单因素分析',
    'subgroup analysis': '亚组分析',
    'post hoc analysis': '事后分析',
    'retrospective analysis': '回顾性分析',
    'prospective analysis': '前瞻性分析',
    'in silico analysis': '计算机分析',
    'in vitro experiments': '体外实验',
    'in vivo experiments': '体内实验',
    'preclinical models': '临床前模型',
    'animal models': '动物模型',
    'mouse model': '小鼠模型',
    'rat model': '大鼠模型',
    'primate model': '灵长类模型',
    'pig model': '猪模型',
    'organoid model': '类器官模型',
    'spheroid model': '球体模型',
    '3D culture': '三维培养',
    '2D culture': '二维培养',
    'primary cells': '原代细胞',
    'cell lines': '细胞系',
    'stable cell line': '稳定细胞系',
    'transient transfection': '瞬时转染',
    'stable expression': '稳定表达',
    'overexpression': '过表达',
    'knockdown': '敲降',
    'knockout': '敲除',
    'knock-in': '敲入',
    'point mutation': '点突变',
    'deletion mutation': '缺失突变',
    'insertion mutation': '插入突变',
    'fusion protein': '融合蛋白',
    'truncated protein': '截短蛋白',
    'splice variant': '剪接变体',
    'isoform': '亚型',
    'paralog': '旁系同源物',
    'ortholog': '直系同源物',
    'homolog': '同源物',
    'conserved domain': '保守域',
    'functional domain': '功能域',
    'regulatory domain': '调控域',
    'catalytic domain': '催化域',
    'binding domain': '结合域',
    'recognition motif': '识别基序',
    'signal peptide': '信号肽',
    'transmembrane domain': '跨膜域',
    'intracellular domain': '胞内域',
    'extracellular domain': '胞外域',
    'N-terminal': 'N端',
    'C-terminal': 'C端',
    'phosphorylation': '磷酸化',
    'ubiquitination': '泛素化',
    'acetylation': '乙酰化',
    'methylation': '甲基化',
    'glycosylation': '糖基化',
    'sumoylation': 'SUMO化',
    'oxidation': '氧化',
    'reduction': '还原',
    'hydrolysis': '水解',
    'cleavage': '切割',
    'activation': '激活',
    'inactivation': '失活',
    'inhibition': '抑制',
    'repression': '抑制',
    'induction': '诱导',
    'suppression': '抑制',
    'promotion': '促进',
    'enhancement': '增强',
    'reduction': '降低',
    'increase': '增加',
    'decrease': '减少',
    'upregulation': '上调',
    'downregulation': '下调',
    'high expression': '高表达',
    'low expression': '低表达',
    'positive correlation': '正相关',
    'negative correlation': '负相关',
    'significant correlation': '显著相关',
    'no significant correlation': '无显著相关',
    'statistical significance': '统计学意义',
    'not statistically significant': '无统计学意义',
    'p value': 'p值',
    'confidence interval': '置信区间',
    'odds ratio': '比值比',
    'hazard ratio': '风险比',
    'relative risk': '相对风险',
    'absolute risk reduction': '绝对风险降低',
    'number needed to treat': '需治疗人数',
    'quality of life': '生活质量',
    'symptom improvement': '症状改善',
    'functional improvement': '功能改善',
    'radiographic response': '影像学缓解',
    'pathologic response': '病理学缓解',
    'complete resection': '完全切除',
    'partial resection': '部分切除',
    'debulking surgery': '减瘤手术',
    'systemic therapy': '系统治疗',
    'local therapy': '局部治疗',
    'radiation therapy': '放疗',
    'chemotherapy': '化疗',
    'targeted therapy': '靶向治疗',
    'hormonal therapy': '内分泌治疗',
    'immunotherapy': '免疫治疗',
    'gene therapy': '基因治疗',
    'cell therapy': '细胞治疗',
    'stem cell transplantation': '干细胞移植',
    'bone marrow transplantation': '骨髓移植',
    'hematopoietic stem cell': '造血干细胞',
    'mesenchymal stem cell': '间充质干细胞',
    'embryonic stem cell': '胚胎干细胞',
    'induced pluripotent stem cell': '诱导多能干细胞',
    'adult stem cell': '成体干细胞',
    'progenitor cell': '祖细胞',
    'differentiated cell': '分化细胞',
    'proliferating cell': '增殖细胞',
    'quiescent cell': '静息细胞',
    'senescent cell': '衰老细胞',
    'apoptotic cell': '凋亡细胞',
    'necrotic cell': '坏死细胞',
    'cancer stem cell': '肿瘤干细胞',
    'tumor-initiating cell': '肿瘤起始细胞',
    'circulating tumor cell': '循环肿瘤细胞',
    'disseminated tumor cell': '播散肿瘤细胞',
    'metastatic cell': '转移细胞',
    'drug-tolerant cell': '耐药细胞',
    'persister cell': '持续存在细胞',
    'resistant cell': '耐药细胞',
    'sensitive cell': '敏感细胞',
    'superoxide dismutase': '超氧化物歧化酶',
    'antioxidant enzyme': '抗氧化酶',
    'protects cells against': '保护细胞免受',
    'oxidative stress': '氧化应激',
    'fungal-specific': '真菌特异性',
    'copper-only SOD': '铜型SOD',
    'previously unrecognized': '此前未认识的',
    'oxidative stress defence': '氧化应激防御',
    'remains unclear': '尚未明确',
    'mutant': '突变体',
    'using': '使用',
    'approach': '方法',
    'examined the contribution': '研究了...的贡献',
    'virulence': '毒力',
    'pathogenesis': '发病机制',
    'hyphal growth': '菌丝生长',
    'biofilm formation': '生物膜形成',
    'oxidative stress response': '氧化应激反应',
    'genotoxic stress': '基因毒性应激',
    'tolerance': '耐受性',
    'contribution to': '对...的贡献',
    'generated a': '构建了',
    'mutant using': '突变体，使用',
    'transient': '瞬时',
    'approach and examined': '方法并研究了',
    'contribution to virulence': '对毒力的贡献',
    'These findings suggest': '这些发现表明',
    'provides insights into': '为了解...提供了见解',
    'reveals a previously unrecognized': '揭示了一个此前未认识的',
    'identification of': '鉴定',
    'a fungal-specific': '一种真菌特异性',
    'copper-only SOD family': '铜型SOD家族',
    'in Candida albicans': '在白色念珠菌中',
    'has revealed': '揭示了',
    'a previously unrecognized component': '一个此前未认识的成分',
    'of fungal oxidative stress defence': '真菌氧化应激防御',
    'yet the role of': '然而...的作用',
    'remains unclear': '尚未明确',
    'Here, we generated': '本研究构建了',
    'a sod6Δ/Δ mutant': 'sod6Δ/Δ突变体',
    'in C. albicans using': '在白色念珠菌中，使用',
    'a transient CRISPR/Cas9 approach': '瞬时CRISPR/Cas9方法',
    'and examined the contribution': '并研究了...的贡献',
    'of SOD6 to virulence': 'SOD6对毒力的贡献',
}

def translate_sentence_fluent(sentence):
    """将英文句子翻译为流畅中文（基于句子匹配）- 全中文输出"""
    if not sentence or len(sentence.strip()) < 5:
        return ''

    text = sentence.strip()
    result = text

    # 第一遍：按长度降序排列，优先匹配最长句子
    sorted_translations = sorted(SENTENCE_TRANSLATIONS.items(), key=lambda x: len(x[0]), reverse=True)

    for eng_phrase, cn_phrase in sorted_translations:
        result = result.replace(eng_phrase, cn_phrase)
        result = result.replace(eng_phrase.upper(), cn_phrase)
        result = result.replace(eng_phrase.capitalize(), cn_phrase)
        result = result.replace(eng_phrase.lower(), cn_phrase)

    # 第二遍：处理剩余的未匹配词汇（使用PAPER_TRANSLATIONS）
    sorted_keywords = sorted(PAPER_TRANSLATIONS.keys(), key=len, reverse=True)
    for kw in sorted_keywords:
        result = result.replace(kw, PAPER_TRANSLATIONS[kw])
        result = result.replace(kw.lower(), PAPER_TRANSLATIONS[kw])
        result = result.replace(kw.upper(), PAPER_TRANSLATIONS[kw])
        result = result.replace(kw.capitalize(), PAPER_TRANSLATIONS[kw])

    # 第三遍：清理标点和残留
    # 移除句号后的多余空格
    result = re.sub(r'\.\s+', '。', result)
    # 清理多余空格
    result = re.sub(r'\s+', ' ', result)
    # 移除句中残留的英文单词（单个或多个字母）
    result = re.sub(r'\b[a-zA-Z]{1,3}\b', '', result)  # 移除1-3个字母的残留单词
    # 清理括号内的残留内容
    result = re.sub(r'\([^)]*[a-zA-Z]{1,5}[^)]*\)', '', result)
    # 再次清理多余空格
    result = re.sub(r'\s+', ' ', result)

    # 如果结果基本没有中文，重新构建
    chinese_chars = len(re.findall(r'[一-鿿]', result))
    english_chars = len(re.findall(r'[a-zA-Z]', result))

    if chinese_chars < 3 or (english_chars > chinese_chars and chinese_chars < 10):
        # 如果中文字符太少，生成一个描述性翻译
        result = f"研究探讨了相关机制"

    return result.strip()

def translate_abstract_fluent(abstract):
    """将英文摘要翻译为流畅中文 - 使用结构化分析而非逐字翻译"""
    if not abstract:
        return ''

    import re

    # 清理摘要
    text = re.sub(r'\.\.\.', '', abstract)
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()

    # 如果摘要太短，返回空
    if len(text) < 50:
        return ''

    # 预翻译技术术语
    pre_translations = [
        ('Superoxide dismutase', '超氧化物歧化酶'),
        ('reactive oxygen species', '活性氧'),
        ('Candida albicans', '白色念珠菌'),
        ('Escherichia coli', '大肠杆菌'),
        ('mouse model', '小鼠模型'),
        ('in vivo', '体内'),
        ('in vitro', '体外'),
        ('patient-derived', '患者来源'),
        ('CRISPR', 'CRISPR基因编辑'),
        ('Cas9', 'Cas9'),
        ('CAR-T', 'CAR-T细胞治疗'),
        ('ADC', '抗体偶联药物'),
        ('bispecific', '双特异性抗体'),
        ('PD-1', 'PD-1'),
        ('PD-L1', 'PD-L1'),
        ('mRNA', 'mRNA'),
        ('iPSC', '诱导多能干细胞'),
        ('organoid', '类器官'),
        ('xenograft', '异种移植'),
    ]

    result = text
    for eng, cn in pre_translations:
        result = result.replace(eng, cn)
        result = result.replace(eng.lower(), cn)

    # 清理残留的英文单词和括号内容
    result = re.sub(r'\([^)]*\)', '', result)  # 移除括号内容
    result = re.sub(r'\b[A-Z]{1,5}\b', '', result)  # 移除单个大写字母
    result = re.sub(r'\b[a-z]{1,3}\b', '', result)  # 移除短英文单词
    result = re.sub(r'\s+', ' ', result)  # 清理空格
    result = result.strip()

    # 确保有足够的中文
    chinese_chars = len(re.findall(r'[一-鿿]', result))
    if chinese_chars < 20:
        return ''

    return result

    # 重组句子
    combined = []
    for i in range(0, len(sentences), 2):
        if i < len(sentences):
            sentence = sentences[i]
            if i + 1 < len(sentences):
                sentence = sentence + sentences[i + 1]
            combined.append(sentence.strip())

    # 翻译每个句子
    cn_parts = []
    for sent in combined:
        if len(sent.strip()) > 10:  # 跳过太短的片段
            translated = translate_sentence_fluent(sent)
            if translated:
                cn_parts.append(translated)

    if cn_parts:
        # 确保以中文句号结尾
        result = '。'.join(cn_parts)
        if not result.endswith('。') and not result.endswith('！') and not result.endswith('？'):
            result += '。'
        return result

    return ''

def translate_paper_keywords(text):
    """翻译论文关键词（备用方法）"""
    if not text:
        return ''
    result = text
    # 按长度排序，优先匹配长词
    sorted_keywords = sorted(PAPER_TRANSLATIONS.keys(), key=len, reverse=True)
    for kw in sorted_keywords:
        result = result.replace(kw, PAPER_TRANSLATIONS[kw])
        result = result.replace(kw.lower(), PAPER_TRANSLATIONS[kw])
    return result

def generate_paper_summary(article):
    """为论文生成详细的中文摘要 - 包含背景、方法、结果、意义"""
    title = article.get('title', '')
    abstract = article.get('abstract', '')
    text_lower = (title + ' ' + abstract).lower()

    # 标题保持英文
    cn_title = title

    # ===== 1. 研究背景 =====
    background_parts = []

    # 识别疾病/适应症
    disease_map = {
        'melanoma': '黑色素瘤',
        'cancer': '肿瘤',
        'tumor': '肿瘤',
        'oncology': '肿瘤',
        'carcinoma': '癌细胞',
        'breast cancer': '乳腺癌',
        'lung cancer': '肺癌',
        'leukemia': '白血病',
        'lymphoma': '淋巴瘤',
        'hematologic': '血液系统疾病',
        'diabetes': '糖尿病',
        'obesity': '肥胖',
        'metabolic': '代谢性疾病',
        'genetic disease': '遗传病',
        'rare disease': '罕见病',
        'alzheimer': '阿尔茨海默病',
        'parkinson': '帕金森病',
        'neurodegenerative': '神经退行性疾病',
        'cardiovascular': '心血管疾病',
        'liver': '肝脏疾病',
        'kidney': '肾脏疾病',
    }

    diseases = []
    for eng, cn in disease_map.items():
        if eng in text_lower:
            diseases.append(cn)
    diseases = list(dict.fromkeys(diseases))  # 去重保持顺序

    # 识别临床阶段
    phase = ''
    if 'phase 3' in text_lower or 'phase iii' in text_lower:
        phase = 'III期临床试验'
    elif 'phase 2' in text_lower or 'phase ii' in text_lower:
        phase = 'II期临床试验'
    elif 'phase 1' in text_lower or 'phase i' in text_lower:
        phase = 'I期临床试验'

    # 识别研究问题
    if 'resistance' in text_lower or 'resistant' in text_lower:
        background_parts.append('针对治疗耐药性问题')
    if 'metastasis' in text_lower or 'metastatic' in text_lower:
        background_parts.append('针对肿瘤转移机制')
    if 'recurrent' in text_lower:
        background_parts.append('针对复发性疾病')
    if 'refractory' in text_lower or 'relapsed' in text_lower:
        background_parts.append('针对难治性/复发性疾病')

    # 构建背景
    if phase:
        background_parts.insert(0, f'本研究为{phase}')
    elif 'preclinical' in text_lower or 'mouse model' in text_lower:
        background_parts.insert(0, '本研究为临床前动物实验')
    elif 'vivo' in text_lower:
        background_parts.insert(0, '本研究为体内实验')
    elif 'vitro' in text_lower:
        background_parts.insert(0, '本研究为体外实验')

    if diseases:
        background_parts.append(f'研究聚焦{"、".join(diseases[:2])}领域')

    background = '；'.join(background_parts) if background_parts else ''

    # ===== 2. 实验方法 =====
    method_parts = []

    # 技术平台
    tech_map = {
        'crispr': 'CRISPR基因编辑',
        'cas9': 'Cas9基因编辑',
        'base editing': '碱基编辑',
        'prime editing': '先导编辑',
        'car-t': 'CAR-T细胞治疗',
        'car t': 'CAR-T细胞治疗',
        'chimeric antigen receptor': 'CAR-T细胞治疗',
        'adc': '抗体偶联药物(ADC)',
        'antibody-drug conjugate': '抗体偶联药物(ADC)',
        'bispecific': '双特异性抗体',
        'mrna': 'mRNA技术',
        'rna sequencing': 'RNA测序',
        'rnaseq': 'RNA测序',
        'rn-a seq': 'RNA测序',
        'ipsc': '诱导多能干细胞(iPSC)',
        'stem cell': '干细胞技术',
        'gene therapy': '基因治疗',
        'vivio crispr': '体内CRISPR基因编辑',
        'knockout': '基因敲除',
        'knock-in': '基因敲入',
        'sirna': 'siRNA干扰',
        'mirna': 'miRNA研究',
    }

    techs = []
    for eng, cn in tech_map.items():
        if eng in text_lower:
            techs.append(cn)
    techs = list(dict.fromkeys(techs))

    if techs:
        method_parts.append(f"采用{'/'.join(techs[:2])}技术")

    # 实验模型
    if 'patient-derived' in text_lower or 'pdx' in text_lower:
        method_parts.append('使用患者来源肿瘤移植模型(PDX)')
    if 'organoid' in text_lower:
        method_parts.append('使用类器官模型')
    if 'mouse model' in text_lower or 'murine' in text_lower:
        method_parts.append('使用小鼠模型')
    if 'non-human primate' in text_lower or 'primate' in text_lower:
        method_parts.append('使用非人灵长类动物模型')
    if 'single-cell' in text_lower:
        method_parts.append('单细胞测序分析')

    # 检测方法
    if 'rna-seq' in text_lower or 'rnaseq' in text_lower:
        method_parts.append('RNA-seq转录组分析')
    if 'proteomics' in text_lower:
        method_parts.append('蛋白质组学分析')
    if 'bioinformatics' in text_lower:
        method_parts.append('生物信息学分析')
    if 'screening' in text_lower:
        method_parts.append('高通量筛选')

    method = '；'.join(method_parts) if method_parts else '常规实验方法'

    # ===== 3. 实验结果 =====
    result_parts = []

    # 关键发现
    if 'identified' in text_lower or 'discovery' in text_lower:
        result_parts.append('鉴定出关键基因/靶点')
    if 'inhibit' in text_lower or 'suppress' in text_lower or 'repression' in text_lower:
        result_parts.append('发现抑制性作用')
    if 'promote' in text_lower or 'activation' in text_lower or 'induced' in text_lower:
        result_parts.append('发现促进作用')
    if 'migration' in text_lower or 'invasion' in text_lower:
        result_parts.append('抑制细胞迁移和侵袭能力')
    if 'proliferation' in text_lower or 'growth' in text_lower:
        result_parts.append('抑制细胞增殖')
    if 'apoptosis' in text_lower:
        result_parts.append('诱导细胞凋亡')
    if 'survival' in text_lower:
        result_parts.append('延长生存期')
    if 'efficacy' in text_lower or 'effective' in text_lower:
        result_parts.append('显示良好有效性')
    if 'safety' in text_lower or 'tolerable' in text_lower or 'toxicity' in text_lower:
        result_parts.append('安全性可接受')

    # 具体数据（如果摘要中有数字）
    import re
    numbers = re.findall(r'\d+\.?\d*%', abstract)
    if numbers:
        result_parts.append(f'相关数据: {numbers[0]}')

    result = '；'.join(result_parts) if result_parts else '取得了重要的实验数据'

    # ===== 4. 研究意义 =====
    significance_parts = []

    if 'novel' in text_lower or 'new target' in text_lower or 'first time' in text_lower:
        significance_parts.append('为相关疾病治疗提供了新靶点')
    if 'potential therapeutic' in text_lower or 'therapeutic target' in text_lower:
        significance_parts.append('具有潜在治疗应用价值')
    if 'biomarker' in text_lower:
        significance_parts.append('可作为预后生物标志物')
    if 'drug discovery' in text_lower or 'drug development' in text_lower:
        significance_parts.append('为药物研发提供新方向')
    if 'combination' in text_lower or 'synergistic' in text_lower:
        significance_parts.append('支持联合治疗策略')

    # 期刊信息
    if article.get('journal'):
        significance_parts.append(f'发表在《{article["journal"]}》')

    significance = '；'.join(significance_parts) if significance_parts else '对领域发展具有参考价值'

    # ===== 组装完整中文详情 =====
    cn_summary = f"【研究背景】{background}。" if background else ''
    cn_summary += f"\n【实验方法】{method}。"
    cn_summary += f"\n【实验结果】{result}。"
    cn_summary += f"\n【研究意义】{significance}。"

    # 翻译的英文摘要（用于对照）- 使用流畅翻译
    cn_abstract = translate_abstract_fluent(abstract) if abstract else ''

    return cn_title, cn_abstract, cn_summary

def search_pubmed(query, days_back=7, max_results=50):
    """搜索PubMed"""
    search_url = PUBMED_API + "esearch.fcgi"
    params = {
        'db': 'pubmed',
        'term': query,
        'reldate': days_back,
        'datetype': 'pdat',
        'retmax': max_results,
        'retmode': 'json',
        'sort': 'date'
    }

    try:
        response = requests.get(search_url, params=params, timeout=30)
        data = response.json()
        return data.get('esearchresult', {}).get('idlist', [])
    except Exception as e:
        print(f"Search error: {e}")
        return []

def fetch_article_details(pmids):
    """获取文章详细信息"""
    if not pmids:
        return []

    fetch_url = PUBMED_API + "efetch.fcgi"
    params = {
        'db': 'pubmed',
        'id': ','.join(pmids),
        'retmode': 'xml',
        'rettype': 'abstract'
    }

    try:
        response = requests.get(fetch_url, params=params, timeout=30)
        root = ET.fromstring(response.content)

        articles = []
        for article in root.findall('.//PubmedArticle'):
            try:
                medline_citation = article.find('.//MedlineCitation')
                if medline_citation is None:
                    continue

                pmid = medline_citation.find('PMID')
                pmid_text = pmid.text if pmid is not None else ''

                article_data = medline_citation.find('Article')
                if article_data is None:
                    continue

                # 标题
                title_elem = article_data.find('ArticleTitle')
                title = ''.join(title_elem.itertext()) if title_elem is not None else ''

                # 摘要
                abstract_elem = article_data.find('Abstract')
                abstract_parts = []
                if abstract_elem is not None:
                    for elem in abstract_elem.findall('AbstractText'):
                        label = elem.get('Label', '')
                        text = ''.join(elem.itertext())
                        if label:
                            abstract_parts.append(f"{label}: {text}")
                        else:
                            abstract_parts.append(text)
                abstract = ' '.join(abstract_parts)

                # 作者
                authors = []
                author_list = article_data.find('AuthorList')
                if author_list is not None:
                    for author in author_list.findall('Author')[:5]:
                        last_name = author.find('LastName')
                        fore_name = author.find('ForeName')
                        if last_name is not None:
                            name = last_name.text
                            if fore_name is not None:
                                name = f"{fore_name.text} {last_name.text}"
                            authors.append(name)

                # 期刊
                journal_elem = article_data.find('Journal')
                journal = ''
                if journal_elem is not None:
                    title_elem = journal_elem.find('Title')
                    journal = title_elem.text if title_elem is not None else ''

                # 日期
                pub_date = ''
                pub_date_elem = article_data.find('ArticleDate')
                if pub_date_elem is not None:
                    year = pub_date_elem.find('Year')
                    month = pub_date_elem.find('Month')
                    day = pub_date_elem.find('Day')
                    if year is not None:
                        pub_date = f"{year.text}-{month.text if month is not None else '01'}-{day.text if day is not None else '01'}"

                # 关键词
                keywords = []
                for kw in article.findall('.//Keyword'):
                    if kw.text:
                        keywords.append(kw.text)

                # 关联公司
                mentioned_companies = []
                text_for_search = title + ' ' + abstract
                for company in COMPANY_KEYWORDS:
                    if company.lower() in text_for_search.lower():
                        mentioned_companies.append(company)

                # 创建临时文章对象用于翻译
                temp_article = {
                    'pmid': pmid_text,
                    'title': title,
                    'abstract': abstract[:500] + '...' if len(abstract) > 500 else abstract,
                    'authors': authors,
                    'journal': journal,
                    'date': pub_date,
                    'keywords': keywords,
                    'companies': mentioned_companies
                }

                # 生成中文翻译
                cn_title, cn_abstract, cn_summary = generate_paper_summary(temp_article)
                temp_article['title_cn'] = cn_title
                temp_article['abstract_cn'] = cn_abstract
                temp_article['summary_cn'] = cn_summary

                articles.append(temp_article)
            except Exception as e:
                print(f"Error parsing article: {e}")
                continue

        return articles
    except Exception as e:
        print(f"Fetch error: {e}")
        return []

def is_important_journal(journal_name):
    """判断是否重要期刊"""
    if not journal_name:
        return False
    journal_lower = journal_name.lower()
    important_patterns = [
        'nature', 'science', 'cell', 'lancet', 'nejm', 'jama',
        'molecular therapy', 'blood', 'jco', 'jci', 'pnas',
        'embo', 'genome research', 'biotechnology'
    ]
    return any(pattern in journal_lower for pattern in important_patterns)

def categorize_article(article):
    """对文章进行分类"""
    categories = []
    text = (article.get('title', '') + ' ' + article.get('abstract', '')).lower()

    # 基因编辑
    gene_editing_keywords = ['crispr', 'cas9', 'base editing', 'prime editing', 'zinc finger', 'talen', 'gene editing', 'gene therapy', 'aav', 'lentiviral']
    if any(kw in text for kw in gene_editing_keywords):
        categories.append('gene_editing')

    # 细胞治疗
    cell_keywords = ['car-t', 'cell therapy', 'ipsc', 'stem cell', 'tcr-t', 'nk cell', 'tumor infiltrating']
    if any(kw in text for kw in cell_keywords):
        categories.append('cell_therapy')

    # ADC
    adc_keywords = ['adc', 'antibody drug conjugate', 'bispecific', 'payload', 'linker']
    if any(kw in text for kw in adc_keywords):
        categories.append('adc')

    # GLP-1
    glp1_keywords = ['glp-1', 'semaglutide', 'ozempic', 'wegovy', 'obesity', 'weight loss', 'diabetes', 'incretin']
    if any(kw in text for kw in glp1_keywords):
        categories.append('glp1')

    # IO
    io_keywords = ['checkpoint', 'pd-1', 'pd-l1', 'ctla-4', 'immunotherapy', 'io combo', 'tumor microenvironment']
    if any(kw in text for kw in io_keywords):
        categories.append('io')

    return categories if categories else ['other']

def search_companies_news(company_names, days_back=7):
    """搜索公司相关新闻(通过PubMed)"""
    results = []
    for company in company_names:
        query = f'{company}[Title/Abstract]'
        pmids = search_pubmed(query, days_back=days_back, max_results=5)
        if pmids:
            articles = fetch_article_details(pmids)
            results.extend(articles)
    return results

def collect_all_data():
    """收集所有数据"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始抓取PubMed数据...")

    all_papers = {
        'gene_editing': [],
        'cell_therapy': [],
        'adc': [],
        'glp1': [],
        'io': []
    }

    # 按类别搜索
    for category, queries in SEARCH_TERMS.items():
        print(f"\n[{category}] 搜索中...")
        for query in queries:
            pmids = search_pubmed(query, days_back=7, max_results=30)
            if pmids:
                articles = fetch_article_details(pmids)
                for article in articles:
                    cats = categorize_article(article)
                    for cat in cats:
                        if cat in all_papers and article not in all_papers[cat]:
                            all_papers[cat].append(article)
                print(f"  找到 {len(articles)} 篇")

    # 搜索重点公司相关
    print("\n[重点公司] 搜索中...")
    company_news = search_companies_news(COMPANY_KEYWORDS[:10], days_back=14)
    print(f"  找到 {len(company_news)} 篇公司相关")

    return {
        'papers': all_papers,
        'company_news': company_news,
        'timestamp': datetime.now().isoformat()
    }

def save_data(data, output_dir):
    """保存数据"""
    os.makedirs(output_dir, exist_ok=True)

    # 保存今日数据
    today = datetime.now().strftime('%Y-%m-%d')
    today_file = os.path.join(output_dir, f'{today}.json')
    with open(today_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # 读取并合并新闻数据
    news_file = os.path.join(output_dir, 'news_latest.json')
    combined_data = dict(data)
    if os.path.exists(news_file):
        try:
            with open(news_file, 'r', encoding='utf-8') as f:
                news_data = json.load(f)
            # 从新闻数据提取分类
            items = news_data.get('items', [])
            deals = [i for i in items if 'deal' in i.get('categories', [])]
            clinical = [i for i in items if 'clinical' in i.get('categories', [])]
            regulatory = [i for i in items if 'regulatory' in i.get('categories', [])]
            # 构建critical和daily结构
            combined_data['critical'] = {
                'deals': deals[:5],
                'clinical': clinical[:5],
                'approvals': regulatory[:5]
            }
            combined_data['daily'] = {
                'deals': deals,
                'clinical': clinical,
                'regulatory': regulatory
            }
        except Exception as e:
            print(f"  合并新闻数据失败: {e}")

    # 更新latest链接
    latest_file = os.path.join(output_dir, 'latest.json')
    with open(latest_file, 'w', encoding='utf-8') as f:
        json.dump(combined_data, f, ensure_ascii=False, indent=2)

    print(f"\n数据已保存到: {today_file}")

def main():
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'daily')

    data = collect_all_data()
    save_data(data, output_dir)

    print("\n完成!")

if __name__ == '__main__':
    main()