from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()


def generate_improvement_tips(result):
    prompt = f"""
    You are a speech therapy assistant. Based on the following speech session results, provide detailed improvement tips for the user:
    
    Disfluency: {result['disfluency']}
    Fluency: {result['fluency']}
    Interjection: {result['interjection']}
    Natural Pause: {result['naturalPause']}

    Offer specific exercises and techniques to help the user improve their speech. Include motivational encouragement and realistic goal suggestions.
    """

    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": "You are a speech therapy assistant."},
                  {"role": "user", "content": prompt}]
    )

    response_message = completion.choices[0].message.content

    return response_message
