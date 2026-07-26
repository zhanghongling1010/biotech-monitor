#!/usr/bin/env python3
"""
Biotech Monitor - 论文排序评分模块
按 相关度(关键词匹配) + 期刊影响因子 对论文综合排序
被 daily_update.py 调用
"""
import math
import re
from datetime import datetime, timedelta

# ===== 期刊影响因子表 (2024-2025 JCR 近似值,按常用刊收录) =====
# key 为规范化刊名(小写、去标点),匹配时先精确后包含
JOURNAL_IF = {
    # 顶刊
    'nature': 48.5, 'science': 44.7, 'cell': 45.5,
    'new england journal of medicine': 96.2, 'nejm': 96.2,
    'lancet': 98.4, 'jama': 63.1, 'bmj': 93.6,
    # Nature 子刊
    'nature biotechnology': 33.1, 'nature medicine': 58.7,
    'nature genetics': 31.7, 'nature biomedical engineering': 26.8,
    'nature nanotechnology': 38.1, 'nature materials': 37.2,
    'nature chemical biology': 12.9, 'nature methods': 36.1,
    'nature communications': 14.7, 'nature immunology': 27.7,
    'nature cancer': 23.5, 'nature metabolism': 20.8,
    'nature reviews drug discovery': 122.7, 'nature reviews genetics': 39.1,
    'nature reviews cancer': 72.5, 'nature reviews molecular cell biology': 81.3,
    'nature reviews immunology': 67.7, 'nature structural molecular biology': 15.7,
    'nature cell biology': 17.3,
    # Cell 子刊
    'cancer cell': 48.8, 'cell stem cell': 19.8, 'cell metabolism': 27.7,
    'cell reports': 7.5, 'cell reports medicine': 11.7,
    'cell research': 28.1, 'immunity': 25.5, 'molecular cell': 14.5,
    'cell genomics': 8.3, 'cell systems': 9.2,
    # 转化医学/临床
    'science translational medicine': 15.8, 'journal of clinical investigation': 13.3,
    'jci insight': 6.3, 'journal of clinical oncology': 42.1,
    'lancet oncology': 41.3, 'jama oncology': 22.5,
    'lancet haematology': 15.4, 'lancet diabetes endocrinology': 44.0,
    'cancer discovery': 29.7, 'annals of oncology': 56.7,
    'blood': 21.0, 'leukemia': 11.4, 'haematologica': 8.2,
    # 基因/细胞治疗专业刊
    'molecular therapy': 12.4, 'molecular therapy nucleic acids': 6.5,
    'molecular therapy methods clinical development': 4.7,
    'molecular therapy oncolytics': 4.2,
    'human gene therapy': 3.8, 'gene therapy': 4.3,
    'the crispr journal': 3.3, 'crispr journal': 3.3,
    'journal of gene medicine': 2.8,
    'nucleic acids research': 16.6, 'genome biology': 10.1,
    'genome medicine': 11.2, 'genome research': 7.0,
    'american journal of human genetics': 8.1,
    'human molecular genetics': 3.5, 'european journal of human genetics': 3.7,
    'genetics in medicine': 6.6,
    'stem cell research therapy': 7.5, 'cytotherapy': 4.5,
    'stem cells translational medicine': 6.0, 'stem cell reports': 5.9,
    # 肿瘤免疫
    'journal for immunotherapy of cancer': 10.3,
    'cancer immunology research': 8.2, 'oncimmunology': 6.3,
    'science immunology': 17.6, 'journal of immunology': 3.9,
    'frontiers in immunology': 5.7, 'cancer research': 12.5,
    'clinical cancer research': 10.4, 'molecular cancer': 27.7,
    'journal of hematology oncology': 29.5,
    'signal transduction and targeted therapy': 40.8,
    'mabs': 5.6, 'antibody therapeutics': 3.5,
    # 递送/材料/药剂
    'advanced materials': 27.4, 'advanced drug delivery reviews': 15.2,
    'journal of controlled release': 10.5, 'biomaterials': 12.8,
    'acs nano': 15.8, 'nano letters': 9.6, 'small': 13.0,
    'acs applied materials interfaces': 8.3, 'pharmaceutics': 4.9,
    'international journal of pharmaceutics': 5.3,
    'molecular pharmaceutics': 4.5, 'drug delivery': 6.5,
    'expert opinion on drug delivery': 5.0,
    'advanced healthcare materials': 9.6, 'bioactive materials': 18.0,
    'acta biomaterialia': 9.7, 'nanomedicine': 4.7,
    # GLP-1/代谢
    'diabetes': 6.2, 'diabetes care': 14.8, 'diabetes obesity and metabolism': 5.4,
    'obesity': 4.2, 'metabolism': 9.8, 'lancet diabetes & endocrinology': 44.0,
    # 综合/其他常见
    'pnas': 9.4, 'proceedings of the national academy of sciences': 9.4,
    'science advances': 11.7, 'elife': 6.4, 'plos biology': 7.8,
    'plos medicine': 10.5, 'plos genetics': 4.0, 'plos one': 2.9,
    'embo journal': 9.4, 'embo reports': 6.5, 'embo molecular medicine': 9.0,
    'international journal of molecular sciences': 4.9, 'cancers': 4.5,
    'scientific reports': 3.8, 'journal of biological chemistry': 4.0,
    'jacc basic to translational science': 8.4,
    'european heart journal': 37.6, 'circulation': 35.5,
    'gastroenterology': 25.7, 'hepatology': 12.9, 'journal of hepatology': 26.8, 'gut': 23.0,
    'drug discovery today': 6.5, 'trends in biotechnology': 11.3,
    'trends in molecular medicine': 12.8, 'current opinion in biotechnology': 7.1,
    'biotechnology advances': 12.1, 'acs chemical biology': 3.5,
    'journal of medicinal chemistry': 6.8, 'european journal of medicinal chemistry': 5.9,
    'bioorganic medicinal chemistry': 3.0,
    'medical oncology': 2.8, 'drug delivery and translational research': 5.7,
    'journal of the american chemical society': 14.4, 'jacs': 14.4,
    'angewandte chemie': 16.1,
}

