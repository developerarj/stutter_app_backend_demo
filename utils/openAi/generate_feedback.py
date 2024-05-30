from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()


def generate_feedback(result):
    prompt = f"""
    You are a speech therapy assistant. Analyze the following speech session result as it is the result of reading given reading material. provide detailed feedback for the user:
    
    Disfluency: {result['disfluency']}
    Fluency: {result['fluency']}
    Interjection: {result['interjection']}
    Natural Pause: {result['naturalPause']}
    
    Provide suggestions for improvement and encouragement.
    """

    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": "You are a speech therapy assistant."},
                  {"role": "user", "content": prompt}]
    )

    # Access the content attribute directly
    response_message = completion.choices[0].message.content

    return response_message


# feedback = generate_feedback(result)
# print(feedback)
