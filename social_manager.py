import csv
from manager import ManagerAgent, main

# Usage
objective = "Go on linkedin, twitter, facebook and make a post promoting my company's new product 'AGI'"
manager_agent = ManagerAgent()
main(manager_agent, objective)
