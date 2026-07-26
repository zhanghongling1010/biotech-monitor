#!/usr/bin/env python3
"""
Biotech Monitor - 新闻溯源回填
顶刊新闻(Nature/Science 等记者报道,无摘要)提到研究论文时,
自动从标题提取关键词、扩大日期窗口反查 PubMed,把原论文补进文献列表。
解决"新闻在7天窗口内但原论文发表更早导致永远漏抓"的问题。
被 daily_update.py 调用。
"""
import re
import requests

PUBMED_API = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

# 新闻停用词(标题里无区分度的词)
STOPWORDS = set('''
the a an and or of in on for with by to from at as is are was were be been
this that these those it its their his her our your my we they he she i you
new says study scientists researchers shows show finds find could can may might
will would after before over under more most first last how what when where which who
why into about against between through during without within
cells cell cancer kills kill drug drugs therapy treatment human patients disease
gene genes genetic dna rna protein proteins enzyme enzymes mechanism mechanisms
approach using use based via target targets targeting
bizarre weird strange novel new-old
news says according report reports reported
'''.split())

# 顶刊(这些刊的无摘要条目视为新闻报道)
NEWS_JOURNALS = {
    'nature', 'science', 'cell',
    'new england journal of medicine', 'nejm', 'lancet', 'jama', 'bmj',
    'nature biotechnology', 'nature medicine', 'nature genetics',
    'science translational medicine',
}


def _norm_journal(name):
    main = str(name or '').split(':')[0]
    jn = re.sub(r'[^a-z0-9 ]', '', main.lower()).strip()
    return re.sub(r'^the ', '', re.sub(r'\s+', ' ', jn))


def is_news_item(paper):
    """顶刊 + 无摘要 = 新闻报道(记者文章),而不是研究论文"""
    return _norm_journal(paper.get('journal')) in NEWS_JOURNALS and not paper.get('abstract')


def extract_query_terms(title, max_terms=3):
    """从新闻标题提取有区分度的关键词:优先大写缩写(Cas12a2、KRAS),
    再用长实词,过滤停用词"""
    title = title or ''
    # 大写/混合大小写缩写词优先(Cas12a2, KRAS, CRISPR, AAV, LNP...)
    acronyms = [w for w in re.findall(r'\b[A-Za-z]*[A-Z][A-Za-z0-9-]*\b', title)
                if len(w) >= 3 and w.lower() not in STOPWORDS]
    # 长实词
    words = [w.lower() for w in re.findall(r'[A-Za-z]{5,}', title)
             if w.lower() not in STOPWORDS]
    # 去重保序:缩写优先,然后实词
    seen, terms = set(), []
    for w in acronyms + words:
        k = w.lower()
        if k not in seen:
            seen.add(k)
            terms.append(w)
        if len(terms) >= max_terms:
            break
    return terms


def search_related_papers(terms, days_back=120, max_results=5):
    """用提取的关键词反查 PubMed(窗口拉长到120天,覆盖原论文发表时间)"""
    if not terms:
        return []
    query = ' AND '.join(f'{t}[Title/Abstract]' for t in terms)
    try:
        r = requests.get(PUBMED_API + 'esearch.fcgi', params={
            'db': 'pubmed', 'term': query, 'reldate': days_back,
            'datetype': 'pdat', 'retmax': max_results,
            'retmode': 'json', 'sort': 'relevance',
        }, timeout=20)
        return r.json().get('esearchresult', {}).get('idlist', [])
    except Exception as e:
        print(f'  溯源搜索失败: {e}')
        return []


def backfill_from_news(papers_by_category, fetch_details_fn, max_news_per_category=3):
    """主入口:扫描各分类中的顶刊新闻,把原论文回填进对应分类。
    fetch_details_fn: 复用 collect_pubmed.fetch_article_details
    返回新增论文数量"""
    added = 0
    for category, papers in papers_by_category.items():
        news_items = [p for p in papers if is_news_item(p)][:max_news_per_category]
        if not news_items:
            continue
        existing_pmids = {str(p.get('pmid')) for p in papers if p.get('pmid')}
        for news in news_items:
            terms = extract_query_terms(news.get('title', ''))
            if len(terms) < 2:
                continue
            # 渐进放松:先全词 AND,无结果就逐步减词,避免过严漏掉原论文
            pmids = []
            for n in range(min(len(terms), 3), 1, -1):
                pmids = search_related_papers(terms[:n])
                if pmids:
                    break
            new_pmids = [p for p in pmids if p not in existing_pmids]
            if not new_pmids:
                continue
            try:
                articles = fetch_details_fn(new_pmids)
            except Exception as e:
                print(f'  溯源抓取详情失败: {e}')
                continue
            for art in articles:
                # 只补研究论文(有摘要),跳过其他新闻/评论
                if not art.get('abstract') or is_news_item(art):
                    continue
                if str(art.get('pmid')) in existing_pmids:
                    continue
                art['backfilled_from_news'] = news.get('title', '')[:80]
                papers.append(art)
                existing_pmids.add(str(art.get('pmid')))
                added += 1
                print(f"  溯源补充: [{category}] {art.get('title', '')[:60]} "
                      f"(源自新闻: {news.get('title', '')[:40]}...)")
    return added
