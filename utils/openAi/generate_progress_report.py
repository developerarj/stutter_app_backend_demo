from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

# refer other function for format


def generate_progress_report(user_id, historical_data):
    prompt = f"""
    You are a speech therapy assistant. Analyze the following historical data for user {user_id} and provide a progress report:
    
    {historical_data} 
    
    Highlight the improvements, current challenges, and suggest next steps.
    """

    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": "You are a speech therapy assistant."},
                  {"role": "user", "content": prompt}]
    )

    response_message = completion.choices[0].message.content

    return response_message
