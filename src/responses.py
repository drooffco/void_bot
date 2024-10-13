from random import choice, randint


def get_response(user_input: str) -> str:
    print(f'getting response')
    lowered: str = user_input.lower()
    if lowered == '':
        return 'no message'
    elif 'hello' in lowered:
        return 'hello there'
    else:
        return choice([
            'uh oh nothing happened',
            'whoops',
            'not what I expected'
        ])

