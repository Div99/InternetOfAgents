from prefect import task, flow
import requests
import random
import string
import multion
import os
import openai
from prefect.task_runners import ConcurrentTaskRunner
from enum import Enum
from typing import Optional
import guidance

# from utils import LLMAdapter

import instructor
from openai import OpenAI
from pydantic import BaseModel
from type import Status, Task, TaskList
from worker import WorkerAgent
from viz import visualize_task_list

openai.api_key = os.getenv("OPENAI_API_KEY")


class ManagerAgent:
    def __init__(
        self,
        objective: str = "",
        model_name: str = "gpt-4-1106-preview",
        use_openai=True,
    ):
        # List of tasks to be performed per agent
        self.workers = []
        self.tasks = []

        self.objective = objective

        if use_openai:
            self.client = instructor.patch(OpenAI())
            # self.client = LLMAdapter(model_name, use_openai=True)
            self.llm = guidance.llms.OpenAI(model_name)
        else:
            raise NotImplementedError
            self.client = LLMAdapter(model_name, use_openai=False)
            self.llm = ""  # use huggingface via Text Generation Inference Interface

    def generate_tasks(self, objective: str) -> TaskList:
        self.system_prompt = "You are an expert task manager that manages agents that each does one task. You decide how many agents is needed to do the meta-task, and what each agent's task is. The agents tasks should be done in parallel."

        self.user_prompt = f"""
                Create the tasks items for the following objective: {objective}
                """

        return self.client.chat.completions.create(
            model="gpt-4-1106-preview",
            response_model=TaskList,
            messages=[
                {
                    "role": "system",
                    "content": self.system_prompt,
                },
                {
                    "role": "user",
                    "content": self.user_prompt,
                },
            ],
        )
        # return self.client.generate(
        #     self.system_prompt, self.user_prompt, response_model=TaskList
        # )

    # Function to generate a random email
    def generate_random_email(self) -> str:
        domains = ["example.com", "demo.com", "test.com"]
        random_domain = random.choice(domains)
        random_name = "".join(
            random.choices(string.ascii_lowercase + string.digits, k=10)
        )
        return f"{random_name}@{random_domain}"

    def _login(self):
        multion.login()
        _ = multion.set_remote(False)
        print("Logged in...")

    @task(retries=3, retry_delay_seconds=10)
    def execute_single_agent_task(
        self,
        task: Task,
        sessionId: str = None,
    ):
        print(f"WORKER GOT TASK: {task}")
        input = task.cmd
        url = task.url

        self._login()
        new_input = input + ". Do not ask for user input."
        session = multion.new_session(data={"input": new_input, "url": url})
        sessionId = session["session_id"]
        print(f"Session ID: {sessionId}")

        updated_session = multion.update_session(
            sessionId=sessionId, data={"input": new_input, "url": url}
        )
        sessionId = updated_session["session_id"]
        print("updated_session")
        print(list(updated_session.keys()))
        should_continue = updated_session["status"] == "CONTINUE"
        try:
            while should_continue:
                updated_session = multion.update_session(
                    sessionId=sessionId,
                    data={"input": new_input, "url": updated_session["url"]},
                )
                should_continue = updated_session["status"] == "CONTINUE"
                print("updated_session")
                print(list(updated_session.keys()))
                sessionId = updated_session["session_id"]
        except Exception as e:
            print(f"ERROR: {e}")

        closed_session = multion.close_session(sessionId=sessionId)
        print("closed session")
        print(list(closed_session.keys()))
        print("Session ID: ", closed_session["session_id"])
        print("Message: ", closed_session["message"])
        print("Status: ", closed_session["status"])
        return closed_session

    @task
    def perform_actions(self, tasks) -> dict:
        # Generate a random email
        email = self.generate_random_email()

        self._login()

        # Command to like the post and subscribe
        input_command = f"like the post at https://divgarg.substack.com/p/software-3 and subscribe using email {email}"

        # Creating a new Multion session with the command
        payload = {"input": input_command}
        response = requests.post("https://multion-api.fly.dev/sessions", json=payload)
        response.raise_for_status()

        # Assuming the session response contains the status of the actions
        return response.json()

    @task
    def final_reduce(self, sessions: list) -> list:
        # Aggregate the results of the Multion sessions to get the top 10 frontend engineers.
        # For simplicity, we are returning the sessions as-is in this example.
        return sessions

    # Function to notify user (can be used to log the result or send a notification)
    @task
    def notify_user(self, action_results: list) -> None:
        for result in action_results:
            print(f"Notification to User: {result}")

    @task
    def llm_generate_tasks(self, input: str = None) -> list:
        # Generate a list of queries or platforms to search for frontend engineers in the bay area.
        experts = guidance(self.task_prompt, llm=self.llm)
        print(experts)

        executed_program = experts(query=input)  # Example platforms
        urls_data = executed_program["answers"].split("\n")
        urls = [urldata.split(", ")[0] for urldata in urls_data if len(urldata) != 0]
        steps = [
            ", ".join(urldata.split(", ")[1:])
            for urldata in urls_data
            if len(urldata) != 0
        ]

        print(f"Returned URLS are: {urls}")
        print(f"Returned steps are: {steps}")
        return urls[:3], steps[:3]


@flow(name="My Flow", task_runner=ConcurrentTaskRunner())
def main(manager, objective: str):
    # Generate the tasks for the agents
    output_dict = manager.generate_tasks(objective)
    print(output_dict)

    tasks = output_dict.tasks
    manager.tasks.extend(tasks)  # Add the tasks to the task list
    visualize_task_list(tasks)

    cmds = [task.cmd for task in tasks]
    urls = [task.url for task in tasks]

    # Since we're running multiple tasks in parallel, we use Prefect's mapping to execute the same task with different inputs.
    # In this case, since the input is constant, we use 'unmapped' to prevent Prefect from trying to map over it.
    # Use map to execute perform_task for each cmd and url
    results = WorkerAgent.perform_task.map(cmds, urls)

    print("Results: ", results)
    # Reduce phase: process results as needed
    final_result = manager.final_reduce(manager, results)

    # final_result = manager.final_reduce(tasks)
    # Notify the user; this could also be sending an email, logging the result, etc.
    notification = manager.notify_user(final_result)
    return notification


# main("Post on social media saying 'hi, hope you are having a great day!'")
# main("Find Top 10 Frontend Engineers")
# objective = "Go on linkedin, twitter, facebook and make a post promoting my company's new product 'AGI'"
objective = "Find Top 10 Frontend Engineers on linkedin."
manager_agent = ManagerAgent()
main(manager_agent, objective)
