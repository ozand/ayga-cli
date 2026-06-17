def test_get_proxy_options():
    from ayga_cli.proxy_strategy import get_proxy_options
    
    # Exact match for 'fast' profile
    fast_opts = get_proxy_options('FreeAI::Perplexity')
    assert {"id": "useproxy", "value": 1} in fast_opts
    assert {"id": "proxyChecker", "value": "USA_1IP_v4"} in fast_opts
    assert {"id": "proxyretries", "value": 5} in fast_opts
    assert {"id": "timeout", "value": 120} in fast_opts
    
    # Prefix match for 'bulk' profile
    bulk_opts = get_proxy_options('FreeAI::ChatGPT')
    assert {"id": "useproxy", "value": 1} in bulk_opts
    assert {"id": "proxyChecker", "value": "best-proxy"} in bulk_opts
    assert {"id": "proxyretries", "value": 20} in bulk_opts
    assert {"id": "timeout", "value": 300} in bulk_opts
    
    # No match
    no_opts = get_proxy_options('SE::Google')
    assert no_opts == []
    
def test_merge_with_proxy():
    from ayga_cli.proxy_strategy import merge_with_proxy
    
    # User overrides useproxy
    user_opts = [{"id": "useproxy", "value": 0}]
    merged = merge_with_proxy('FreeAI::Perplexity', user_opts)
    assert {"id": "useproxy", "value": 0} in merged
    assert {"id": "proxyChecker", "value": "USA_1IP_v4"} in merged
    
    # User overrides proxyChecker
    user_opts = [{"id": "proxyChecker", "value": "custom"}]
    merged = merge_with_proxy('FreeAI::Perplexity', user_opts)
    assert {"id": "useproxy", "value": 1} in merged
    assert {"id": "proxyChecker", "value": "custom"} in merged