# ===== 各类别核心关键词(相关度评分用) =====
CATEGORY_KEYWORDS = {
    'gene_editing': ['crispr', 'cas9', 'cas12', 'cas13', 'base editing', 'prime editing',
                     'gene editing', 'gene therapy', 'genome editing', 'talen', 'zinc finger',
                     'aav', 'lentiviral', 'epigenome editing', 'base editor'],
    'cell_therapy': ['car-t', 'car t', 'cell therapy', 'car-nk', 'tcr-t', 'tcr',
                     'ipsc', 'stem cell', 'nk cell', 'til', 'tumor infiltrating',
                     'msc', 'mesenchymal', 'allogeneic', 'autologous'],
    'adc': ['adc', 'antibody-drug conjugate', 'antibody drug conjugate', 'payload',
            'linker', 'bispecific', 'monoclonal antibody'],
    'glp1': ['glp-1', 'glp1', 'semaglutide', 'tirzepatide', 'liraglutide',
             'obesity', 'weight loss', 'incretin', 'gip', 'glucagon'],
    'io': ['pd-1', 'pd-l1', 'ctla-4', 'checkpoint', 'immunotherapy', 'immune checkpoint',
           'tumor microenvironment', 'lag-3', 'tim-3', 'tigit', 'cancer vaccine'],
    'delivery_systems': ['lnp', 'lipid nanoparticle', 'nanoparticle', 'aav', 'exosome',
                         'delivery', 'viral vector', 'adeno-associated', 'liposome',
                         'mrna delivery', 'targeted delivery', 'vlp', 'virus-like particle'],
}

# ===== 顶刊保证名单:这些期刊的论文永远排在最前,确保必推送 =====
TOP_TIER_JOURNALS = {
    'nature', 'science', 'cell',
    'new england journal of medicine', 'nejm', 'lancet', 'jama', 'bmj',
    'nature biotechnology', 'nature medicine', 'nature genetics',
    'nature biomedical engineering', 'nature nanotechnology',
    'nature methods', 'nature cancer',
    'cell stem cell', 'cancer cell', 'cell metabolism', 'cell research',
    'science translational medicine', 'science immunology',
    'lancet oncology', 'lancet haematology', 'lancet diabetes endocrinology',
    'journal of clinical oncology', 'cancer discovery',
}

