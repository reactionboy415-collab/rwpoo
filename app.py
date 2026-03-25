import os
import uuid
import json
import requests
from flask import Flask, render_template_string, request, Response, stream_with_context

app = Flask(__name__)

# --- PREMIUM SHOPSENSE UI ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ShopSense AI | Discern Better</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&family=Playfair+Display:ital,wght@1,600&display=swap" rel="stylesheet">
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background: #050505; color: #e5e5e5; font-family: 'Outfit', sans-serif; }
        .serif { font-family: 'Playfair Display', serif; }
        .accent-border { border-bottom: 1px solid rgba(255,255,255,0.1); }
        .status-dot { width: 6px; height: 6px; background: #fff; border-radius: 50%; display: inline-block; animation: blink 1.4s infinite; }
        @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.2; } }
        .data-card { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 20px; margin-top: 20px; }
    </style>
</head>
<body class="min-h-screen p-8 md:p-24">
    <div class="max-w-3xl mx-auto">
        <header class="mb-20">
            <h1 class="text-5xl md:text-7xl serif italic mb-2">ShopSense AI</h1>
            <p class="text-xs tracking-[0.4em] text-gray-500 uppercase">Automated Consumer Intelligence</p>
        </header>

        <div class="relative mb-16">
            <input type="text" id="topic" placeholder="What are we analyzing today?" 
                   class="w-full bg-transparent border-b border-gray-800 py-4 text-2xl outline-none focus:border-white transition-colors serif italic">
            <button onclick="ignite()" class="absolute right-0 bottom-4 text-sm font-semibold hover:text-white text-gray-500 transition-colors">START &rarr;</button>
        </div>

        <div id="flow" class="space-y-6"></div>
        <div id="result" class="opacity-0 transition-opacity duration-1000"></div>
    </div>

    <script>
        function ignite() {
            const topic = document.getElementById('topic').value;
            if(!topic) return;
            
            const flow = document.getElementById('flow');
            const result = document.getElementById('result');
            flow.innerHTML = '';
            result.style.opacity = '0';

            const source = new EventSource(`/analyze?topic=${encodeURIComponent(topic)}`);
            
            source.onmessage = function(e) {
                const raw = JSON.parse(e.data);
                const queryData = raw.responses?.researchProductComparison;
                
                if(queryData) {
                    const content = Object.values(queryData)[0];
                    
                    if(content.statusLog) {
                        content.statusLog.forEach(log => {
                            if(!document.getElementById(log.statusMessageId)) {
                                const div = document.createElement('div');
                                div.id = log.statusMessageId;
                                div.className = 'text-sm text-gray-400 flex items-center gap-3 animate-pulse';
                                div.innerHTML = `<span class="status-dot"></span> ${log.statusMessage}`;
                                flow.appendChild(div);
                            }
                        });
                    }

                    if(content.data) {
                        result.innerHTML = `<div class="data-card"><pre class="text-xs text-blue-300 overflow-x-auto">${JSON.stringify(content.data, null, 2)}</pre></div>`;
                        result.style.opacity = '1';
                        source.close();
                    }
                }
            };
            source.onerror = () => source.close();
        }
    </script>
</body>
</html>
"""

def fetch_data(topic):
    session = f"anon-{uuid.uuid4().hex[:10]}"
    qid = uuid.uuid4().hex[:12]
    url = "https://api.vetted.ai/queries"
    headers = {
        "Content-Type": "application/json",
        "x-session-id": session,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Origin": "https://vetted.ai",
        "Accept": "application/x-ndjson"
    }
    payload = {
        "queries": {
            "researchProductComparison": {
                qid: { "localization": "IN", "context": f"Detailed review for {topic}" }
            }
        }
    }
    try:
        with requests.post(url, json=payload, headers=headers, stream=True) as r:
            for line in r.iter_lines():
                if line:
                    yield f"data: {line.decode('utf-8')}\\n\\n"
    except:
        yield f"data: {json.dumps({'error': 'System failure'})}\\n\\n"

@app.route('/')
def index(): return render_template_string(HTML_TEMPLATE)

@app.route('/analyze')
def api():
    topic = request.args.get('topic', '')
    return Response(stream_with_context(fetch_data(topic)), mimetype="text/event-stream")

if __name__ == '__main__':
    # Render uses 'PORT' environment variable
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
