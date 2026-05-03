from dotenv import load_dotenv
import os
load_dotenv()
import anthropic
client = anthropic.Anthropic()
r = client.messages.create(model='claude-sonnet-4-6', max_tokens=10, messages=[{'role':'user','content':'hi'}])
print(r.content)

