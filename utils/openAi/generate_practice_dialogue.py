from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()


def generate_practice_dialogue(topic):
    prompt = f"Create a practice dialogue for a user learning to improve speech fluency. The topic is {topic}."

    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": "You are a conversation coach."},
                  {"role": "user", "content": prompt}]
    )

    response_message = completion.choices[0].message.content

    return response_message
