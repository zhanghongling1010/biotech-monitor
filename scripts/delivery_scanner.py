#!/usr/bin/env python3
"""
LNP/体内递送系统专门扫描器
从 PubMed 抓取最新进展
"""
import requests
import json
import re
import time
import os
from datetime import datetime, timedelta

PUBMED_API = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

# 检索策略（多个 query 覆盖不同递送技术）
SEARCH_QUERIES = [
    # LNP 相关
    ('lipid nanoparticle mRNA delivery', 'lipid nanoparticle'),
    ('lipid nanoparticle gene therapy', 'lipid nanoparticle'),
    ('LNP in vivo CRISPR', 'lipid nanoparticle'),

    # AAV 相关
    ('AAV gene therapy clinical', 'aav'),
    ('adeno-associated virus vector 2026', 'aav'),
    ('AAV manufacturing production', 'aav'),

    # 其他递送
    ('exosome drug delivery', 'exosome'),
    ('virus-like particle VLP therapeutic', 'vlp'),
    ('nanoparticle targeted delivery gene', 'nanoparticle'),
    ('electroporation in vivo CRISPR', 'electroporation'),

    # 临床转化
    ('gene therapy in vivo delivery 2026', 'in_vivo'),
    ('CRISPR delivery therapeutic', 'crispr_delivery'),
]

# 关键词分类
DELIVERY_TYPES = {
    'lnp': [r'\bLNP\b', r'lipid nanoparticle', r'lipid nano'],
    'aav': [r'\bAAV\b', r'adeno-associated'],
    'exosome': [r'exosome', r'外泌体'],
    'vlp': [r'virus.like particle', r'\bVLP\b'],
    'nanoparticle': [r'nanoparticle', r'纳米'],
    'electroporation': [r'electroporation', r'电穿孔'],
    'lentivirus': [r'lentivir', r'慢病毒'],
    'adenovirus': [r'adenovirus', r'腺病毒'],
}


def search_pubmed(query, days_back=14, max_results=30):
    """PubMed 搜索"""
    try:
        params = {
            'db': 'pubmed',
            'term': query,
            'reldate': days_back,
            'datetype': 'pdat',
            'retmax': max_results,
            'retmode': 'json',
            'sort': 'date'
        }
        resp = requests.get(f"{PUBMED_API}/esearch.fcgi", params=params, timeout=30)
        data = resp.json()
        return data.get('esearchresult', {}).get('idlist', [])
    except Exception as e:
        print(f"Search error: {e}")
        return []


def fetch_details(pmids):
    """获取论文详情"""
    if not pmids:
        return []
    try:
        resp = requests.get(
            f"{PUBMED_API}/esummary.fcgi",
            params={'db': 'pubmed', 'id': ','.join(pmids), 'retmode': 'json'},
            timeout=30
        )
        data = resp.json()
        result = data.get('result', {})
        papers = []
        for pmid in pmids:
            if pmid in result:
                p = result[pmid]
                papers.append({
                    'pmid': pmid,
                    'title': p.get('title', ''),
                    'authors': [a.get('name', '') for a in p.get('authors', [])][:5],
                    'journal': p.get('fulljournalname', '') or p.get('source', ''),
                    'date': p.get('pubdate', ''),
                    'abstract': '',  # 需要再获取
                })
        return papers
    except Exception as e:
        print(f"Fetch error: {e}")
        return []


def fetch_abstracts(pmids):
    """获取摘要"""
    if not pmids:
        return {}
    try:
        resp = requests.get(
            f"{PUBMED_API}/efetch.fcgi",
            params={'db': 'pubmed', 'id': ','.join(pmids), 'retmode': 'xml'},
            timeout=30
        )
        abstracts = {}
        text = resp.text
        for pmid in pmids:
            m = re.search(rf'<PMID[^>]*>{re.escape(pmid)}</PMID>.*?</PubmedArticle>', text, re.DOTALL)
            if m:
                article = m.group(0)
                abs_m = re.search(r'<AbstractText[^>]*>(.*?)</AbstractText>', article, re.DOTALL)
                if abs_m:
                    abstracts[pmid] = re.sub(r'<[^>]+>', '', abs_m.group(1)).strip()
        return abstracts
    except Exception as e:
        print(f"Abstract error: {e}")
        return {}


def classify_delivery(text):
    """识别递送类型"""
    text_lower = text.lower()
    types = []
    for dtype, patterns in DELIVERY_TYPES.items():
        for p in patterns:
            if re.search(p, text_lower, re.IGNORECASE):
                types.append(dtype)
                break
    return list(set(types)) if types else ['other']


def main():
    print("=" * 60)
    print("LNP / 体内递送系统专门扫描")
    print("=" * 60)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    all_papers = {}

    for query, category in SEARCH_QUERIES:
        print(f"\n[{category}] 搜索: {query[:40]}...")
        pmids = search_pubmed(query, days_back=14, max_results=15)
        print(f"  找到 PMID: {len(pmids)}")

        if pmids:
            papers = fetch_details(pmids)
            abstracts = fetch_abstracts(pmids)
            for p in papers:
                p['abstract'] = abstracts.get(p['pmid'], '')
                if p['pmid'] not in all_papers:
                    text = (p['title'] + ' ' + p['abstract']).lower()
                    p['delivery_types'] = classify_delivery(text)
                    p['query_category'] = category
                    all_papers[p['pmid']] = p
        time.sleep(0.5)

    # 按日期排序
    papers_list = sorted(all_papers.values(), key=lambda x: x.get('date', ''), reverse=True)

    # 输出统计
    type_count = {}
    for p in papers_list:
        for t in p.get('delivery_types', []):
            type_count[t] = type_count.get(t, 0) + 1

    print("\n" + "=" * 60)
    print("📊 递送类型分布")
    print("=" * 60)
    for t, c in sorted(type_count.items(), key=lambda x: -x[1]):
        print(f"  {t.upper()}: {c} 篇")

    # 输出 top 文章
    print("\n" + "=" * 60)
    print(f"📚 找到 {len(papers_list)} 篇相关文章（展示前15）")
    print("=" * 60)
    for i, p in enumerate(papers_list[:15], 1):
        types_str = ','.join(p.get('delivery_types', []))
        print(f"\n{i}. PMID:{p['pmid']} [{types_str}]")
        print(f"   {p['title'][:80]}")
        print(f"   {p['journal']} | {p['date']}")

    # 保存
    output_dir = '/Users/nnn_nice/scripts/biotech-monitor/data/daily'
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f'delivery_papers_{datetime.now().strftime("%Y%m%d")}.json')

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'date': datetime.now().strftime('%Y-%m-%d'),
            'timestamp': datetime.now().isoformat(),
            'count': len(papers_list),
            'type_distribution': type_count,
            'papers': papers_list
        }, f, ensure_ascii=False, indent=2)

    print(f"\n已保存: {output_file}")

    return papers_list


if __name__ == '__main__':
    main()