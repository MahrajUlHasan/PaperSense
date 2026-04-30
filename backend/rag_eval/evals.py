import os
import sys
import asyncio
from pathlib import Path
import pandas as pd

from openai import AsyncOpenAI
from ragas.llms import llm_factory
from ragas.embeddings import embedding_factory

# Import metric classes directly for manual scoring
from ragas.metrics.collections import (
    Faithfulness,
    AnswerRelevancy,
    ContextPrecision,
    ContextRecall,
    NoiseSensitivity
)

from rag_adapter import PaperSenseRAGAdapter

# Initialize Async OpenAI Client for Ragas Scorers
client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Setup LLM and Embeddings specifically for the metrics
llm = llm_factory("gpt-4o", client=client)
embeddings = embedding_factory("openai","text-embedding-3-small", client=client)

# Instantiate the individual metric scorers
faithfulness_scorer = Faithfulness(llm=llm)
relevancy_scorer = AnswerRelevancy(llm=llm, embeddings=embeddings)
precision_scorer = ContextPrecision(llm=llm, embeddings=embeddings)
recall_scorer = ContextRecall(llm=llm, embeddings=embeddings)


def load_dataset():
    """Returns 10 specific Q&A pairs for 'Attention Is All You Need'."""
    return [
        {
            "question": "What is the main architecture proposed in this paper?",
            "ground_truth": "The Transformer, an architecture based entirely on attention mechanisms, dispensing with recurrence and convolutions."
        },
        {
            "question": "What type of attention mechanism does the Transformer rely on?",
            "ground_truth": "It relies on Multi-Head Attention, which consists of several parallel Scaled Dot-Product Attention layers."
        },
        {
            "question": "What are the advantages of self-attention over recurrent layers according to the paper?",
            "ground_truth": "Self-attention reduces the total computational complexity per layer, allows for more parallelizable computation, and shortens the path length between long-range dependencies."
        },
        {
            "question": "What hardware was used to train the models?",
            "ground_truth": "The models were trained on one machine with 8 NVIDIA P100 GPUs."
        },
        {
            "question": "How does the Transformer architecture differ from previous dominant sequence models?",
            "ground_truth": "The Transformer abandons complex recurrent and convolutional neural networks, relying entirely on attention mechanisms to draw global dependencies between input and output[cite: 5]."
        },
        {
            "question": "What is self-attention?",
            "ground_truth": "Self-attention, also called intra-attention, is a mechanism that relates different positions of a single sequence to compute a representation of that entire sequence[cite: 5]."
        },
        {
            "question": "In general terms, how does an attention function work?",
            "ground_truth": "An attention function maps a query and a set of key-value pairs to an output, which is calculated as a weighted sum of the values[cite: 5]."
        },
        {
            "question": "What are the two sub-layers present in each layer of the encoder?",
            "ground_truth": "The first sub-layer is a multi-head self-attention mechanism, and the second is a simple, position-wise fully connected feed-forward network[cite: 5]."
        },
        {
            "question": "What structural components immediately follow each sub-layer in the encoder and decoder?",
            "ground_truth": "Each sub-layer is wrapped with a residual connection and is immediately followed by layer normalization[cite: 5]."
        },
        {
            "question": "What additional sub-layer is inserted into the decoder that is not present in the encoder?",
            "ground_truth": "The decoder contains a third sub-layer that performs multi-head attention over the output of the encoder stack[cite: 5]."
        },
        {
            "question": "Why did the authors choose to use sinusoidal functions for positional encodings rather than learned embeddings?",
            "ground_truth": "They hypothesized that sinusoidal functions would allow the model to easily learn to attend by relative positions and help the model extrapolate to sequence lengths longer than those encountered during training[cite: 5]."
        },
        {
            "question": "What type of encoding was used to prepare the sentences in the English-German translation dataset?",
            "ground_truth": "The sentences were encoded using byte-pair encoding with a shared source-target vocabulary[cite: 5]."
        },
        {
            "question": "How did the authors organize the sentence pairs during the training process to handle different lengths?",
            "ground_truth": "Sentence pairs were batched together based on their approximate sequence length[cite: 5]."
        },
        {
            "question": "What specific regularization technique was used that makes the model more unsure of its predictions but ultimately improves accuracy and translation scores?",
            "ground_truth": "The authors employed label smoothing during training[cite: 5]."
        }

    ]


