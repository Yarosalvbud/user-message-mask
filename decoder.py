from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass

import tiktoken
import torch

import os

from opf._common.label_space import (
    resolve_label_space_from_config,
)
from opf._core.decoding import build_sequence_decoder
from opf._core.sequence_labeling import build_label_info
from opf._core.spans import (
    decode_text_with_offsets,
    labels_to_spans,
    token_spans_to_char_spans,
    trim_char_spans_whitespace,
)

@dataclass(frozen=True)
class OPFRuntime:
    encoding: object
    label_info: object
    decoder: object

def _build_opf_runtime() -> OPFRuntime:
    model_config = {
        "model_type": os.environ["OPF_MODEL_TYPE"],
        "inference_contract_version": int(
            os.environ["OPF_INFERENCE_CONTRACT_VERSION"]
        ),
        "encoding": os.environ["OPF_ENCODING"],
        "num_labels": int(
            os.environ["OPF_NUM_LABELS"]
        ),
    }

    _, _, ner_class_names = resolve_label_space_from_config(
        model_config,
        context="user-message-mask",
    )

    label_info = build_label_info(
        ner_class_names
    )

    encoding = tiktoken.get_encoding(
        model_config["encoding"]
    )

    decoder, _ = build_sequence_decoder(
        decode_mode="viterbi",
        label_info=label_info,
        viterbi_calibration_path=None,
        checkpoint_dir=None,
    )

    return OPFRuntime(
        encoding=encoding,
        label_info=label_info,
        decoder=decoder,
    )


def _call_privacy_filter(
    text: str,
) -> list[list[float]]:
    payload = json.dumps(
        {
            "model": os.environ["VLLM_MODEL"],
            "input": text,
            "pooling_task": "token_classify",
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        os.environ["VLLM_URL"],
        data=payload,
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(
        request,
        timeout=int(os.environ.get("TIMEOUT_SECONDS", "15")),
    ) as response:
        body = json.loads(
            response.read().decode("utf-8")
        )

    scores = body["data"][0]["data"]

    if not isinstance(scores, list):
        raise RuntimeError(
            "Invalid privacy-filter response"
        )

    return scores


def _decode_spans(
    text: str,
    probabilities: list[list[float]],
    opf_runtime: OPFRuntime
) -> list[tuple[int, int, str]]:
    token_ids = tuple(
        int(token)
        for token in opf_runtime.encoding.encode(
            text,
            allowed_special="all",
        )
    )

    if not token_ids:
        return []

    if len(token_ids) != len(probabilities):
        raise RuntimeError(
            "Token count mismatch: "
            f"local={len(token_ids)}, "
            f"vllm={len(probabilities)}"
        )

    log_probs = torch.tensor(
        probabilities,
        dtype=torch.float32,
    )

    log_probs = torch.log(
        log_probs.clamp_min(1e-30)
    )

    decoded_labels = opf_runtime.decoder.decode(
        log_probs
    )

    labels_by_index = {
        token_idx: int(label)
        for token_idx, label
        in enumerate(decoded_labels)
    }

    token_spans = labels_to_spans(
        labels_by_index,
        opf_runtime.label_info,
    )

    decoded_text, char_starts, char_ends = (
        decode_text_with_offsets(
            token_ids,
            opf_runtime.encoding,
        )
    )

    if decoded_text != text:
        raise RuntimeError(
            "Tokenizer round-trip mismatch"
        )

    char_spans = token_spans_to_char_spans(
        token_spans,
        char_starts,
        char_ends,
    )

    char_spans = trim_char_spans_whitespace(
        char_spans,
        text,
    )

    result: list[tuple[int, int, str]] = []

    for label_idx, start, end in char_spans:
        if not (
            0 <= start < end <= len(text)
        ):
            continue

        label = opf_runtime.label_info.span_class_names[
            label_idx
        ]

        result.append(
            (
                int(start),
                int(end),
                str(label),
            )
        )

    return result


def _redact_text(
    text: str,
    spans: list[tuple[int, int, str]],
) -> str:
    if not spans:
        return text

    spans = sorted(
        spans,
        key=lambda item: (
            item[0],
            -(item[1] - item[0]),
        ),
    )

    result: list[str] = []
    cursor = 0

    for start, end, label in spans:
        if start < cursor:
            continue

        result.append(
            text[cursor:start]
        )

        result.append(
            result.append(
                f"<{label.upper()}>"
            )
        )

        cursor = end

    result.append(
        text[cursor:]
    )

    return "".join(result)


def transform_user_message(
    user_message: str,
    session_id: str | None = None,
    task_id: str | None = None,
    **kwargs,
):
    del session_id, task_id, kwargs

    if not isinstance(user_message, str):
        return None

    if not user_message.strip():
        return user_message

    probabilities = _call_privacy_filter(
        user_message
    )

    spans = _decode_spans(
        user_message,
        probabilities,
    )

    redacted_text = _redact_text(
        user_message,
        spans,
    )

    return redacted_text

if __name__ == "__main__":
    import json
    import sys

    text = sys.stdin.read()

    probabilities = _call_privacy_filter(
        text
    )

    opf_runtime = _build_opf_runtime()

    spans = _decode_spans(
        text,
        probabilities,
        opf_runtime
    )

    redacted_text = _redact_text(
        text,
        spans,
    )

    print(
        json.dumps(
            {
                "redacted_text": redacted_text,
                "span_count": len(spans),
            },
            ensure_ascii=False,
        )
    )
