from prefect import task, flow
import requests
import random
import string
import multion
from prefect.task_runners import ConcurrentTaskRunner
from enum import Enum
from typing import Optional
import guidance

import instructor
from openai import OpenAI
from pydantic import BaseModel


class Status(Enum):
    NOT_ACTIVE = "NOT_ACTIVE"
    PENDING = "PENDING"
    DONE = "DONE"
    FAILED = "FAILED"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"


class Task(BaseModel):
    name: str = ""
    cmd: str
    status: Status = Status.NOT_ACTIVE


class ManagerAgent:
    def __init__(self, objective: str = "Like_and_Subscribe"):
        # List of tasks to be performed per agent
        self.workers = []
        self.tasks = []

        self.objective = objective
        self.task_prompt = """
            {{#system~}}
            You are an expert task manager that manages agents that each does one task. You decide how many agents is needed to do the meta-task, and what each agent's task is. The agents tasks should be done in parallel
            {{~/system}}

            {{#user~}}
            Book a cheap car from Civic Center to Embacadero Station
            Answer:
            Retrieve the price to get a car from Civic Center to Embacadero Station using Uber
            Retrieve the price to get a car from Civic Center to Embacadero Station using Lyft

            {{query}}
            Answer:
            {{~/user}}

            {{#assistant~}}
            {{gen 'answers' temperature=0 max_tokens=300}}
            {{~/assistant}}
            """

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
        self, input: str = None, url: str = "https://www.google.com", tabId: str = None
    ):
        self._login()
        new_input = input + ". Do not ask for user input."
        session = multion.new_session(data={"input": new_input, "url": url})
        tabId = session["session_id"]
        print(f"Session ID: {tabId}")

        updated_session = multion.update_session(
            tabId=tabId, data={"input": new_input, "url": url}
        )
        tabId = updated_session["session_id"]
        print("updated_session")
        print(list(updated_session.keys()))
        should_continue = updated_session["status"] == "CONTINUE"
        try:
            while should_continue:
                updated_session = multion.update_session(
                    tabId=tabId,
                    data={"input": new_input, "url": updated_session["url"]},
                )
                should_continue = updated_session["status"] == "CONTINUE"
                print("updated_session")
                print(list(updated_session.keys()))
                tabId = updated_session["session_id"]
        except Exception as e:
            print(f"ERROR: {e}")

        closed_session = multion.close_session(tabId=tabId)
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

    from prefect import Flow, unmapped

    def create_tasks_per_worker(self, objective, num_workers: int = 3):
        # Enables `response_model`
        client = instructor.patch(OpenAI())

        prompt = "You"
        task = client.chat.completions.create(
            model="gpt-4-turbo",
            response_model=Task,
            messages=[
                {"role": "user", "content": "Extract Jason is 25 years old"},
            ],
        )

        assert isinstance(user, UserDetail)
        assert user.name == "Jason"
        assert user.age == 25

        for i in range(num_workers):
            self.workers.append(Task(f"Worker {i}"))

        @task
        def generate_a_list(input: str = None) -> list:
            # Generate a list of queries or platforms to search for frontend engineers in the bay area.
            experts = guidance(list_prompt, llm=gpt4)
            executed_program = experts(query=input)  # Example platforms
            urls_data = executed_program["answers"].split("\n")
            urls = [
                urldata.split(", ")[0] for urldata in urls_data if len(urldata) != 0
            ]
            steps = [
                ", ".join(urldata.split(", ")[1:])
                for urldata in urls_data
                if len(urldata) != 0
            ]

            print(f"Returned URLS are: {urls}")
            print(f"Returned steps are: {steps}")
            return urls[:3], steps[:3]

    @flow(name="My Flow", task_runner=ConcurrentTaskRunner())
    def main(self, task="Like_and_Subscribe"):
        # Generate a list of tasks to be performed

        # Generate a random email
        email = self.generate_random_email()

        input_command = f"like the post at https://divgarg.substack.com/p/software-3 and subscribe using email {email}"

        tasks = [input_command] * 3
        urls = ["https://divgarg.substack.com/p/software-3"] * 3

        # Since we're running multiple tasks in parallel, we use Prefect's mapping to execute the same task with different inputs.
        # In this case, since the input is constant, we use 'unmapped' to prevent Prefect from trying to map over it.
        sessions = self.execute_single_agent_task.map(input=tasks, url=urls)
        self.tasks.extend(sessions)  # Add the tasks to the task list

        final_result = self.final_reduce(sessions)
        # Notify the user; this could also be sending an email, logging the result, etc.
        notification = self.notify_user(final_result)

    # Run the flow
    def run(self):
        self.main()


manager_agent = ManagerAgent()
manager_agent.run()