def extract_value(result):
    """Helper to safely extract the numerical value from the Ragas Result object"""
    return getattr(result, "value", result)


async def run_evaluation_mode(adapter, raw_data, use_hybrid: bool, mode_name: str):
    """Runs the RAG pipeline and scores it concurrently question-by-question."""
    print(f"\n==============================================")
    print(f"RUNNING EVALUATION MODE: {mode_name}")
    print(f"==============================================")

    results_list = []

    for row in raw_data:
        question = row["question"]
        reference = row["ground_truth"]
        print(f"\nAsking: {question}")

        # 1. Gather response from the RAG Pipeline (Synchronous execution)
        response = adapter.query(question, use_hybrid=use_hybrid)
        ans = response.get("answer", "")
        contexts = response.get("contexts", [])

        print("  -> Scoring with Ragas...")

        # 2. Score concurrently across all metrics for this single question
        # Faithfulness and Relevancy only need inputs/response/contexts
        task_f = faithfulness_scorer.ascore(
            user_input=question,
            response=ans,
            retrieved_contexts=contexts
        )
        task_r = relevancy_scorer.ascore(
            user_input=question,
            response=ans
        )
        # Precision and Recall also require the ground truth reference
        task_p = precision_scorer.ascore(
            user_input=question,
            retrieved_contexts=contexts,
            reference=reference
        )
        task_c = recall_scorer.ascore(
            user_input=question,
            retrieved_contexts=contexts,
            reference=reference
        )

        # Run the metric evaluations concurrently
        f_res, r_res, p_res, c_res = await asyncio.gather(task_f, task_r, task_p, task_c)

        # Ragas 0.3+ returns a custom result object for `.ascore`, we extract `.value`
        f_score = extract_value(f_res)
        r_score = extract_value(r_res)
        p_score = extract_value(p_res)
        c_score = extract_value(c_res)

        print(f"  -> Faithfulness: {f_score} | Relevancy: {r_score} | Precision: {p_score} | Recall: {c_score}")

        results_list.append({
            "question": question,
            "answer": ans,
            "ground_truth": reference,
            "faithfulness": f_score,
            "answer_relevancy": r_score,
            "context_precision": p_score,
            "context_recall": c_score,
            "search_mode": mode_name
        })

    return pd.DataFrame(results_list)


async def main():
    print("Initializing PaperSense RAG Adapter...")
    adapter = PaperSenseRAGAdapter()

    test_paper_path = Path(__file__).parent / "evals" /"datasets" / "test_paper.pdf"

    if not test_paper_path.exists():
        print(f"Error: Test paper not found at {test_paper_path}")
        print("Please download 'Attention Is All You Need' and save it as 'test_paper.pdf'.")
        return

    print(f"\nIngesting {test_paper_path.name} into vector store...")
    adapter.ingest_test_paper(str(test_paper_path))

    raw_data = load_dataset()

    # Run Both Modes using asyncio
    df_dense = await run_evaluation_mode(adapter, raw_data, use_hybrid=False, mode_name="Dense Search")
    df_hybrid = await run_evaluation_mode(adapter, raw_data, use_hybrid=True, mode_name="Hybrid Search")

    # Combine and save results
    final_df = pd.concat([df_dense, df_hybrid], ignore_index=True)

    results_dir = Path(__file__).parent /"evals" / "experiments"
    results_dir.mkdir(parents=True, exist_ok=True)

    csv_path = results_dir / "comparison_eval_results.csv"
    final_df.to_csv(csv_path, index=False)

    print(f"\n✅ Experiment complete! Comparison results saved to: {csv_path.resolve()}")

    # Print a quick summary of averages
    print("\n--- Summary Averages ---")
    summary = final_df.groupby("search_mode").mean(numeric_only=True)
    print(summary)


if __name__ == "__main__":
    # Standard entry point for asyncio python scripts
    asyncio.run(main())