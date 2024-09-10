from typing_extensions import TypedDict, Optional
from langgraph.graph import StateGraph, START, END
from langsmith import traceable
from langsmith.wrappers import wrap_openai
import sqlite3
import openai

client = wrap_openai(openai.Client())

class AgentState(TypedDict):
    originalQuery: str
    games: Optional[str]
    summary: Optional[str]

workflow_graph = StateGraph(AgentState)

@traceable
def get_games_from_date(state: AgentState) -> AgentState:
    conn = sqlite3.connect('chess_games.db')
    db = conn.cursor()

    # Query the chess games based on date range (end_time is Unix timestamp)
    query = '''
        SELECT pgn, color, url
        FROM chess_games 
        ORDER BY end_time DESC LIMIT 10
    '''

    db.execute(query)
    games = db.fetchall()
    conn.close()
    return {"games": games}

def summerize_games(state: AgentState) -> AgentState:
    summary_prompt = f"You are a chess teacher. Look through the games provided to find patterns and weaknesses in the player's game. \
        Provide insights into how they can improve in more general senses. Give concrete examples of where in my games I show weakness and specifically how to improve. \
        Don't use generalities like 'Lack of harmony between piece movements'. Instead explain what I did and what a harmonious move or strucutre would have been. \
        Use the games to show and explain how they can improve on those specific areas. If you use a specific example, link to it and notify what part of the match.\
        Here is their specific question: \n\n{state['originalQuery']}. \
        Games: \n\n{state["games"]})"

    result = client.chat.completions.create(
        messages=[{"role": "user", "content": summary_prompt}],
        model="gpt-4o"
    )

    return {"summary": result.choices[0].message.content}

workflow_graph.add_node("Get Games", get_games_from_date)
workflow_graph.add_node("Summarize Games", summerize_games)

workflow_graph.add_edge(START, "Get Games")
workflow_graph.add_edge("Get Games", "Summarize Games")
workflow_graph.add_edge("Summarize Games", END)

graph = workflow_graph.compile()

def run_chess_agent(query: str) -> dict:
    initial_state = {
        "originalQuery": query,
        "games": None,
        "summary": None
    }
    result = graph.invoke(initial_state)
    return result["summary"]

# if __name__ == "__main__":
#     query = "How can i improve on my games?"
#     final_result = graph.invoke({"originalQuery": query})
#     print(final_result)