import os
import uuid
import json
import requests
from flask import Flask, render_template_string, request, Response, stream_with_context

app = Flask(__name__)

# --- PREMIUM UI WITH MARKDOWN SUPPORT ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ShopSense AI | Discern Better</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&family=Playfair+Display:ital,wght@1,600&display=swap" rel="stylesheet">
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        body { background: #050505; color: #e5e5e5; font-family: 'Outfit', sans-serif; }
        .serif { font-family: 'Playfair Display', serif; }
        .status-dot { width: 6px; height: 6px; background: #d4af37; border-radius: 50%; display: inline-block; animation: blink 1.4s infinite; }
        @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.2; } }
        .verdict-box { background: rgba(255,255,255,0.02); border-left: 3px solid #d4af37; padding: 30px; border-radius: 4px; line-height: 1.8; }
        .verdict-box h3 { color: #d4af37; font-family: 'Playfair Display', serif; font-size: 1.5rem; margin-bottom: 1rem; }
        .verdict-box ul { list-style: disc; margin-left: 20px; color: #aaa; }
        .verdict-box strong { color: #fff; }
    </style>
</head>
<body class="min-h-screen p-8 md:p-24">
    <div class="max-w-3xl mx-auto">
        <header class="mb-20">
            <h1 class="text-5xl md:text-7xl serif italic mb-2">ShopSense AI</h1>
            <p class="text-xs tracking-[0.4em] text-gray-500 uppercase font-semibold">Intelligence Stream</p>
        </header>

        <div class="relative mb-16">
            <input type="text" id="topic" placeholder="Inquire about a product..." 
                   class="w-full bg-transparent border-b border-gray-800 py-4 text-2xl outline-none focus:border-[#d4af37] transition-all serif italic">
            <button onclick="ignite()" class="absolute right-0 bottom-4 text-xs font-bold tracking-widest text-[#d4af37]">ANALYZE &rarr;</button>
        </div>

        <div id="flow" class="space-y-4 mb-10"></div>
        <div id="result" class="opacity-0 transition-opacity duration-1000"></div>
    </div>

    <script>
        let lastLogId = "";

        function ignite() {
            const topic = document.getElementById('topic').value;
            if(!topic) return;
            
            const flow = document.getElementById('flow');
            const result = document.getElementById('result');
            flow.innerHTML = '';
            result.style.opacity = '0';
            result.innerHTML = '';

            const source = new EventSource(`/analyze?topic=${encodeURIComponent(topic)}`);
            
            source.onmessage = function(e) {
                try {
                    const raw = JSON.parse(e.data);
                    const resMap = raw.responses?.researchProductComparison;
                    
                    if(resMap) {
                        const content = Object.values(resMap)[0];
                        
                        // 1. Status Log Handling
                        if(content.statusLog) {
                            content.statusLog.forEach(log => {
                                if(log.statusMessageId !== lastLogId) {
                                    lastLogId = log.statusMessageId;
                                    const div = document.createElement('div');
                                    div.className = 'text-sm text-gray-500 flex items-center gap-3 fade-in';
                                    div.innerHTML = `<span class="status-dot"></span> ${log.statusMessage}`;
                                    flow.appendChild(div);
                                }
                            });
                        }

                        // 2. Final Data/Summary Handling
                        // Vetted sends final data in 'data' object inside the response
                        if(content.data && content.data.summary) {
                            renderFinalResult(content.data.summary);
                            source.close();
                        }
                    }
                } catch(err) { console.error("Parse Error", err); }
            };
            source.onerror = () => source.close();
        }

        function renderFinalResult(markdownText) {
            const result = document.getElementById('result');
            result.className = 'verdict-box opacity-100 transition-opacity duration-1000';
            // Use marked to convert markdown to HTML
            result.innerHTML = `<h3>The Executive Verdict</h3>` + marked.parse(markdownText);
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
                qid: { "localization": "IN", "context": f"Complete detailed analysis and buyer's guide for {topic}. Focus on pros, cons and real user sentiment." }
            }
        }
    }
    try:
        with requests.post(url, json=payload, headers=headers, stream=True, timeout=120) as r:
            for line in r.iter_lines():
                if line:
                    yield f"data: {line.decode('utf-8')}\\n\\n"
    except:
        yield f"data: {json.dumps({'error': 'Connection Lost'})}\\n\\n"

@app.route('/')
def index(): return render_template_string(HTML_TEMPLATE)

@app.route('/analyze')
def api():
    topic = request.args.get('topic', '')
    return Response(stream_with_context(fetch_data(topic)), mimetype="text/event-stream")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
