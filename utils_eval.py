from collections import Counter
from evaluate import load
import numpy as np
import textstat
import nltk
from rouge_score import rouge_scorer, scoring
from typing import List, Dict, Tuple

metric_bertscore = load("bertscore")
metric_sari = load("sari")


def add_newline_to_end_of_each_sentence(s):
    """This was added to get rougeLsum scores matching published rougeL scores for BART and PEGASUS."""
    s = s.replace("\n", "")
    return "\n".join(nltk.sent_tokenize(s))


def calculate_rouge(
    predictions,
    references,
):
    """Calculate rouge using rouge_scorer package.
    Args:
        pred_lns: list of summaries generated by model
        tgt_lns: list of groundtruth summaries (e.g. contents of val.target)
    Returns:
         Dict[score: value] if aggregate else defaultdict(list) keyed by rouge_keys
    """
    scorer = rouge_scorer.RougeScorer(
        ["rouge1", "rouge2", "rougeL", "rougeLsum"], use_stemmer=True
    )
    aggregator = scoring.BootstrapAggregator()
    for pred, tgt in zip(predictions, references):
        pred = add_newline_to_end_of_each_sentence(pred)
        tgt = [add_newline_to_end_of_each_sentence(s) for s in tgt]
        scores = scorer.score_multi(tgt, pred)
        aggregator.add_scores(scores)

    result = aggregator.aggregate()
    return {k: round(v.mid.fmeasure * 100, 4) for k, v in result.items()}


def get_readability_score(text, metric="flesch_reading_grade"):
    """get the readability score and grade level of text"""
    if metric == "flesch_reading_ease":
        score = textstat.flesch_reading_ease(text)
        if score > 90:
            grade = "5th grade"
        elif score > 80:
            grade = "6th grade"
        elif score > 70:
            grade = "7th grade"
        elif score > 60:
            grade = "8th & 9th grade"
        elif score > 50:
            grade = "10th to 12th grade"
        elif score > 30:
            grade = "college"  # Collge student = average 13th to 15th grade
        elif score > 10:
            grade = "college graduate"
        else:
            grade = "professional"
        return score, grade

    elif metric == "flesch_kincaid_grade":
        score = textstat.flesch_kincaid_grade(
            text
        )  # Note: this score can be negative like -1
        grade = round(score)
        if grade > 16:
            grade = "college graduate"  # Collge graduate: >16th grade
        elif grade > 12:
            grade = "college"
        elif grade <= 4:
            grade = "4th grade or lower"
        else:
            grade = f"{grade}th grade"
        return score, grade

    elif metric == "ari":
        sents = nltk.sent_tokenize(text)
        words = nltk.word_tokenize(text)
        num_sents = len(sents)
        num_words = len(words)
        num_chars = sum(len(w) for w in words)
        score = (
            4.71 * (num_chars / float(num_words))
            + 0.5 * (float(num_words) / num_sents)
            - 21.43
        )
        return score, "None"

    # elif metric == 'SMOG': # Note: SMOG formula needs at least three ten-sentence-long samples for valid calculation
    #     score = textstat.smog_index(text)
    #     grade = round(score)
    #     if grade > 16:
    #         grade = 'college graduate'
    #     elif grade > 12:
    #         grade = 'college'
    #     else:
    #         grade = f"{grade}th grade"
    #     return score, grade

    elif metric == "dale_chall":
        score = textstat.dale_chall_readability_score(text)
        if score >= 10:
            grade = "college graduate"
        elif score >= 9:
            grade = "college"  # Collge student = average 13th to 15th grade
        elif score >= 8:
            grade = "11th to 12th grade"
        elif score >= 7:
            grade = "9th to 10th grade"
        elif score >= 6:
            grade = "7th to 8th grade"
        elif score >= 5:
            grade = "5th to 6th grade"
        else:
            grade = "4th grade or lower"
        return score, grade

    elif metric == "gunning_fog":
        score = textstat.gunning_fog(text)
        grade = round(score)
        if grade > 16:
            grade = "college graduate"
        elif grade > 12:
            grade = "college"
        elif grade <= 4:
            grade = "4th grade or lower"
        else:
            grade = f"{grade}th grade"
        return score, grade

    else:
        raise ValueError(f"Unknown metric {metric}")


def calculate_sari(sources, predictions, references):
    result_sari = metric_sari.compute(
        sources=sources, predictions=predictions, references=references
    )
    return result_sari


def clean_string(s):
    return s.replace("<s>", "").replace("</s>", "").replace("<pad>", "")


def compute_metrics(
    sources: List[str],
    predictions: List[str],
    labels: List[List[str]],
    metrics: List[str],
) -> Dict:
    """Test docstring.

    Args:
        sources (list[str]): List of input sources
        predictions (list[str]): List of output sources
        labels (list[list[str]]): List of list of reference strings
    Returns:
        dict: Output of computed metrics
    """

    assert type(sources) == list and type(sources[0]) == str, print(
        "Sources should be a list of strings"
    )
    assert type(predictions) == list and type(predictions[0]) == str, print(
        "Predictions should be a list of strings"
    )
    assert type(labels) == list and type(labels[0]) == list, print(
        "Labels should be a list of LISTS, each containing the labels"
    )

    # Clean inputs
    sources = [clean_string(s) for s in sources]
    predictions = [clean_string(s) for s in predictions]
    labels = [[clean_string(s) for s in lst] for lst in labels]

    result = {}

    if "rouge" in metrics:
        result_rouge = calculate_rouge(predictions, labels)
        for key in result_rouge.keys():
            result[key] = result_rouge[key]
    if "sari" in metrics:
        result_sari = calculate_sari(
            sources=sources, predictions=predictions, references=labels
        )
        result["sari"] = result_sari["sari"]
    if "bert_score" in metrics:
        result_bert = []
        for (pred, label) in zip(predictions, labels):
            result_bert_temp = metric_bertscore.compute(
                predictions=[pred] * len(label), references=label, lang="en"
            )
            if type(result_bert_temp["f1"]) == list:
                result_bert.append(result_bert_temp["f1"][0])
            else:
                result_bert.append(result_bert_temp["f1"])
        result["bert_score"] = np.mean(result_bert)

    if "bert_score_l" in metrics:
        result_bert_l = []
        for (pred, source) in zip(predictions, sources):
            result_bert_temp = metric_bertscore.compute(
                predictions=[pred], references=[source], lang="en"
            )
            if type(result_bert_temp["f1"]) == list:
                result_bert_l.append(result_bert_temp["f1"][0])
            else:
                result_bert_l.append(result_bert_temp["f1"])
        result["bert_score_l"] = np.mean(result_bert_l)

    readability_dict = {}
    for metric in [
        "flesch_reading_ease",
        "flesch_kincaid_grade",
        "ari",
        "dale_chall",
        "gunning_fog",
    ]:
        if metric in metrics:
            result_readability = list(
                map(lambda s: get_readability_score(s, metric=metric), predictions)
            )
            readability_dict[f"{metric}_counts"] = Counter(
                list(map(lambda item: item[1], result_readability))
            )
            readability_dict[f"{metric}_score"] = np.mean(
                list(map(lambda item: item[0], result_readability))
            )
    result.update(readability_dict)

    return {k: round(v, 4) if "counts" not in k else v for k, v in result.items()}
