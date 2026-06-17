import json
import time
import urllib.request
import urllib.error

API_URL = "http://192.168.1.35:9091/API"
PASSWORD = "123"
LOG_FILE = "/home/ozand/Projects/ayga-cli/direct_api_experiments.json"

experiments = [
    {"parser": "FreeAI::Perplexity", "preset": "default", "query": "what is 2+2", "options": []},
    {"parser": "FreeAI::ChatGPT", "preset": "default", "query": "what is 2+2", "options": []},
    {"parser": "FreeAI::DeepAI", "preset": "default", "query": "Write a short poem about coding", "options": [{"id": "chat_style", "value": "ai_poem"}]},
    {"parser": "FreeAI::DeepAI", "preset": "default", "query": "Write a python fibonacci function", "options": [{"id": "chat_style", "value": "ai_code"}]},
    {"parser": "FreeAI::Copilot", "preset": "default", "query": "what is 2+2", "options": []},
    {"parser": "FreeAI::Kimi", "preset": "default", "query": "what is 2+2", "options": []}
]

def run_test(parser, preset, query, options, max_retries=5, timeout=180):
    payload = {
        "password": PASSWORD,
        "action": "oneRequest",
        "data": {
            "parser": parser,
            "preset": preset,
            "query": query
        }
    }
    if options:
        payload["data"]["options"] = options
        
    req_data = json.dumps(payload).encode("utf-8")
    
    for attempt in range(1, max_retries + 1):
        start_time = time.time()
        try:
            req = urllib.request.Request(
                API_URL, 
                data=req_data, 
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as res:
                response_body = res.read().decode("utf-8")
                duration = time.time() - start_time
                data = json.loads(response_body)
                
                if data.get("success") == 1:
                    return {
                        "status": "success",
                        "duration": duration,
                        "attempt": attempt,
                        "error": None,
                        "raw_response": data
                    }
                else:
                    error_msg = data.get("error") or str(data)
                    print(f"[{parser}] Attempt {attempt} failed with internal error: {error_msg}")
                    if attempt == max_retries:
                        return {
                            "status": "failed",
                            "duration": duration,
                            "attempt": attempt,
                            "error": error_msg,
                            "raw_response": data
                        }
        except urllib.error.URLError as e:
            duration = time.time() - start_time
            print(f"[{parser}] Attempt {attempt} failed with connection error: {e}")
            if attempt == max_retries:
                return {
                    "status": "failed",
                    "duration": duration,
                    "attempt": attempt,
                    "error": str(e),
                    "raw_response": None
                }
        except Exception as e:
            duration = time.time() - start_time
            print(f"[{parser}] Attempt {attempt} failed with unexpected error: {e}")
            if attempt == max_retries:
                return {
                    "status": "failed",
                    "duration": duration,
                    "attempt": attempt,
                    "error": str(e),
                    "raw_response": None
                }
        time.sleep(2)

def main():
    results = []
    for exp in experiments:
        print(f"Starting experiment: {exp['parser']} (preset: {exp['preset']})")
        res = run_test(exp["parser"], exp["preset"], exp["query"], exp["options"])
        exp_result = {
            "parser": exp["parser"],
            "preset": exp["preset"],
            "query": exp["query"],
            "options": exp["options"],
            "status": res.get("status") if res else "failed",
            "duration": res.get("duration") if res else 0.0,
            "attempts": res.get("attempt") if res else 1,
            "error": res.get("error") if res else "No response returned",
            "has_data": res is not None and res.get("raw_response") is not None
        }
        results.append(exp_result)
        status = res.get("status") if res else "failed"
        duration = res.get("duration") if res else 0.0
        print(f"Finished {exp['parser']} - Status: {status}, Time: {duration:.2f}s")
        
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"All experiments finished. Log written to {LOG_FILE}")

if __name__ == "__main__":
    main()
