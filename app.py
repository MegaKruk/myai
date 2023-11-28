from flask import Flask, request, jsonify
from framework.myai_framework import *

app = Flask(__name__)


@app.route('/remember', methods=['POST'])
def remember():
    # TODO: replace with qdrant for better context injection
    return "i member!"


@app.route('/ask_detect_intent', methods=['POST'])
def ask_detect_intent():
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


@app.route('/ask_search', methods=['POST'])
def ask_search():
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


@app.route('/ask', methods=['POST'])
def ask():
    try:
        data = request.json
        print(f"data:\n{data}")
        question = data.get('question')
        answer = answer_question(question, [])
        return jsonify({"reply": answer})

    except Exception as e:
        # Handle exceptions (e.g., bad JSON)
        return jsonify({"reply": str(e)})


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


@app.route('/', methods=['GET'])
def main():
    # TODO: create frontend or CLI
    return "Render index.html here"


if __name__ == '__main__':
    app.run(debug=True)
