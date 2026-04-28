import os
import sys
from pathlib import Path

from openai import OpenAI

from ragas import Dataset, experiment
from ragas.llms import llm_factory
from ragas.metrics import DiscreteMetric
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall
)
from ragas import evaluate, EvaluationDataset
from ragas.dataset_schema import SingleTurnSample
from ragas.embeddings import embedding_factory

from google import genai
from rag_adapter import PaperSenseRAGAdapter


# Add the current directory to the path so we can import rag module when run as a script
sys.path.insert(0, str(Path(__file__).parent))
from rag import default_rag_client
from config import settings


openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
# openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
rag_client = default_rag_client(llm_client=openai_client, logdir="evals/logs")
llm = llm_factory("gpt-4o", client=openai_client)
# embeddings = embedding_factory("openai", client=openai_client)
# embeddings = genai.Client(api_key=settings.google_api_key)


def load_dataset():
    dataset = Dataset(
        name="test_dataset",
        backend="local/csv",
        root_dir="evals",
    )

    data_samples = [
        {
            "question": "What is the main architecture proposed in this paper?",
            "ground_truth": "The main architecture proposed is the Transformer, which is based solely on attention mechanisms, dispensing with recurrence and convolutions entirely."
        },
        {
            "question": "What are the advantages of self-attention according to the authors?",
            "ground_truth": "Self-attention reduces computational complexity per layer, allows for more parallelization, and yields shorter path lengths between long-range dependencies in the network."
        },
        {
            "question": "Which optimizer was used for training the models?",
            "ground_truth": "The Adam optimizer was used with varying learning rates."
        }
    ]

    for sample in data_samples:
        row = {"question": sample["question"], "ground_truth": sample["ground_truth"]}
        dataset.append(row)

    # make sure to save it
    dataset.save()
    return dataset


my_metric = DiscreteMetric(
    name="correctness",
    prompt="Check if the response contains points mentioned from the grading notes and return 'pass' or 'fail'.\nResponse: {response} Grading Notes: {grading_notes}",
    allowed_values=["pass", "fail"],
)


@experiment()
async def run_experiment(row):
    response = rag_client.query(row["question"])
    score = my_metric.score(
        llm=llm,
        response=response.get("answer", " "),
        grading_notes=row["grading_notes"],
    )
    score2 =my_metric.score(
        llm=llm,
        response=response2.get("answer", " "),
        grading_notes=row["grading_notes"],
    )

    experiment_view = {
        **row,
        "response": response.get("answer", ""),
        "score": score.value,
        "log_file": response.get("logs", " "),
    }
    return experiment_view


async def main():
    print("Initializing PaperSense RAG Adapter...")
    adapter = PaperSenseRAGAdapter()

    # Step 1: Ingest the test document
    test_paper_path = Path(__file__).parent / "evals" /"datasets" / "test_paper.pdf"

    if not test_paper_path.exists():
        print(f"Error: Test paper not found at {test_paper_path}")
        print("Please place a 'test_paper.pdf' in the datasets folder.")
        return

    print(f"\nIngesting {test_paper_path.name} into Qdrant...")
    adapter.ingest_test_paper(str(test_paper_path))

    # Step 2: Prepare the queries
    print("\nLoading test dataset...")
    raw_data = load_dataset()

    prepared_data = {
        "question": [],
        "answer": [],
        "contexts": [],
        "ground_truth": []
    }

    # Step 3: Run pipeline queries to gather real contexts and generated answers
    print("\nQuerying RAG Pipeline...")
    samples = []

    for row in raw_data:
        question = row["question"]
        print(f"Asking: {question}")

        response = adapter.query(question )

        # Ragas 0.3+ Schema Requirements
        sample = SingleTurnSample(
            user_input=question,
            response=response["answer"],
            retrieved_contexts=response["contexts"],
            reference=row["ground_truth"]
        )
        samples.append(sample)

    # Step 4: Convert into Ragas Dataset and Evaluate
    dataset = EvaluationDataset(samples = samples)

    metrics = [
        faithfulness,  # Checks if the answer hallucinates beyond contexts
        answer_relevancy,  # Checks if answer is actually relevant to question
        context_precision,  # Checks if contexts retrieved were highly relevant
        context_recall  # Checks if retrieved contexts covered the ground truth
    ]

    print("\nEvaluating with Ragas (This may take a minute)...")
    results = evaluate(
        dataset=dataset,
        metrics=metrics,
        llm=llm,
        experiment_name="papersense_eval"
    )

    print("\nEvaluation Results:")
    print(results)

    # Step 5: Save results to CSV for analysis
    results_dir = Path(__file__).parent /"evals"/ "experiments"
    results_dir.mkdir(parents=True, exist_ok=True)

    csv_path = results_dir / "eval_results.csv"
    df = results.to_pandas()
    df.to_csv(csv_path, index=False)

    print(f"\nExperiment results successfully saved to: {csv_path.resolve()}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
