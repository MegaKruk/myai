from my_secrets.my_secrets import *
import requests
import json
import uuid
import ast


conversation_context = [] # Global variable to store context (old)


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


def read_json_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)


def download_file(url):
    local_filename = f"./data/{url.split('/')[-1]}"
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return local_filename


def create_collection_in_qdrant(collection_name, documents, QDRANT_URL, doc_keys):
    # Define the schema of the collection, including the vectors field
    collection_schema = {
        "name": collection_name,
        # "vector_size": 1536,  # Set the appropriate vector size
        # "distance": "Cosine",  # Or another distance metric
        "vectors": {
            "size": 1536,
            "distance": "Cosine"
        }
    }
    # Create collection
    response = requests.get(f"{QDRANT_URL}/collections/{collection_name}")
    if response.status_code == 404:
        print("Collection does not exist, create it")
        response = requests.put(f"{QDRANT_URL}/collections/{collection_name}", json=collection_schema)
        if response.status_code != 200:
            raise Exception(f"Error creating collection: {response.json()}")
    else:
        print("Collection exists")
    # Insert documents into the collection
    len_documents = len(documents)
    for idx, doc in enumerate(documents):
        HEADERS = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        if isinstance(doc_keys, list):
            input_text = ""
            for doc_key in doc_keys:
                if doc_key in ['imie', 'nazwisko']:
                    input_text += f"{doc[doc_key]} "
                else:
                    input_text += f"\n{doc_key.replace('_', ' ').capitalize()}: {doc[doc_key]}\n"
        else:
            input_text = doc[doc_keys]
        payload = {
            "model": "text-embedding-ada-002",
            "input": f"{input_text}"
        }
        response = requests.post(ADA_002_API_URL, headers=HEADERS, json=payload)
        vector = [0] * 1536
        if response.status_code == 200:
            vector = response.json().get("data", [{}])[0].get("embedding")
        else:
            # Handle error
            response.raise_for_status()
        doc_id = str(uuid.uuid4())
        payload = {
            "points": [{
                "id": doc_id,  # Using URL as a unique identifier
                "vector": vector,  # The vector obtained from ADA
                "payload": doc
            }]
        }
        response = requests.put(f"{QDRANT_URL}/collections/{collection_name}/points", json=payload)
        if response.status_code != 200:
            raise Exception(f"Error inserting document: {response.json()}")
        print(f"{idx+1} / {len_documents}")
    print(f"Collection '{collection_name}' created and documents inserted.")


def generate_meme(meme_text, meme_image_url):
    url = "https://api.renderform.io/api/v2/render"

    headers = {
        "x-api-key": RENDERFORM_API_KEY,
        "Content-Type": "application/json"
    }

    data = {
        "template": template_id,
        "data": {
            "meme-text.text": meme_text,
            "meme-image.src": meme_image_url
        }
    }

    response = requests.post(url, json=data, headers=headers)

    if response.status_code == 200:
        # Assuming the response contains a JSON payload with the image URL
        return response.json()
    else:
        # Handle errors
        return f"Error: {response.status_code} - {response.text}"


def load_json_from_url(url):
    try:
        response = requests.get(url)

        # Check if the response status code is 200 (OK)
        if response.status_code == 200:
            return response.json()  # Parse JSON from response
        else:
            print(f"Failed to retrieve data: {response.status_code}")
            return None
    except requests.RequestException as e:
        print(f"Error during requests to {url} : {str(e)}")
        return None


def compress_data(data):
    compressed_data = {}
    for person, info_list in data.items():
        compressed_info = []
        for info in info_list:
            # Removing unnecessary characters and using abbreviations
            compressed_info.append(info.replace('. ', '.').replace(', ', ',').replace("\t", "").replace("\n", ""))
        compressed_data[person] = compressed_info
    return compressed_data


def count_tokens(messages, model="gpt-3.5-turbo-0613"):
    # Mock encoding function, as we don't have the actual encoding logic
    def encode(text):
        # This is a simplification. In reality, encoding depends on the model's vocabulary.
        return len(text.split())

    # Model-specific token counts
    if model in ["gpt-3.5-turbo-0613", "gpt-3.5-turbo-16k-0613", "gpt-4-0314", "gpt-4-32k-0314", "gpt-4-0613", "gpt-4-32k-0613"]:
        tokens_per_message = 3
        tokens_per_name = 1
    elif model == "gpt-3.5-turbo-0301":
        tokens_per_message = 4
        tokens_per_name = -1
    elif "gpt-3.5-turbo" in model:
        # Recursive call for certain conditions, assuming the default model
        return count_tokens(messages, "gpt-3.5-turbo-0613")
    elif "gpt-4" in model:
        return count_tokens(messages, "gpt-4-0613")
    else:
        raise ValueError(f"count_tokens is not implemented for model {model}.")

    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message + encode(message['content'])
        if 'name' in message:
            num_tokens += encode(message['name']) + tokens_per_name

    # Adding a constant token count (as in the TypeScript version)
    num_tokens += 3
    return num_tokens
