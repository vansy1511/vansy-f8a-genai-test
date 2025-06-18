# agent_evaluator.py

import pandas as pd
import time
from datetime import datetime  # NEW: Import the datetime module
from langchain.callbacks import get_openai_callback

def evaluate_agent(agent_executor, csv_filepath):
    """
    Evaluates a LangChain agent based on a CSV file.

    Args:
        agent_executor (AgentExecutor): The agent executor to be evaluated.
                                        It MUST be initialized with `return_intermediate_steps=True`.
        csv_filepath (str): The path to the evaluation CSV file.
                            The CSV must contain 'question' and 'expected_tool' columns.

    Returns:
        tuple: A tuple containing:
            - dict: A dictionary with summary statistics (cost, avg latency, tool accuracy).
            # MODIFIED: Updated docstring to reflect the new column
            - pd.DataFrame: A DataFrame with detailed results, including the new
                            'tool_selection_datetime' column.
    """
    try:
        df = pd.read_csv(csv_filepath)
        # df = df.head(1)
        print(len(df))
    except FileNotFoundError:
        print(f"Error: The file '{csv_filepath}' was not found.")
        return None, None
        
    results_data = []
    latencies = []
    correct_tool_selections = 0
    total_tool_selections = 0

    print(f"Starting evaluation on {len(df)} questions...")

    with get_openai_callback() as cb:
        for index, row in df.iterrows():
            question = row['question']
            expected_tool = row['expected_tool']

            print(f"\n[Test {index+1}/{len(df)}] Question: {question}")
            
            start_time = time.time()
            try:
                response = agent_executor.invoke({"input": question})
            except Exception as e:
                print(f"  ERROR processing question: {e}")
                continue
            
            end_time = time.time()
            latency = end_time - start_time
            latencies.append(latency)
            
            # --- Check for tool usage ---
            actual_tool = "No Tool Used"
            is_correct = False
            selection_datetime = "N/A" # NEW: Initialize a default value for the timestamp

            if response.get('intermediate_steps'):
                action = response['intermediate_steps'][0][0]
                actual_tool = action.tool
                if actual_tool not in ["HospitalGraphQA", "HospitalReviewsQA"]:
                    actual_tool = "no"
                total_tool_selections += 1
                
                # NEW: Capture the current time and format it as a string
                selection_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                if actual_tool == expected_tool:
                    correct_tool_selections += 1
                    is_correct = True
            
            print(f"  -> Expected Tool: {expected_tool}")
            print(f"  -> Actual Tool:   {actual_tool}")
            print(f"  -> Selected At:   {selection_datetime}") # NEW: Print the timestamp
            print(f"  -> Correct:       {is_correct}")
            print(f"  -> Latency:       {latency:.2f}s")

            # MODIFIED: Add the new timestamp column to the results data
            results_data.append({
                "num": index,
                "question": question,
                "expected_tool": expected_tool,
                "actual_tool": actual_tool,
                "tool_selection_datetime": selection_datetime, # I used a more standard name
                "is_correct": is_correct,
                "latency_sec": latency,
                "final_answer": response.get('output', 'N/A')
            })

    tool_accuracy = (correct_tool_selections / total_tool_selections * 100) if total_tool_selections > 0 else 0
    avg_latency = sum(latencies) / len(latencies) if latencies else 0

    summary_stats = {
        "total_questions": len(df),
        "total_cost_usd": cb.total_cost,
        "total_tokens": cb.total_tokens,
        "average_latency_sec": avg_latency,
        "tool_selection_accuracy_percent": tool_accuracy,
    }
    
    detailed_results_df = pd.DataFrame(results_data)
    
    print("\n--- Evaluation Complete ---")
    
    return summary_stats, detailed_results_df