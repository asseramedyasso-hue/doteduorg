import os
from flask import Flask, request, jsonify

app = Flask(__name__)

# Load API key from environment variable
API_KEY = os.getenv('CHATBOT_API_KEY')

@app.route('/chatbot', methods=['POST'])
def chatbot_response():
    data = request.get_json()
    user_input = data.get('message')

    # Example response generation logic
    response = generate_response(user_input)

    return jsonify({'response': response})

def generate_response(user_input):
    # Dummy algorithm, replace this with actual logic
    return f'You said: {user_input}'

if __name__ == '__main__':
    app.run(debug=True)