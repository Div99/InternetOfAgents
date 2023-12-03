import multion
from prefect import task


# class WorkerAgent:
#     def __init__(self):
#         self.session_id = None
#         self._login()

#     def _login(self):
#         multion.login()
#         # Check for token verification error here
#         response = multion.set_remote(False)
#         print("Logged in to MultiON:", response)

#     def _start_session(self, input_command, url):
#         response = multion.new_session({"input": input_command, "url": url})
#         self.session_id = response["session_id"]
#         print("New session started:", response["message"])
#         print("Session ID:", self.session_id)

#     def _update_session(self, input_command, url):
#         response = multion.update_session(
#             self.session_id, {"input": input_command, "url": url}
#         )
#         print("Session updated:", response["message"])
#         return response

#     def _close_session(self):
#         response = multion.close_session(self.session_id)
#         print("Session closed:", response)
#         self.session_id = None

#     @task
#     def perform_task(self, input: str, url: str):
#         print("perform_task", self, input, url)
#         self._start_session(input, url)
#         new_input = input + ". Do not ask for user input."

#         should_continue = True
#         try:
#             while should_continue:
#                 updated_session = self._update_session(new_input, url)
#                 should_continue = updated_session["status"] == "CONTINUE"
#                 print("updated_session")
#                 print(list(updated_session.keys()))
#                 self.session_id = updated_session["session_id"]
#         except Exception as e:
#             print(f"ERROR: {e}")

#         self._close_session()


# # Example usage of the WorkerAgent
# worker = WorkerAgent()
# input_command = "what is the weather today"
# url = "https://www.google.com"
# worker.perform_task(input=input_command, url=url)

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
                updated_session = WorkerAgent._update_session(session_id, new_input, url)
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
        print("New session started:", response['message'])
        return response['session_id']

    @staticmethod
    def _update_session(session_id, input_command, url):
        response = multion.update_session(session_id, {"input": input_command, "url": url})
        print("Session updated:", response['message'])
        return response

    @staticmethod
    def _close_session(session_id):
        response = multion.close_session(session_id)
        print("Session closed:", response)
