from flask import Flask, request, jsonify
from agent import run_chess_agent  # Assuming this is the entry point to invoke LangGraph

app = Flask(__name__)

@app.route('/query', methods=['POST'])
def handle_query():
    if request.content_type != 'application/json':
        return jsonify({'error': 'Invalid Content-Type, application/json expected'}), 400
    
    data = request.json
    print(data)
    
    if not data:
        return jsonify({'error': 'Invalid JSON body'}), 400
    
    query = data.get('query_text', '')
    print(query)
    if not query:
        return jsonify({"error": "No query provided"}), 400
    
    print(query)

    # Run the LangGraph workflow with the provided query
    result = run_chess_agent(query)
    print(result)
    return jsonify({"summary": result})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8100)