# 高价值信号词(额外加分:临床/人体/突破)
BONUS_TERMS = ['clinical trial', 'phase 1', 'phase 2', 'phase 3', 'first-in-human',
               'patient', 'in vivo', 'breakthrough', 'fda']


def _normalize_journal(name):
    return re.sub(r'[^a-z0-9 ]', '', (name or '').lower()).strip()


def get_impact_factor(journal):
    """查影响因子,先精确匹配,再包含匹配;查不到返回 None"""
    if not journal:
        return None
    jn = _normalize_journal(journal)
    # PubMed 刊名常带副标题,如 "Molecular therapy : the journal of..."
    jn = re.sub(r'\s+', ' ', jn)
    if jn in JOURNAL_IF:
        return JOURNAL_IF[jn]
    # 包含匹配:找表中最长的能作为前缀/子串命中的刊名
    best = None
    for k, v in JOURNAL_IF.items():
        if jn.startswith(k) or (len(k) >= 8 and k in jn):
            if best is None or len(k) > len(best[0]):
                best = (k, v)
    return best[1] if best else None


def relevance_score(paper, category):
    """相关度评分:标题命中权重高,摘要次之,临床/突破性信号加分,近期加分"""
    title = (paper.get('title') or '').lower()
    abstract = (paper.get('abstract') or '').lower()
    score = 0.0
    for kw in CATEGORY_KEYWORDS.get(category, []):
        if kw in title:
            score += 4.0
        elif kw in abstract:
            score += 1.0
    text = title + ' ' + abstract
    for kw in BONUS_TERMS:
        if kw in text:
            score += 1.5
    # 近期加分(3天内+2,7天内+1)
    try:
        d = datetime.strptime((paper.get('date') or '')[:10], '%Y-%m-%d')
        age = (datetime.now() - d).days
        if age <= 3:
            score += 2.0
        elif age <= 7:
            score += 1.0
    except (ValueError, TypeError):
        pass
    return score


def if_score(impact_factor):
    """影响因子归一化到 0-10(log 标度,IF=50 满分)"""
    if not impact_factor:
        return 3.0  # 未收录期刊给基础分,不歧视但也不加分
    return min(math.log1p(impact_factor) / math.log1p(50), 1.0) * 10.0


def composite_score(paper, category):
    """综合分 = 相关度*0.55 + 影响因子分*0.45"""
    rel = relevance_score(paper, category)
    impact = get_impact_factor(paper.get('journal'))
    ifs = if_score(impact)
    total = rel * 0.55 + ifs * 0.45
    return round(total, 2), round(rel, 2), impact


def is_top_tier(journal):
    """是否顶刊保证名单(CNS/NEJM/Lancet/JAMA 及大子刊)。
    仅精确匹配(去掉 'the' 前缀和 ':' 副标题后),避免 Cell Reports/
    Nature Communications 等被 'cell'/'nature' 前缀误伤"""
    if not journal:
        return False
    main = str(journal).split(':')[0]
    jn = re.sub(r'\s+', ' ', _normalize_journal(main))
    jn = re.sub(r'^the ', '', jn)
    return jn in TOP_TIER_JOURNALS


def sort_papers_by_score(papers, category):
    """排序:顶刊保证名单永远置顶(内部按综合分),其余按综合分降序。
    评分写回 paper 字段供前端展示"""
    pinned = []
    rest = []
    for p in papers:
        total, rel, impact = composite_score(p, category)
        p['composite_score'] = total
        p['relevance_score'] = rel
        p['impact_factor'] = impact
        p['top_tier'] = is_top_tier(p.get('journal'))
        (pinned if p['top_tier'] else rest).append(p)
    key = lambda x: (x['composite_score'], x.get('date', ''))
    pinned.sort(key=key, reverse=True)
    rest.sort(key=key, reverse=True)
    return pinned + rest
