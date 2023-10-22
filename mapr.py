from prefect import task, flow
import multion
from datetime import timedelta
import openai
import guidance
import requests
from prefect.task_runners import ConcurrentTaskRunner
import os
from dotenv import load_dotenv
load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

gpt4 = guidance.llms.OpenAI("gpt-4")

list_prompt = """
{{#system~}}
You are an expert task manager that manages parallel agents that each does one task, only list the websites that made sense for the task:
{{~/system}}

{{#user~}}
Find Top 10 Frontend Engineers in the Austen area
Answer:
https://www.linkedin.com
https://www.indeed.com
https://www.glassdoor.com

{{query}}
Answer:
{{~/user}}
{{#assistant~}}
{{gen 'answers' temperature=0 max_tokens=300}}
{{~/assistant}}
"""

# reduce_prompt = """
# {{#system~}}
# You are an expert task manager that aggregates results returned by each agent.:
# {{~/system}}

# {{#user~}}
# Aggregate the following: 
# Answer:
# https://www.linkedin.com
# https://www.indeed.com
# https://www.glassdoor.com

# {{query}}
# Answer:
# {{~/user}}

# {{#assistant~}}
# {{gen 'aggregated' temperature=0 max_tokens=300}}
# {{~/assistant}}
# """

@task
def generate_a_list(input: str = None) -> list:
    # Generate a list of queries or platforms to search for frontend engineers in the bay area.
    experts = guidance(list_prompt, llm=gpt4)
    executed_program = experts(query=input) # Example platforms
    urls = executed_program["answers"].split("\n")
    print(f"Returned URLS are: {urls}")
    return urls[:3]

@task
def reduce(platforms: list) -> list:
    return platforms

@task
def execute_the_task(platform: str, input: str="") -> dict:
    # Create a new Multion session to find frontend engineers in the bay area on the given platform.
    payload = {"input": input, "url": platform}
    response = requests.post("https://multion-api.fly.dev/sessions", json=payload)
    response.raise_for_status()
    return response.json()

@task
def final_reduce(sessions: list) -> list:
    # Aggregate the results of the Multion sessions to get the top 10 frontend engineers.
    # For simplicity, we are returning the sessions as-is in this example.
    return sessions

@task
def notify_user(final_result: list) -> None:
    # Notify the user with the list of top 10 frontend engineers.
    print(f"Notification to User: {final_result}")

def _login():
    multion.login()
    _ = multion.set_remote(False)
    print("Logged in...")

@task(retries=3, retry_delay_seconds=10)
def execute_single_agent_task(task: str = None, url: str = "https://www.google.com", tabId: str = None):
    _login()
    new_input = task + ". Do not ask for user input." 
    session = multion.new_session(data={"input": new_input, "url": url})
    tabId = session['session_id']
    print(f"Session ID: {tabId}")

    updated_session = multion.update_session(tabId=tabId, data={"input": new_input, "url": url})
    tabId = updated_session['session_id']
    print("updated_session")
    print(list(updated_session.keys()))
    should_continue = updated_session["status"] == "CONTINUE"
    try:
      while should_continue:
          updated_session = multion.update_session(tabId=tabId, data={"input": new_input, "url": updated_session["url"]})
          should_continue = updated_session["status"] == "CONTINUE"
          print("updated_session")
          print(list(updated_session.keys()))
          tabId = updated_session['session_id']
    except Exception as e:
      print(f"ERROR: {e}")
        
    closed_session = multion.close_session(tabId=tabId)
    print("closed session")
    print(list(closed_session.keys()))
    print("Session ID: ", closed_session['session_id'])
    print("Message: ", closed_session['message'])
    print("Status: ", closed_session['status'])
    return closed_session


@flow(name="My Flow",
      task_runner=ConcurrentTaskRunner())
def main(task="Find Top 10 Frontend Engineers"):
    platforms = generate_a_list(task)
    reduced_platforms = reduce(platforms)
    sessions = []
    for platform in reduced_platforms:
        session = execute_single_agent_task.submit(task=task, url=platform)
        sessions.append(session)
    final_result = final_reduce(sessions)
    notification = notify_user(final_result)


# main("Post on social media saying 'hi, hope you are having a great day!'")
# main("Find Top 10 Frontend Engineers")
main("Find Top 10 Frontend Engineers")
