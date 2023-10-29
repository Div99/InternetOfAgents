from prefect import task, flow
import multion
from datetime import timedelta
import openai
import guidance
import requests
from prefect.task_runners import ConcurrentTaskRunner
import os
from dotenv import load_dotenv
from langchain.agents import initialize_agent
import base64
import os
from io import BytesIO
from typing import Optional

from langchain import (
    LLMMathChain,
    OpenAI,
    SerpAPIWrapper,
)
from langchain.agents import initialize_agent, Tool
from langchain.agents import AgentType
from langchain.chat_models import ChatOpenAI

os.environ["LANGCHAIN_TRACING"] = "true"
# os.environ['OPENAI_API_KEY'] = "<openai_api_key>"
from langchain.tools import StructuredTool

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
# 1. Improve the accuracy of the use case here
# 2. Do the script 10 times to measure accuracy
# 3. Create a function to aggregate the results back to users

class MultionToolSpec:
    """MultiOn tool spec."""

    spec_functions = ["browse"]

    def __init__(
        self,
        token_file: Optional[str] = "multion_token.txt",
        default_url: Optional[str] = "https://google.com",
        mode: Optional[str] = "step",
    ) -> None:
        """Initialize with parameters."""
        import multion

        multion.refresh_token()
        multion.login()

        self.current_status = "NOT_ACTIVE"
        self.session_id = None
        self.current_url = default_url
        self.mode = mode

    def browse(self, instruction: str, url: str):
        """
        Browse the web using MultiOn
        MultiOn gives the ability for LLMs to control web browsers using natural language instructions
        Always include an URL to start browsing from (default to https://www.google.com/search?q=<search_query> if no better option, where <search_query> is a generated query to Google.)

        You may have to repeat the instruction through multiple steps or update your instruction to get to
        the final desired state. If the status is 'CONTINUE', then reissue the same instruction to continue execution

        args:
            instruction (str): The detailed and specific natural language instruction for web browsing
            url (str): The best URL to start the session based on user instruction
        """
        import multion

        multion.refresh_token()
        multion.set_remote(False)

        # If a session exists, update it. Otherwise, create a new session.
        if self.session_id:
            session = multion.update_session(
                self.session_id, {"input": instruction, "url": self.current_url}
            )

        else:
            session = multion.new_session(
                {"input": instruction, "url": url if url else self.current_url}
            )
            self.session_id = session["session_id"]

        # Update the current status and URL based on the session
        self._update_status(session)

        while self.mode == "auto" and (self.current_status == "CONTINUE"):
            session = multion.update_session(
                self.session_id, {"input": instruction, "url": self.current_url}
            )
            self._update_status(session)
            print(self.current_status, self.current_url)

        # Until agent completes the task we keep triggering agent
        # while (agent.current_status != 'DONE') {
        #     console.log("CURRENT STATUS:", agent.current_status);
        #     switch (agent.current_status) {
        #         case 'NOT_ACTIVE':
        #             response = await triggerAgent(userQuery, domain, agent);
        #             continue;
        #         case 'CONTINUE':
        #             domain = agent.current_url;
        #             response = await triggerAgent(userQuery, domain, agent);
        #             continue;
        #         case 'NOT SURE':
        #             let model_query = `YOU HAD ASKED USER THIS QUESTION PREVIOUSLY: ${agent.question}\n`;
        #             let user_response = `AND THIS IS THE USER'S RESPONSE TO THE QUESTION: ${agent.user_response}`;
        #             let new_query = userQuery + `\n` + model_query + user_response;
        #             console.log("New user query:", new_query)
        #             domain = agent.current_url;
        #             response = await triggerAgent(new_query, domain, agent);
        #             continue;
        #         case 'WRONG':
        #     }
        return {
            "status": session["status"],
            "url": session["url"],
            "action_completed": session["message"],
            "content": self._read_screenshot(session["screenshot"]),
        }

    def _update_status(self, session):
        """Update the current status and URL based on the session."""
        self.current_status = session["status"]
        self.current_url = session["url"]

    def _read_screenshot(self, screenshot) -> str:
        import pytesseract
        from PIL import Image

        image_bytes = screenshot.replace("data:image/png;base64,", "")
        image = Image.open(self._bytes_to_image(image_bytes))

        return pytesseract.image_to_string(image)

    def _bytes_to_image(self, img_bytes):
        return BytesIO(base64.b64decode(img_bytes))

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

def agent(query: str):
    multion_toolkit = MultionToolSpec()
    tool = StructuredTool.from_function(multion_toolkit.browse)

    llm = OpenAI(temperature=0)

    # Structured tools are compatible with the STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION agent type.
    agent_executor = initialize_agent(
        [tool],
        llm,
        agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
    )

    return agent_executor.run(query)


@task(retries=3, retry_delay_seconds=10)
def execute_single_agent_task(task: str = None, url: str = "https://www.google.com", tabId: str = None):
    _login()
    # new_input = task + ". Do not ask for user input." 
    # session = multion.new_session(data={"input": new_input, "url": url})
    # tabId = session['session_id']
    # print(f"Session ID: {tabId}")

    # updated_session = multion.update_session(tabId=tabId, data={"input": new_input, "url": url})
    # tabId = updated_session['session_id']
    # print("updated_session")
    # print(list(updated_session.keys()))
    # should_continue = updated_session["status"] == "CONTINUE"
    # try:
    #   while should_continue:
    #       updated_session = multion.update_session(tabId=tabId, data={"input": new_input, "url": updated_session["url"]})
    #       should_continue = updated_session["status"] == "CONTINUE"
    #       print("updated_session")
    #       print(list(updated_session.keys()))
    #       tabId = updated_session['session_id']
    try:
        agent(query=task)
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
Go on both linkedin and twitter and switch to the account "AI Engineer Foundation" owned by me, and only then make a poll with the question: 'Do you think really powerful AGI should be open source?' and two options: 'Yes', 'No'
""")
# main("""
# 1. Go to twitter.com 2. Log in to the AI Engineer Foundation account 3. Click on the 'Tweet' button 4. Select the option to create a poll 5. Enter the question 'Do you think really powerful AGI should be open source?' 6. Add two options: 'Yes'", "'No' 7. Tweet the poll
# """)
# main("""go to twitter to switch account onto AI engineer foundation""") # works!
