from typing import Any

PROXY_PROFILES = {
    'fast': {
        'checker': 'USA_1IP_v4',
        'useproxy': 1,
        'proxyretries': 5,
        'timeout': 120
    },
    'bulk': {
        'checker': 'best-proxy',
        'useproxy': 1,
        'proxyretries': 20,
        'timeout': 300
    }
}

PARSER_PROXY_MAP = {
    'FreeAI::Perplexity': 'fast',
    'FreeAI::': 'bulk',
    'HTML::ArticleExtractor': 'fast',
    'HTML::TextExtractor': 'fast',
    'Net::HTTP': 'fast'
}

def get_proxy_options(parser: str) -> list[dict[str, Any]]:
    profile_name = None
    
    # Exact match
    if parser in PARSER_PROXY_MAP:
        profile_name = PARSER_PROXY_MAP[parser]
    else:
        # Prefix match (sort by length descending to match longest prefix first, though not strictly required here)
        for prefix in sorted(PARSER_PROXY_MAP.keys(), key=len, reverse=True):
            if parser.startswith(prefix):
                profile_name = PARSER_PROXY_MAP[prefix]
                break
                
    if not profile_name or profile_name not in PROXY_PROFILES:
        return []
        
    profile = PROXY_PROFILES[profile_name]
    
    options = []
    if 'useproxy' in profile:
        options.append({"id": "useproxy", "value": profile['useproxy']})
    if 'checker' in profile:
        options.append({"id": "proxyChecker", "value": profile['checker']})
    if 'proxyretries' in profile:
        options.append({"id": "proxyretries", "value": profile['proxyretries']})
    if 'timeout' in profile:
        options.append({"id": "timeout", "value": profile['timeout']})
        
    return options

def merge_with_proxy(parser: str, user_options: list[dict[str, Any]]) -> list[dict[str, Any]]:
    proxy_options = get_proxy_options(parser)
    if not proxy_options:
        return user_options
        
    merged = {opt['id']: opt['value'] for opt in proxy_options}
    for opt in user_options:
        merged[opt['id']] = opt['value']
        
    return [{"id": k, "value": v} for k, v in merged.items()]
