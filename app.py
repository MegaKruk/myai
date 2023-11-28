from flask import Flask, request, jsonify
from framework.myai_framework import *
from my_secrets.my_secrets import GPT_API_URL, OPENAI_API_KEY, SERPAPI_KEY
import ast

app = Flask(__name__)
conversation_context = [] # Global variable to store context


def context_to_string(context):
    conversation_context_str = ""
    for entry in context:
        conversation_context_str += f"- {entry}\n"
    return conversation_context_str


def serpapi_search(query):
    # The base URL for the SerpAPI search
    url = 'https://serpapi.com/search'

    # Parameters for the GET request
    params = {
        'q': query,     # Your search query, in this case, the webpage URL
        'api_key': SERPAPI_KEY # Your private SerpAPI key
    }

    # Making the GET request
    response = requests.get(url, params=params)
    # Check if the request was successful
    if response.status_code == 200:
        print("200 OK") # Return the JSON response if successful
    else:
        print("ERROR:")
        print(f"response code: {response.code}")
        print(f"response text: {response.text}")
    return response.json()


def extract_context_from_serpapi_results(serpapi_search_results):
    organic_results = serpapi_search_results.get("organic_results", [])
    print(len(json.dumps(organic_results).encode('utf-8')))
    return organic_results


def answer_question(question, serpapi_context):
    user_content = f"### PYTANIE: {question}"
    if len(conversation_context) > 0:
        user_content += f"\n### KONTEKST: \n{context_to_string(conversation_context)}"
    if len(serpapi_context) > 0:
        user_content += f"\n### KONTEKST Z WYSZUKIWANIA: \n{context_to_string(serpapi_context)}"

    HEADERS = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
        "User-Agent": "OpenAI-Python-Client"
    }
    messages = [
        {"role": "system", "content": "Odpowiadasz na PYTANIA ULTRA-krótko i ULTRA-zwięźle, najlepiej 1 słowem. "
                                      "Czasami dostaniesz KONTEKST, wtedy posłuź się widzą z niego aby odpowiedzieć na PYTANIE. "
                                      "Przykładowe PYTANIE: 'Nad jakim morzem leży Polska?' Idealna odpowiedź: 'Bałtyckie'"},
        {"role": "user", "content": user_content}
    ]
    payload = {
        "model": "gpt-4",
        "messages": messages
    }
    response = requests.post(GPT_API_URL, headers=HEADERS, json=payload)
    answer = response.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    if answer.startswith("'") and answer.endswith("'"):
        answer = answer[1:-1]
    print(f"answer:\n{answer}")
    return answer


def convert_markdown_to_html(markdown_input):
    HEADERS = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
        "User-Agent": "OpenAI-Python-Client"
    }
    messages = [
        {"role": "system", "content": "md2html"},
        {"role": "user", "content": f"{markdown_input}"}
    ]
    payload = {
        # there seem to be some errors in training data?
        "model": "ft:gpt-3.5-turbo-1106:personal::8ORnxKfC",
        "messages": messages
    }
    response = requests.post(GPT_API_URL, headers=HEADERS, json=payload)
    html_output = response.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    if html_output.startswith("'") and html_output.endswith("'"):
        html_output = html_output[1:-1]
    print(f"answer:\n{html_output}")
    return html_output


