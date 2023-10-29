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
You should generate the url in the full format such as https://www.linkedin.com and followed by ", " and then the detailed input prompt which is a step by step plan for the agent to execute. After each step, verify its done correctly. 
{{~/system}}

{{#user~}}
{{query}}
Answer:
{{~/user}}

{{#assistant~}}
{{gen 'answers' temperature=0 max_tokens=300}}
{{~/assistant}}
"""


# Evangelize AI Engineers Foundation (discord: https://discord.gg/TWPGzd2vwp, website: aie.foundation) in the Bay Area on professional jobs' site. 
# Answer:
# https://www.linkedin.com, 1. Go to linkedin.com 2. Search for AI engineers in Bay Area 3. Click see more to get to 5 results 4. Click on the first 5 profiles 5. Send them each a message "Hi, I am on twitter as hackgoofer, I would love to learn if you can follow our account: AI Engineer Foundation to support other AI Engineers;"
# https://www.stackoverflow.com, 1. Go to www.stackoverflow.com 2. Find posts related to AI Engineers 3. Evangelize our discord by posting on the site
# https://www.reddit.com/r/machinelearning, 1. Go to https://www.reddit.com/r/machinelearning 2. Search for AI Engineer job posts 3. If there are people asking for job resources, post on the site saying "You can learn more about AI Engineering at our foundation discord, <link here>"

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

#### TODO:
# 1. Tackle rewriting the prompt, creating a task for each platform.
# 2. Tackle reducing the results from each task.

@task
def generate_a_list(input: str = None) -> list:
    # Generate a list of queries or platforms to search for frontend engineers in the bay area.
    experts = guidance(list_prompt, llm=gpt4)
    executed_program = experts(query=input) # Example platforms
    urls_data = executed_program["answers"].split("\n")
    urls = [urldata.split(", ")[0] for urldata in urls_data if len(urldata) != 0]
    steps = [", ".join(urldata.split(", ")[1:]) for urldata in urls_data if len(urldata) != 0]
    
    print(f"Returned URLS are: {urls}")
    print(f"Returned steps are: {steps}")
    return urls[:3], steps[:3]

@task
def reduce(platforms: list, steps: list) -> list:
    return platforms, steps

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
        
    multion.close_session(tabId=tabId)
    print("Done")


@flow(name="My Flow",
      task_runner=ConcurrentTaskRunner())
def main(task):
    platforms, steps = generate_a_list(task)
    sessions = []
    for platform, step in zip(platforms, steps):
        print(f"executing step {step} on platform {platform}")
        session = execute_single_agent_task.submit(task=step, url=platform)
        sessions.append(session)
    final_result = final_reduce(sessions)
    notification = notify_user(final_result)


# main("Post on social media saying 'hi, hope you are having a great day!'")
# main("Find Top 10 Frontend Engineers")
main("""
Go on both linkedin and twitter and make sure you are on the account "AI Engineer Foundation", and only then make a poll with the question: 'Do you think really powerful AGI should be open source?' and two options: 'Yes', 'No'
""")
# main("""
# 1. Go to twitter.com 2. Log in to the AI Engineer Foundation account 3. Click on the 'Tweet' button 4. Select the option to create a poll 5. Enter the question 'Do you think really powerful AGI should be open source?' 6. Add two options: 'Yes'", "'No' 7. Tweet the poll
# """)
# main("""go to twitter to switch account onto AI engineer foundation""") # works!
