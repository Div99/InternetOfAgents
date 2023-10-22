from prefect import task
import requests
import random
import string


# Function to generate a random email
def generate_random_email() -> str:
    domains = ["example.com", "demo.com", "test.com"]
    random_domain = random.choice(domains)
    random_name = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return f"{random_name}@{random_domain}"


@task
def perform_actions() -> dict:
    # Generate a random email
    email = generate_random_email()

    # Command to like the post and subscribe
    input_command = f"like the post at https://divgarg.substack.com/p/software-3 and subscribe using email {email}"

    # Creating a new Multion session with the command
    payload = {"input": input_command}
    response = requests.post("https://multion-api.fly.dev/sessions", json=payload)
    response.raise_for_status()

    # Assuming the session response contains the status of the actions
    return response.json()


# Function to notify user (can be used to log the result or send a notification)
@task
def notify_user(action_results: list) -> None:
    for result in action_results:
        print(f"Notification to User: {result}")


from prefect import Flow

with Flow("Like_and_Subscribe") as flow:
    # Since we're running three tasks in parallel, we use Prefect's mapping to execute the same task with different inputs.
    # In this case, since the input is constant, we use 'unmapped' to prevent Prefect from trying to map over it.
    action_results = perform_actions.map(unmapped("constant_input"))

    # Notify the user; this could also be sending an email, logging the result, etc.
    notification = notify_user(action_results)

# Run the flow
flow.run()
