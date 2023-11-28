import requests
import json
import uuid
from my_secrets.my_secrets import my_api_key, ADA_002_API_URL, OPENAI_API_KEY, template_id, RENDERFORM_API_KEY


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
