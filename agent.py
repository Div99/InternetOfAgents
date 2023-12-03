import openai
from functools import lru_cache
from utils import LLMAdapter
import multion


class Agent:
    def __init__(self, agent_type:str="openai", model_name:str="gpt4", model_configs=None) -> None:
        self.client = LLMAdapter(url_or_name=model_name, use_openai=(agent_type=="openai"), configs=model_configs)
        self._login()

    def _login(self):
        multion.login()
        # Check for token verification error here
        response = multion.set_remote(False)
        print("Logged in to MultiON:", response)


class WorkerAgent(Agent):
    def __init__(self, agent_type:str="openai", model_name:str="gpt4", model_configs=None) -> None:
        super().__init__(agent_type=agent_type, model_name=model_name, model_configs=model_configs)
        self.session_id = None

    def _start_session(self, input_command, url):
        response = multion.new_session({"input": input_command, "url": url})
        self.session_id = response['session_id']
        print("New session started:", response['message'])
        print("Session ID:", self.session_id)

    def _update_session(self, input_command, url):
        response = multion.update_session(self.session_id, {"input": input_command, "url": url})
        print("Session updated:", response['message'])
        return response

    def _close_session(self):
        response = multion.close_session(self.session_id)
        print("Session closed:", response)
        self.session_id = None

    @task(retries=3, retry_delay_seconds=10)
    def perform_task(self, input: str, url: str):
        self._start_session(input, url)
        new_input = input + ". Do not ask for user input."

        should_continue = True
        try:
            while should_continue:
                updated_session = self._update_session(new_input, url)
                should_continue = updated_session["status"] == "CONTINUE"
                print("updated_session")
                print(list(updated_session.keys()))
                self.session_id = updated_session["session_id"]
        except Exception as e:
            print(f"ERROR: {e}")

        self._close_session()


class ManagerAgent(Agent):
    def __init__(
        self,
        objective: str = "",
        model_name: str = "gpt-4",
        use_openai=True,
    ):
        # List of tasks to be performed per agent
        self.workers = []
        self.tasks = []

        self.objective = objective

        if use_openai:
            self.llm = guidance.llms.OpenAI(model_name)
        else:
            raise NotImplementedError
            self.llm = ""  # use huggingface via Text Generation Inference Interface

    def generate(self, objective: str) -> TaskList:
        self.system_prompt = "You are an expert task manager that manages agents that each does one task. You decide how many agents is needed to do the meta-task, and what each agent's task is. The agents tasks should be done in parallel"

        self.user_prompt = """
                Create the tasks items for the following objective: {objective}
                """

        return self.llm.generate(
            self.system_prompt,
            self.user_prompt,
            max_tokens=100,
            temperature=0.7,
            top_p=1.0,
            frequency_penalty=0.5,
            presence_penalty=0.0,
            stop=["\n\n"],
        )

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
    def main(self, objective: str):
        cmds, urls = self.generate(objective)

        # Since we're running multiple tasks in parallel, we use Prefect's mapping to execute the same task with different inputs.
        # In this case, since the input is constant, we use 'unmapped' to prevent Prefect from trying to map over it.
        tasks = self.execute_single_agent_task.map(input=cmds, url=urls)
        self.tasks.extend(tasks)  # Add the tasks to the task list

        final_result = self.final_reduce(tasks)
        # Notify the user; this could also be sending an email, logging the result, etc.
        notification = self.notify_user(final_result)
        return notification

    # Run the flow
    def run(self, objective: str):
        self.main(objective)