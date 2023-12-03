from prefect import task, flow
import requests
import random
import string
import multion
from prefect.task_runners import ConcurrentTaskRunner


# Function to generate a random email
def generate_random_email() -> str:
    domains = ["example.com", "demo.com", "test.com"]
    random_domain = random.choice(domains)
    random_name = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return f"{random_name}@{random_domain}"


def _login():
    multion.login()
    _ = multion.set_remote(False)
    print("Logged in...")


@task(retries=3, retry_delay_seconds=10)
def execute_single_agent_task(
    input: str = None, url: str = "https://www.google.com", tabId: str = None
):
    _login()
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
                tabId=tabId, data={"input": new_input, "url": updated_session["url"]}
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
def perform_actions(tasks) -> dict:
    # Generate a random email
    email = generate_random_email()

    _login()

    # Command to like the post and subscribe
    input_command = f"like the post at https://divgarg.substack.com/p/software-3 and subscribe using email {email}"

    # Creating a new Multion session with the command
    payload = {"input": input_command}
    response = requests.post("https://multion-api.fly.dev/sessions", json=payload)
    response.raise_for_status()

    # Assuming the session response contains the status of the actions
    return response.json()


@task
def final_reduce(sessions: list) -> list:
    # Aggregate the results of the Multion sessions to get the top 10 frontend engineers.
    # For simplicity, we are returning the sessions as-is in this example.
    return sessions


# Function to notify user (can be used to log the result or send a notification)
@task
def notify_user(action_results: list) -> None:
    for result in action_results:
        print(f"Notification to User: {result}")


from prefect import Flow, unmapped


@flow(name="My Flow", task_runner=ConcurrentTaskRunner())
def main(task="Like_and_Subscribe"):
    # Generate a list of tasks to be performed

    # Generate a random email
    email = generate_random_email()

    input_command = f"like the post at https://divgarg.substack.com/p/software-3 and subscribe using email {email}"

    tasks = [input_command] * 3
    urls = ["https://divgarg.substack.com/p/software-3"] * 3

    # Since we're running multiple tasks in parallel, we use Prefect's mapping to execute the same task with different inputs.
    # In this case, since the input is constant, we use 'unmapped' to prevent Prefect from trying to map over it.
    sessions = execute_single_agent_task.map(input=tasks, url=urls)
    final_result = final_reduce(sessions)
    # Notify the user; this could also be sending an email, logging the result, etc.
    notification = notify_user(final_result)


# Run the flow
main()
