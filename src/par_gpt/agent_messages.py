"""Random message generator for a bot."""

import random


def get_random_message() -> str:
    """
    Selects a random message from a predefined list of bot messages.

    Returns:
        str: A randomly selected message.
    """
    messages = [
        "One moment please.",
        "Working on it!",
        "I'm on it!",
        "Okay!",
        "Making it so!",
        "Making it happen!",
        "Task is underway!",
        "No problem! One moment, please.",
    ]

    return random.choice(messages)


if __name__ == "__main__":
    print(get_random_message())
