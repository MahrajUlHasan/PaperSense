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
            "question": "Why do the authors use a scaling factor of 1/sqrt(d_k) in the attention mechanism?",
            "ground_truth": "To prevent the dot products from growing too large in magnitude, which would push the softmax function into regions where it has extremely small gradients."
        },
        {
            "question": "How does the model inject information about the relative or absolute position of the tokens?",
            "ground_truth": "By adding positional encodings to the input embeddings at the bottoms of the encoder and decoder stacks, using sine and cosine functions of different frequencies."
        },
        {
            "question": "What optimizer is used to train the Transformer model?",
            "ground_truth": "The Adam optimizer with specific parameters (beta1=0.9, beta2=0.98, eps=10^-9) and a custom learning rate schedule."
        },
        {
            "question": "What regularization techniques are employed during training?",
            "ground_truth": "Residual dropout (applied to the output of each sub-layer and the sums of embeddings and positional encodings) and label smoothing."
        },
        {
            "question": "How many layers (N) are in the encoder and decoder stacks of the base model?",
            "ground_truth": "Both the encoder and decoder are composed of a stack of N=6 identical layers."
        },
        {
            "question": "What is the BLEU score achieved by the Transformer (big) model on the English-to-German translation task?",
            "ground_truth": "It achieved a BLEU score of 28.4 on the WMT 2014 English-to-German translation task."
        },
        {
            "question": "What are the advantages of self-attention over recurrent layers according to the paper?",
            "ground_truth": "Self-attention reduces the total computational complexity per layer, allows for more parallelizable computation, and shortens the path length between long-range dependencies."
        },
        {
            "question": "What hardware was used to train the models?",
            "ground_truth": "The models were trained on one machine with 8 NVIDIA P100 GPUs."
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