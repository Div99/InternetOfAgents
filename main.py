from prefect import task, flow
import multion
from datetime import timedelta
import openai


agent_task_prompt = """
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

def _login():
    multion.login()
    _ = multion.set_remote(False)

@task(retries=3, retry_delay_seconds=10)
def execute_single_agent_task(input: str = None, url: str = "https://www.google.com", tabId: str = None):
    _login()
    session = multion.new_session(data={"input": input, "url": url})
    print(session.keys())
    tabId = session['tabId']

    updated_session = multion.update_session(tabId=tabId, data={"input": input, "url": url})
    print("updated_session")
    print(updated_session)
    should_continue = updated_session["status"] == "CONTINUE"
    while should_continue:
        updated_session = multion.update_session(tabId=tabId, data={"input": input, "url": url})
        should_continue = updated_session["status"] == "CONTINUE"
        print("updated_session")
        print(updated_session)
        
    closed_session = multion.close_session(tabId=tabId)
    print("closed session")
    print(closed_session)


@flow(log_prints=True)
def orchestration_task(input: str = None):
    # decide through LLM how many agents to spawn
    experts = guidance(agent_task_prompt, llm=gpt4)
    executed_program = experts(query=input)
    print(executed_program)
    
    # call? figure out all of the agents' task, with their input, each input can be different

    # figure out the input tasks per agent
    
    # run the agent in parallel -- prefect <---- TODO: figure out how to do this
    
    # get results aggregated by the main agent

    # return the results
    execute_single_agent_task(input)

if __name__ == "__main__":
    orchestration_task.serve(name="orchestration_task",
                      tags=["multion"],
                      parameters={"input": "Send the top 3 ai engineers on linkedin a message."},
                      interval=60)