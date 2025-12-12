"""
Fuzzing tests for RequestValidator parsing logic.

These tests generate randomized HTTP request payloads and ensure the validation
layer either accepts them or returns structured errors without raising.
"""

import os
import random
import string

import pytest
from flask import Flask

from xai.core.request_validator_middleware import RequestValidator


app = Flask(__name__)


def _random_path() -> str:
    return "/" + "".join(random.choice(string.ascii_letters) for _ in range(random.randint(1, 128)))


def _random_content_type() -> str:
    base_types = [
        "application/json",
        "application/x-www-form-urlencoded",
        "multipart/form-data",
        "text/plain",
        "image/png",
        "application/xml",
    ]
    return random.choice(base_types)


def test_request_validator_size_and_type_fuzz():
    validator = RequestValidator(max_json_size=2048, max_url_length=256)
    for _ in range(200):
        method = random.choice(["GET", "POST", "PUT", "DELETE"])
        data = os.urandom(random.randint(0, 4096))
        headers = {"Content-Type": _random_content_type()}
        with app.test_request_context(
            path=_random_path(),
            method=method,
            data=data,
            headers=headers,
        ):
            valid, _ = validator.validate_request_size()
            assert isinstance(valid, bool)
            valid, _ = validator.validate_content_type()
            assert isinstance(valid, bool)


def _random_json(depth=0):
    if depth > 5:
        return random.randint(0, 100)
    choice = random.random()
    if choice < 0.3:
        return [_random_json(depth + 1) for _ in range(random.randint(0, 4))]
    if choice < 0.6:
        return {f"k{depth}_{i}": _random_json(depth + 1) for i in range(random.randint(0, 4))}
    return random.randint(-1000, 1000)


def test_request_validator_json_depth_fuzz():
    validator = RequestValidator(max_json_size=4096)
    for _ in range(100):
        payload = _random_json()
        with app.test_request_context(
            path="/json",
            method="POST",
            json=payload,
            headers={"Content-Type": "application/json"},
        ):
            valid, _ = validator.validate_json_structure(max_depth=5)
            assert isinstance(valid, bool)