def detect_query_intention(query):
    intentSchema = {
        "name": "describe_intention",
        "description": "",
        "parameters": {
            "type": "object",
            "properties": {
                "tool": {
                    "type": "string",
                    "description": """
                      intent musi być jednym z:
                      'remember' — zostanie wybrane kiedy użytkownik poprosi o zapamiętanie informacji. Przykład: 'Mam na imię Megakruk' = {'intent': 'remember', 'desc': 'Zapamiętaj imię'};
                      'simple_question' — zostanie wybrane kiedy użytkownik poprosi o odpowiedzenie na pytanie, które nie wymaga użycia przeglądarki w celu uzyskania dodatkowych, aktualnych informacji, a wystarczy wiedza ogólna i ewentualnie kontekst. Przykład 1: 'Kto napisał Romeo i Julię?' = {'intent': 'simple_question', 'desc': 'Autor - Romeo i Julia'}. Przykład 2: 'Podaj najbliższe morze położone na północ od Polski' = {'intent': 'simple_question', 'desc': 'Morze na północ od Polski'}. Przykład 3: 'Kim jest MegaKruk?' = {'intent': 'simple_question', 'desc': 'Kim jest użytkownik MegaKruk, potrzebny kontekst.'};
                      'complex_question' — zostanie wybrane kiedy użytkownik poprosi o odpowiedzenie na bardziej skomplikowane pytanie wymagające sprawdzenia faktów lub zrobienia research'u przez użycie przeglądarki. Przykład 1: 'Jaki jest aktualny adres URL do portalu Onet biorąc pod uwagę, że dzisiaj jest 2023-11-23?' = {'intent': 'complex_question', 'desc': 'Aktualny adres URL do Onet'}. Przykład 2: 'Podajnajlepiej zarabiające gry na Androida' = {'intent': 'complex_question', 'desc': 'Najlepiej zarabiające gry Android'}
                      """,
                }
            },
            "required": ["intent"],
        },
    }
    HEADERS = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
        "User-Agent": "OpenAI-Python-Client"
    }
    messages = [
        {"role": "system", "content": f"{intentSchema}"},
        {"role": "user",
         "content": f" ### ZAPYTANIE: {query}"}
    ]
    payload = {
        "model": "gpt-4",
        "messages": messages
    }
    response = requests.post(GPT_API_URL, headers=HEADERS, json=payload)
    intent = response.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    intent_dict = ast.literal_eval(intent)
    return intent_dict


def remember_old(info):
    conversation_context.append(info)
    return f"OK. Info '{info}' was saved to context"


@app.route('/ask', methods=['POST'])
def ask():
    try:
        # Extract question from JSON
        data = request.json
        print(f"data:\n{data}")
        question_or_info = data.get('question')
        intent = detect_query_intention(question_or_info)
        print(intent)
        if intent["intent"] == "simple_question":
            # Use your function to get the answer
            answer = answer_question(question_or_info, [])
        elif intent["intent"] == "remember":
            # Add info to the context, later replace with qdrant?
            answer = remember_old(question_or_info)
        elif intent["intent"] == "complex_question":
            serpapi_search_results = serpapi_search(question_or_info)
            serpapi_context = extract_context_from_serpapi_results(serpapi_search_results)
            answer = answer_question(question_or_info, serpapi_context)
        else:
            return jsonify({"reply": f"Unknown query intent: {intent}"})
        # Return the answer in the required JSON format
        return jsonify({"reply": answer})

    except Exception as e:
        # Handle exceptions (e.g., bad JSON)
        return jsonify({"reply": str(e)})


@app.route('/remember', methods=['POST'])
def remember():
    # TODO: replace with qdrant for better context injection
    return "i member!"


@app.route('/ask_search', methods=['POST'])
def remember():
    try:
        data = request.json
        print(f"data:\n{data}")
        question_or_info = data.get('question')
        serpapi_search_results = serpapi_search(question_or_info)
        serpapi_context = extract_context_from_serpapi_results(serpapi_search_results)
        answer = answer_question(question_or_info, serpapi_context)
        return jsonify({"reply": answer})

    except Exception as e:
        # Handle exceptions (e.g., bad JSON)
        return jsonify({"reply": str(e)})


@app.route('/', methods=['GET'])
def main():
    # TODO: create frontend or CLI
    return "Render index.html here"


@app.route('/md2html', methods=['POST'])
def md2html():
    try:
        data = request.json
        print(f"data:\n{data}")
        markdown_input = data.get('question')
        html_output = convert_markdown_to_html(markdown_input)
        return jsonify({"reply": html_output})
    except Exception as e:
        # Handle exceptions (e.g., bad JSON)
        return jsonify({"reply": str(e)})


@app.route('/context')
def context():
    return context_to_string(conversation_context)


@app.route('/health')
def health():
    return "myai app is healthy"


@app.route('/clear_context', methods=['POST'])
def clear_context():
    try:
        conversation_context.clear()
        return "context cleared"
    except Exception as e:
        return f"error while clearing context: {e}"


if __name__ == '__main__':
    app.run(debug=True)
