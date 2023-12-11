import multion
from prefect import task

class WorkerAgent:
    def __init__(self):
        self._login()

    @staticmethod
    def _login():
        multion.login()
        response = multion.set_remote(False)
        print("Logged in to MultiON:", response)

    @task
    @staticmethod
    def perform_task(input: str, url: str):
        session_id = WorkerAgent._start_session(input, url)
        new_input = input + ". Do not ask for user input."

        should_continue = True
        try:
            while should_continue:
                updated_session = WorkerAgent._update_session(
                    session_id, new_input, url
                )
                should_continue = updated_session["status"] == "CONTINUE"
                print("updated_session")
                print(list(updated_session.keys()))
                session_id = updated_session["session_id"]
        except Exception as e:
            print(f"ERROR: {e}")

        WorkerAgent._close_session(session_id)

    @staticmethod
    def _start_session(input_command, url):
        response = multion.new_session({"input": input_command, "url": url})
        print("New session started:", response["message"])
        return response["session_id"]

    @staticmethod
    def _update_session(session_id, input_command, url):
        response = multion.update_session(
            session_id, {"input": input_command, "url": url}
        )
        print("Session updated:", response["message"])
        return response

    @staticmethod
    def _close_session(session_id):
        return
        # response = multion.close_session(session_id)
        # print("Session closed:", response)
