import random

def random_wait(a=800, b=1800):
    return random.randint(a, b)


def random_scroll():
    return random.randint(1800, 3500)


def get_random_user_agent():
    uas = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/121.0 Safari/537.36",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15) AppleWebKit/605.1.15 Version/17.0 Safari/605.1.15",
    ]
    return random.choice(uas)


def get_random_viewport():
    return {
        "width": random.randint(1100, 1600),
        "height": random.randint(700, 1000)
    }
